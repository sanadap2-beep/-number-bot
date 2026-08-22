"""
مدير مزودي الأرقام مع Failover تلقائي.

المنطق:
1) يجلب أسعار كل المزودين المتاحين للدولة/الخدمة.
2) يرتبهم حسب السعر (الأرخص أولاً).
3) يحاول الشراء من الأرخص، إذا فشل ينتقل للتالي.
4) يتحقق من is_online قبل المحاولة لتجنب التأخير.
5) العملة: دولار أمريكي (USD) بالكامل.
"""
import logging
from dataclasses import dataclass
from decimal import Decimal

from database.models import Country, NumberService, ProviderName, ProviderStatus
from providers.fivesim import FiveSimProvider
from providers.herosms import HeroSMSProvider
from providers.sms_activate import SMSActivateProvider
from providers.smshub import SMSHubProvider
from config import settings

logger = logging.getLogger(__name__)


class ProviderUnavailableError(Exception):
    pass


@dataclass
class BuyResult:
    provider: ProviderName
    provider_order_id: str
    phone_number: str
    cost_usd: Decimal


class ProviderManager:

    def __init__(self):
        self._providers: dict[ProviderName, object] = {}
        self._init_providers()

    def _init_providers(self):
        """يُنشئ المزودين الذين لديهم API key فقط."""
        if settings.FIVESIM_API_KEY:
            self._providers[ProviderName.FIVESIM] = FiveSimProvider()

        if settings.HEROSMS_API_KEY:
            self._providers[ProviderName.HEROSMS] = HeroSMSProvider()

        if settings.SMS_ACTIVATE_API_KEY:
            self._providers[ProviderName.SMS_ACTIVATE] = SMSActivateProvider()

        if settings.SMSHUB_API_KEY:
            self._providers[ProviderName.SMSHUB] = SMSHubProvider()

        logger.info(
            f"تم تهيئة {len(self._providers)} مزود أرقام: "
            f"{', '.join(p.value for p in self._providers.keys())}"
        )

    def _get_instance(self, provider: ProviderName):
        instance = self._providers.get(provider)
        if instance is None:
            raise ProviderUnavailableError(
                f"المزود {provider.value} غير مهيأ (لا يوجد API Key)"
            )
        return instance

    def _get_provider_code(
        self,
        provider: ProviderName,
        country: Country,
    ) -> str | None:
        """يجلب كود الدولة الخاص بمزود معين."""
        code_map = {
            ProviderName.FIVESIM: country.fivesim_code,
            ProviderName.HEROSMS: country.herosms_code,
            ProviderName.SMS_ACTIVATE: country.sms_activate_code,
            ProviderName.SMSHUB: country.smshub_code,
        }
        return code_map.get(provider)

    def _get_service_code(
        self,
        provider: ProviderName,
        service: NumberService,
    ) -> str | None:
        """يجلب كود الخدمة الخاص بمزود معين."""
        code_map = {
            ProviderName.FIVESIM: service.fivesim_code,
            ProviderName.HEROSMS: service.herosms_code,
            ProviderName.SMS_ACTIVATE: service.sms_activate_code,
            ProviderName.SMSHUB: service.smshub_code,
        }
        return code_map.get(provider)

    async def _is_provider_online(
        self,
        session,
        provider: ProviderName,
    ) -> bool:
        """يتحقق من حالة المزود في قاعدة البيانات."""
        status = await session.get(ProviderStatus, provider)
        if status is None:
            return False
        # A fresh installation has no health-check result yet. Allow the
        # first real request instead of blocking every provider for the first
        # ten minutes until the scheduler runs.
        if status.last_checked_at is None:
            return True
        return status.is_online

    async def get_cheapest_price(
        self,
        service: NumberService,
        country: Country,
        session=None,
    ) -> dict[ProviderName, Decimal]:
        """
        يجلب أسعار كل المزودين المتاحين لخدمة/دولة معينة.
        يرجع dict مع المزود كمفتاح والسعر بالدولار كقيمة.
        """
        result = {}

        for provider_name, instance in self._providers.items():
            country_code = self._get_provider_code(
                provider_name, country
            )
            service_code = self._get_service_code(
                provider_name, service
            )

            if not country_code or not service_code:
                continue

            if session:
                is_online = await self._is_provider_online(
                    session, provider_name
                )
                if not is_online:
                    continue

            try:
                price = await instance.get_price(
                    country_code, service_code
                )
                if price is not None:
                    result[provider_name] = price
            except Exception as e:
                logger.warning(
                    f"فشل جلب سعر من {provider_name.value}: {e}"
                )

        return result

    async def buy_number(
        self,
        service: NumberService,
        country: Country,
        session=None,
    ) -> BuyResult:
        """
        يشتري رقماً من أرخص مزود متاح.
        إذا فشل ينتقل تلقائياً للمزود التالي (Failover).
        """
        prices = await self.get_cheapest_price(
            service, country, session
        )

        if not prices:
            raise ProviderUnavailableError(
                f"لا يوجد مزود متاح لـ "
                f"{service.name_ar} - {country.name_ar}"
            )

        sorted_providers = sorted(
            prices.items(), key=lambda x: x[1]
        )

        errors = []

        for provider_name, estimated_price in sorted_providers:
            instance = self._providers[provider_name]
            country_code = self._get_provider_code(
                provider_name, country
            )
            service_code = self._get_service_code(
                provider_name, service
            )

            try:
                purchased = await instance.buy_number(
                    country_code, service_code
                )
                logger.info(
                    f"شراء ناجح من {provider_name.value}: "
                    f"{purchased.phone_number} "
                    f"بتكلفة {purchased.cost_usd}$"
                )
                return BuyResult(
                    provider=provider_name,
                    provider_order_id=purchased.provider_order_id,
                    phone_number=purchased.phone_number,
                    cost_usd=purchased.cost_usd,
                )
            except Exception as e:
                errors.append(
                    f"{provider_name.value}: {e}"
                )
                logger.warning(
                    f"فشل الشراء من {provider_name.value}: {e}"
                )
                continue

        raise ProviderUnavailableError(
            f"فشل الشراء من كل المزودين المتاحين. "
            f"{' | '.join(errors)}"
        )

    async def check_status(
        self,
        provider: ProviderName,
        order_id: str,
    ):
        """يتحقق من حالة طلب عند مزود محدد."""
        return await self._get_instance(provider).check_status(
            order_id
        )

    async def cancel_order(
        self,
        provider: ProviderName,
        order_id: str,
    ) -> bool:
        """يلغي طلباً عند مزود محدد."""
        return await self._get_instance(provider).cancel_order(
            order_id
        )

    async def finish_order(
        self,
        provider: ProviderName,
        order_id: str,
    ) -> bool:
        """يُنهي طلباً عند مزود محدد بعد استلام الكود."""
        return await self._get_instance(provider).finish_order(
            order_id
        )

    async def get_balance(
        self,
        provider: ProviderName,
    ) -> Decimal:
        """يجلب رصيد مزود محدد بالدولار."""
        return await self._get_instance(provider).get_balance()

    def get_available_providers(self) -> list[ProviderName]:
        """يجلب قائمة المزودين المهيأين (لديهم API Key)."""
        return list(self._providers.keys())


provider_manager = ProviderManager()
