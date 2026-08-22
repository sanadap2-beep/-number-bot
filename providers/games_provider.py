"""
مزود شحن الألعاب والتطبيقات.
يتصل بـ API الخاص بمزود شحن الألعاب لتنفيذ الطلبات تلقائياً.
يدعم أي مزود يستخدم REST API مع JSON.
"""
import logging
from decimal import Decimal

import aiohttp

from database.models import ApiProvider

logger = logging.getLogger(__name__)


class GamesProviderError(Exception):
    pass


class GamesProviderClient:
    """
    عميل عام للتواصل مع مزودي شحن الألعاب.
    كل مزود يُخزن بياناته (api_url, api_key) في جدول api_providers.
    """

    def __init__(self, provider: ApiProvider):
        self.provider = provider
        self.api_url = provider.api_url.rstrip("/")
        self.api_key = provider.api_key

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        url = f"{self.api_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            async with aiohttp.ClientSession(
                headers=headers
            ) as session:
                async with session.request(
                    method,
                    url,
                    json=data,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    text = await resp.text()
                    if resp.status not in (200, 201):
                        raise GamesProviderError(
                            f"خطأ من مزود الألعاب "
                            f"{self.provider.name}: "
                            f"HTTP {resp.status}: {text[:200]}"
                        )
                    try:
                        return await resp.json(
                            content_type=None
                        )
                    except Exception:
                        raise GamesProviderError(
                            f"استجابة غير صالحة من "
                            f"{self.provider.name}: {text[:200]}"
                        )
        except aiohttp.ClientError as e:
            raise GamesProviderError(
                f"خطأ اتصال مع {self.provider.name}: {e}"
            )

    async def get_balance(self) -> Decimal:
        """يجلب رصيد الحساب لدى المزود."""
        try:
            data = await self._request("GET", "balance")
            balance = data.get("balance", data.get("data", {}).get("balance", 0))
            return Decimal(str(balance))
        except Exception as e:
            logger.error(
                f"فشل جلب رصيد مزود الألعاب "
                f"{self.provider.name}: {e}"
            )
            raise

    async def place_order(
        self,
        service_id: str,
        target: str,
        quantity: int = 1,
    ) -> dict:
        """
        يرسل طلب شحن لعبة/تطبيق.
        service_id: آيدي الخدمة عند المزود
        target: آيدي اللاعب أو الحساب
        quantity: الكمية
        يرجع dict يحتوي على order_id على الأقل.
        """
        try:
            data = await self._request(
                "POST",
                "order",
                data={
                    "service_id": service_id,
                    "target": target,
                    "quantity": quantity,
                },
            )

            order_id = data.get(
                "order_id",
                data.get("id", data.get("data", {}).get("order_id"))
            )

            if order_id is None:
                raise GamesProviderError(
                    f"لم يُرجع المزود {self.provider.name} "
                    f"رقم طلب. الاستجابة: {data}"
                )

            return {
                "order_id": str(order_id),
                "status": data.get("status", "pending"),
                "raw": data,
            }
        except GamesProviderError:
            raise
        except Exception as e:
            raise GamesProviderError(
                f"فشل إرسال الطلب لمزود "
                f"{self.provider.name}: {e}"
            )

    async def check_order_status(
        self, order_id: str
    ) -> dict:
        """
        يتحقق من حالة الطلب.
        يرجع dict يحتوي status و message.
        """
        try:
            data = await self._request(
                "GET",
                f"order/{order_id}",
            )

            status = data.get(
                "status",
                data.get("data", {}).get("status", "pending")
            )
            message = data.get(
                "message",
                data.get("data", {}).get("message", "")
            )

            status_map = {
                "completed": "completed",
                "success": "completed",
                "done": "completed",
                "failed": "failed",
                "error": "failed",
                "cancelled": "failed",
                "canceled": "failed",
                "refunded": "refunded",
                "processing": "processing",
                "pending": "pending",
                "in_progress": "processing",
                "partial": "partial",
            }

            normalized_status = status_map.get(
                status.lower(), "pending"
            )

            return {
                "status": normalized_status,
                "message": message,
                "raw": data,
            }
        except GamesProviderError:
            raise
        except Exception as e:
            raise GamesProviderError(
                f"فشل فحص حالة الطلب {order_id} "
                f"من {self.provider.name}: {e}"
            )

    async def get_services(self) -> list[dict]:
        """يجلب قائمة الخدمات المتاحة (اختياري)."""
        try:
            data = await self._request("GET", "services")
            services = data if isinstance(data, list) else data.get(
                "data", data.get("services", [])
            )
            return services
        except Exception as e:
            logger.warning(
                f"فشل جلب خدمات مزود {self.provider.name}: {e}"
            )
            return []
