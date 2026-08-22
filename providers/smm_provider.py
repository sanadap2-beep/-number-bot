"""
مزود رشق السوشيال ميديا.
يدعم أي موقع SMM يستخدم البروتوكول القياسي v2 API.
البروتوكول القياسي يستخدم 4 endpoints:
- balance: جلب الرصيد
- services: جلب الخدمات
- order: إرسال طلب
- status: فحص حالة الطلب
"""
import logging
from decimal import Decimal

import aiohttp

from database.models import ApiProvider

logger = logging.getLogger(__name__)


class SMMProviderError(Exception):
    pass


class SMMProviderClient:
    """
    عميل عام لأي موقع SMM يدعم v2 API.
    الأدمن يضيف المزود من لوحة التحكم بإدخال:
    - api_url: رابط الـ API (مثل https://example.com/api/v2)
    - api_key: مفتاح الـ API
    """

    def __init__(self, provider: ApiProvider):
        self.provider = provider
        self.api_url = provider.api_url.rstrip("/")
        self.api_key = provider.api_key

    async def _request(
        self,
        data: dict,
    ) -> dict | list:
        """
        يرسل طلب POST لـ API المزود.
        كل طلبات SMM v2 API تُرسل عبر POST بنفس الرابط.
        """
        data["key"] = self.api_key

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    text = await resp.text()
                    if resp.status != 200:
                        raise SMMProviderError(
                            f"خطأ من مزود SMM "
                            f"{self.provider.name}: "
                            f"HTTP {resp.status}: {text[:200]}"
                        )
                    try:
                        result = await resp.json(
                            content_type=None
                        )
                    except Exception:
                        raise SMMProviderError(
                            f"استجابة غير صالحة من "
                            f"{self.provider.name}: {text[:200]}"
                        )

                    if isinstance(result, dict) and result.get("error"):
                        raise SMMProviderError(
                            f"خطأ من {self.provider.name}: "
                            f"{result.get('error')}"
                        )

                    return result
        except aiohttp.ClientError as e:
            raise SMMProviderError(
                f"خطأ اتصال مع {self.provider.name}: {e}"
            )

    async def get_balance(self) -> Decimal:
        """يجلب رصيد الحساب لدى المزود."""
        try:
            data = await self._request({
                "action": "balance",
            })
            balance = data.get(
                "balance",
                data.get("data", {}).get("balance", 0)
            )
            return Decimal(str(balance))
        except Exception as e:
            logger.error(
                f"فشل جلب رصيد مزود SMM "
                f"{self.provider.name}: {e}"
            )
            raise

    async def get_services(self) -> list[dict]:
        """
        يجلب كل الخدمات المتاحة من المزود.
        كل خدمة تحتوي: service (id), name, rate, min, max, type, category.
        """
        try:
            result = await self._request({
                "action": "services",
            })
            if isinstance(result, list):
                return result
            return result.get("data", result.get("services", []))
        except Exception as e:
            logger.warning(
                f"فشل جلب خدمات مزود SMM "
                f"{self.provider.name}: {e}"
            )
            return []

    async def place_order(
        self,
        service_id: str,
        link: str,
        quantity: int,
    ) -> dict:
        """
        يرسل طلب رشق.
        service_id: آيدي الخدمة عند المزود
        link: رابط الحساب/المنشور
        quantity: الكمية المطلوبة
        يرجع dict يحتوي order_id.
        """
        try:
            data = await self._request({
                "action": "add",
                "service": service_id,
                "link": link,
                "quantity": str(quantity),
            })

            order_id = data.get("order")
            if order_id is None:
                raise SMMProviderError(
                    f"لم يُرجع المزود {self.provider.name} "
                    f"رقم طلب. الاستجابة: {data}"
                )

            return {
                "order_id": str(order_id),
                "status": "pending",
                "raw": data,
            }
        except SMMProviderError:
            raise
        except Exception as e:
            raise SMMProviderError(
                f"فشل إرسال طلب SMM لمزود "
                f"{self.provider.name}: {e}"
            )

    async def check_order_status(
        self, order_id: str
    ) -> dict:
        """
        يتحقق من حالة الطلب.
        يرجع status, start_count, remains, charge.
        """
        try:
            data = await self._request({
                "action": "status",
                "order": order_id,
            })

            status = data.get("status", "pending")

            status_map = {
                "Completed": "completed",
                "completed": "completed",
                "In progress": "processing",
                "in_progress": "processing",
                "Processing": "processing",
                "processing": "processing",
                "Pending": "pending",
                "pending": "pending",
                "Partial": "partial",
                "partial": "partial",
                "Canceled": "failed",
                "canceled": "failed",
                "Cancelled": "failed",
                "cancelled": "failed",
                "Refunded": "refunded",
                "refunded": "refunded",
                "Error": "failed",
                "error": "failed",
                "Fail": "failed",
            }

            normalized_status = status_map.get(
                status, "pending"
            )

            return {
                "status": normalized_status,
                "start_count": data.get("start_count"),
                "remains": data.get("remains"),
                "charge": data.get("charge"),
                "raw": data,
            }
        except SMMProviderError:
            raise
        except Exception as e:
            raise SMMProviderError(
                f"فشل فحص حالة الطلب {order_id} "
                f"من {self.provider.name}: {e}"
            )

    async def check_multiple_orders(
        self, order_ids: list[str]
    ) -> dict:
        """
        يتحقق من حالة عدة طلبات دفعة واحدة.
        يرجع dict بمفتاح order_id وقيمة حالة الطلب.
        """
        try:
            data = await self._request({
                "action": "status",
                "orders": ",".join(order_ids),
            })
            return data
        except Exception as e:
            logger.warning(
                f"فشل فحص طلبات متعددة من "
                f"{self.provider.name}: {e}"
            )
            return {}
