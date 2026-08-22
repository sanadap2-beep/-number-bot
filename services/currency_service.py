"""
خدمة تحويل العملات.
تُستخدم لتحويل عملات المزودين إلى دولار.
"""
import logging
from decimal import Decimal, ROUND_HALF_UP

from services.settings_service import SettingsService

logger = logging.getLogger(__name__)


# ── أسعار صرف افتراضية (يمكن تحديثها من لوحة الأدمن) ──
DEFAULT_RATES_TO_USD = {
    "USD": Decimal("1"),
    "EUR": Decimal("1.08"),
    "RUB": Decimal("0.011"),
    "TRY": Decimal("0.03"),
    "IDR": Decimal("0.000064"),
    "INR": Decimal("0.012"),
    "PKR": Decimal("0.0036"),
    "BDT": Decimal("0.0091"),
    "SYP": Decimal("0.000067"),
    "SAR": Decimal("0.27"),
    "AED": Decimal("0.27"),
    "EGP": Decimal("0.020"),
    "IQD": Decimal("0.00076"),
    "JOD": Decimal("1.41"),
    "LBP": Decimal("0.000011"),
    "MAD": Decimal("0.10"),
    "DZD": Decimal("0.0075"),
    "TND": Decimal("0.32"),
    "LYD": Decimal("0.21"),
    "YER": Decimal("0.004"),
    "SDG": Decimal("0.0017"),
    "QAR": Decimal("0.27"),
    "OMR": Decimal("2.60"),
    "KWD": Decimal("3.25"),
    "BHD": Decimal("2.65"),
    "IRR": Decimal("0.000024"),
    "CNY": Decimal("0.14"),
    "GBP": Decimal("1.27"),
    "CAD": Decimal("0.73"),
    "AUD": Decimal("0.65"),
    "BRL": Decimal("0.20"),
    "MXN": Decimal("0.058"),
    "ARS": Decimal("0.001"),
    "COP": Decimal("0.00025"),
    "VND": Decimal("0.000041"),
    "THB": Decimal("0.029"),
    "PHP": Decimal("0.018"),
    "MYR": Decimal("0.22"),
    "SGD": Decimal("0.75"),
    "KRW": Decimal("0.00074"),
    "JPY": Decimal("0.0068"),
    "HKD": Decimal("0.13"),
    "TWD": Decimal("0.031"),
    "ZAR": Decimal("0.055"),
    "NGN": Decimal("0.00065"),
    "UAH": Decimal("0.025"),
    "PLN": Decimal("0.25"),
    "UZS": Decimal("0.000080"),
    "KZT": Decimal("0.0022"),
}


class CurrencyService:
    """خدمة تحويل العملات إلى دولار."""

    @staticmethod
    def get_default_rate(currency: str) -> Decimal:
        """يجلب سعر الصرف الافتراضي لعملة."""
        return DEFAULT_RATES_TO_USD.get(
            currency.upper(), Decimal("1")
        )

    @staticmethod
    async def get_rate_to_usd(
        currency: str, session=None
    ) -> Decimal:
        """
        يجلب سعر تحويل العملة إلى الدولار.
        أولاً من الإعدادات، ثم من القيم الافتراضية.
        """
        currency = currency.upper()

        if currency == "USD":
            return Decimal("1")

        setting_key = f"rate_{currency.lower()}_to_usd"
        rate_str = await SettingsService.get(setting_key)

        if rate_str:
            try:
                return Decimal(rate_str)
            except Exception:
                pass

        return CurrencyService.get_default_rate(currency)

    @staticmethod
    async def convert_to_usd(
        amount: Decimal,
        currency: str,
        session=None,
    ) -> Decimal:
        """
        يحول مبلغ من عملة معينة إلى دولار.
        """
        if currency.upper() == "USD":
            return amount

        rate = await CurrencyService.get_rate_to_usd(
            currency, session
        )
        result = amount * rate
        return result.quantize(
            Decimal("0.0001"),
            rounding=ROUND_HALF_UP,
        )

    @staticmethod
    def get_supported_currencies() -> list[str]:
        """يجلب قائمة العملات المدعومة."""
        return list(DEFAULT_RATES_TO_USD.keys())

    @staticmethod
    async def set_custom_rate(
        session,
        currency: str,
        rate: Decimal,
    ) -> None:
        """يحفظ سعر صرف مخصص لعملة."""
        currency = currency.upper()
        setting_key = f"rate_{currency.lower()}_to_usd"
        await SettingsService.set(session, setting_key, str(rate))
        logger.info(
            f"تم تحديث سعر الصرف: 1 {currency} = {rate} USD"
        )
