"""
خدمة الإشعارات المركزية.

مسؤوليات هذا الملف:
1) إرسال إشعارات للأدمن (قناة خاصة).
2) إرسال إشعارات للقناة العامة (عمليات ناجحة).
3) إرسال إشعارات للمستخدمين.
4) إرسال إشعارات البكاب.
5) إخفاء اسم المستخدم جزئياً في القناة العامة.
"""
import logging
from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from services.settings_service import SettingsService

logger = logging.getLogger(__name__)


def _mask_username(username: str | None, full_name: str | None) -> str:
    """
    يخفي اسم المستخدم جزئياً للقناة العامة.
    مثال: "Ahmed Ali" → "Ah***Ali"
    مثال: "@sanad" → "@sa***"
    """
    name = username or full_name or "مستخدم"
    if len(name) <= 3:
        return name[0] + "***"
    visible_start = name[:2]
    visible_end = name[-2:] if len(name) > 4 else ""
    return f"{visible_start}***{visible_end}"


class NotificationService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def notify_admin(
        self,
        text: str,
        reply_markup=None,
        parse_mode: str = "HTML"
    ) -> int | None:
        """
        يرسل إشعاراً نصياً لقناة الأدمن.
        يرجع message_id إذا نجح، أو None إذا فشل.
        """
        from config import settings
        chat_id = settings.ADMIN_NOTIFY_CHAT_ID
        if not chat_id:
            logger.error("ADMIN_NOTIFY_CHAT_ID غير محدد في .env")
            return None
        try:
            sent = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return sent.message_id
        except TelegramForbiddenError:
            logger.error(
                f"البوت محظور أو ليس أدمن في قناة الأدمن (chat_id={chat_id}). "
                "تأكد أن البوت أدمن في القناة."
            )
            return None
        except TelegramBadRequest as e:
            logger.error(f"خطأ في إرسال إشعار الأدمن (chat_id={chat_id}): {e}")
            return None
        except Exception as e:
            logger.error(f"خطأ غير متوقع في إرسال إشعار الأدمن: {e}")
            return None

    async def notify_admin_photo(
        self,
        photo_file_id: str,
        caption: str,
        reply_markup=None,
        parse_mode: str = "HTML"
    ) -> int | None:
        """
        يرسل إشعاراً بصورة لقناة الأدمن.
        يرجع message_id إذا نجح، أو None إذا فشل.
        """
        from config import settings
        chat_id = settings.ADMIN_NOTIFY_CHAT_ID
        if not chat_id:
            logger.error("ADMIN_NOTIFY_CHAT_ID غير محدد في .env")
            return None
        try:
            sent = await self.bot.send_photo(
                chat_id=chat_id,
                photo=photo_file_id,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return sent.message_id
        except TelegramForbiddenError:
            logger.error(
                f"البوت محظور أو ليس أدمن في قناة الأدمن (chat_id={chat_id}). "
                "تأكد أن البوت أدمن في القناة."
            )
            return None
        except TelegramBadRequest as e:
            logger.error(f"خطأ في إرسال صورة إشعار الأدمن (chat_id={chat_id}): {e}")
            return None
        except Exception as e:
            logger.error(f"خطأ غير متوقع في إرسال صورة إشعار الأدمن: {e}")
            return None

    async def notify_user(
        self,
        telegram_id: int,
        text: str,
        reply_markup=None,
        parse_mode: str = "HTML"
    ) -> bool:
        """
        يرسل إشعاراً للمستخدم.
        يرجع True إذا نجح، False إذا فشل.
        """
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return True
        except TelegramForbiddenError:
            logger.warning(
                f"المستخدم {telegram_id} حظر البوت، تخطي الإشعار."
            )
            return False
        except TelegramBadRequest as e:
            logger.warning(
                f"خطأ في إرسال إشعار للمستخدم {telegram_id}: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"خطأ غير متوقع في إرسال إشعار للمستخدم {telegram_id}: {e}"
            )
            return False

    async def notify_public_channel(
        self,
        text: str,
        parse_mode: str = "HTML"
    ) -> bool:
        """
        يرسل إشعار عملية ناجحة للقناة العامة.
        يرجع True إذا نجح، False إذا فشل أو القناة غير محددة.
        """
        channel_id_str = await SettingsService.get("public_channel_id", "0")
        try:
            channel_id = int(channel_id_str)
        except (ValueError, TypeError):
            channel_id = 0

        if not channel_id:
            return False

        try:
            await self.bot.send_message(
                chat_id=channel_id,
                text=text,
                parse_mode=parse_mode,
            )
            return True
        except TelegramForbiddenError:
            logger.error(
                f"البوت محظور أو ليس أدمن في القناة العامة (chat_id={channel_id})."
            )
            return False
        except TelegramBadRequest as e:
            logger.error(f"خطأ في إرسال إشعار للقناة العامة: {e}")
            return False
        except Exception as e:
            logger.error(f"خطأ غير متوقع في إرسال إشعار للقناة العامة: {e}")
            return False

    async def notify_backup_channel(
        self,
        document_bytes: bytes,
        filename: str,
        caption: str,
    ) -> bool:
        """
        يرسل ملف البكاب لقناة البكاب.
        يرجع True إذا نجح، False إذا فشل.
        """
        channel_id_str = await SettingsService.get("backup_channel_id", "0")
        try:
            channel_id = int(channel_id_str)
        except (ValueError, TypeError):
            channel_id = 0

        if not channel_id:
            logger.warning("backup_channel_id غير محدد، تخطي البكاب.")
            return False

        try:
            from aiogram.types import BufferedInputFile
            file = BufferedInputFile(document_bytes, filename=filename)
            await self.bot.send_document(
                chat_id=channel_id,
                document=file,
                caption=caption,
            )
            return True
        except Exception as e:
            logger.error(f"خطأ في إرسال البكاب: {e}")
            return False

    async def notify_successful_number_order(
        self,
        username: str | None,
        full_name: str | None,
        service_name: str,
        price_usd: str,
    ) -> None:
        """
        يرسل إشعار شراء رقم ناجح للقناة العامة.
        """
        masked = _mask_username(username, full_name)
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        text = (
            "✅ <b>عملية شراء ناجحة!</b>\n\n"
            f"👤 المستخدم: {masked}\n"
            f"📞 الخدمة: {service_name}\n"
            f"💰 المبلغ: {price_usd}$\n"
            f"📅 التاريخ: {now} UTC"
        )
        await self.notify_public_channel(text)

    async def notify_successful_unified_order(
        self,
        username: str | None,
        full_name: str | None,
        product_name: str,
        price_usd: str,
    ) -> None:
        """
        يرسل إشعار شراء منتج (لعبة/تطبيق/SMM) ناجح للقناة العامة.
        """
        masked = _mask_username(username, full_name)
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        text = (
            "✅ <b>عملية شراء ناجحة!</b>\n\n"
            f"👤 المستخدم: {masked}\n"
            f"🛒 المنتج: {product_name}\n"
            f"💰 المبلغ: {price_usd}$\n"
            f"📅 التاريخ: {now} UTC"
        )
        await self.notify_public_channel(text)

    async def notify_provider_low_balance(
        self,
        provider_name: str,
        balance: str,
        threshold: str,
    ) -> None:
        """
        يرسل تنبيه لقناة الأدمن عند انخفاض رصيد مزود عن الحد المحدد.
        """
        text = (
            "⚠️ <b>تنبيه: رصيد منخفض!</b>\n\n"
            f"🔌 المزود: {provider_name}\n"
            f"💰 الرصيد الحالي: {balance}$\n"
            f"🚨 الحد الأدنى المحدد: {threshold}$\n\n"
            "يرجى شحن رصيد المزود في أقرب وقت."
        )
        await self.notify_admin(text)

    async def notify_provider_offline(
        self,
        provider_name: str,
        error: str,
    ) -> None:
        """
        يرسل تنبيه لقناة الأدمن عند توقف مزود عن الاستجابة.
        """
        text = (
            "🔴 <b>تنبيه: مزود غير متاح!</b>\n\n"
            f"🔌 المزود: {provider_name}\n"
            f"⚠️ الخطأ: {error[:200]}\n\n"
            "تم تعطيل المزود تلقائياً حتى يعود للعمل."
        )
        await self.notify_admin(text)

    async def notify_new_deposit(
        self,
        user_telegram_id: int,
        username: str | None,
        amount_usd: str,
        tx_number: str,
        deposit_id: int,
        photo_file_id: str,
        reply_markup,
    ) -> int | None:
        """
        يرسل إشعار إيداع جديد لقناة الأدمن مع صورة الإثبات وأزرار القبول/الرفض.
        يرجع message_id الرسالة في القناة.
        """
        caption = (
            "🆕 <b>طلب شحن رصيد جديد</b>\n\n"
            f"👤 المستخدم: {user_telegram_id}"
            f" (@{username or '-'})\n"
            f"💵 المبلغ: <b>{amount_usd}$</b>\n"
            f"🔢 رقم العملية: <code>{tx_number}</code>\n"
            f"🆔 رقم الطلب: #{deposit_id}\n"
            f"⏰ الوقت: "
            f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"
        )
        return await self.notify_admin_photo(
            photo_file_id=photo_file_id,
            caption=caption,
            reply_markup=reply_markup,
        )

    async def notify_deposit_approved(
        self,
        user_telegram_id: int,
        amount_usd: str,
    ) -> None:
        """يرسل إشعار قبول الإيداع للمستخدم."""
        await self.notify_user(
            telegram_id=user_telegram_id,
            text=(
                "✅ <b>تم قبول طلب شحن رصيدك!</b>\n\n"
                f"💰 تمت إضافة <b>{amount_usd}$</b> إلى رصيدك.\n"
                "يمكنك الآن استخدام رصيدك لشراء الخدمات."
            ),
        )

    async def notify_deposit_rejected(
        self,
        user_telegram_id: int,
        reason: str | None = None,
    ) -> None:
        """يرسل إشعار رفض الإيداع للمستخدم."""
        text = (
            "❌ <b>تم رفض طلب شحن رصيدك</b>\n\n"
        )
        if reason:
            text += f"📝 السبب: {reason}\n\n"
        text += (
            "يرجى التأكد من صحة بيانات التحويل "
            "والمحاولة مجدداً، أو التواصل مع الدعم الفني."
        )
        await self.notify_user(
            telegram_id=user_telegram_id,
            text=text,
        )

    async def notify_order_completed(
        self,
        user_telegram_id: int,
        product_name: str,
        result_text: str,
    ) -> None:
        """يرسل إشعار اكتمال طلب للمستخدم."""
        await self.notify_user(
            telegram_id=user_telegram_id,
            text=(
                "✅ <b>تم تنفيذ طلبك بنجاح!</b>\n\n"
                f"🛒 المنتج: {product_name}\n\n"
                f"{result_text}"
            ),
        )

    async def notify_order_failed(
        self,
        user_telegram_id: int,
        product_name: str,
        amount_usd: str,
    ) -> None:
        """يرسل إشعار فشل طلب مع استرجاع الرصيد للمستخدم."""
        await self.notify_user(
            telegram_id=user_telegram_id,
            text=(
                "❌ <b>فشل تنفيذ طلبك</b>\n\n"
                f"🛒 المنتج: {product_name}\n"
                f"💰 تم استرجاع <b>{amount_usd}$</b> "
                "إلى رصيدك تلقائياً."
            ),
        )

    async def notify_insufficient_balance(
        self,
        user_telegram_id: int,
        required_usd: str,
        current_balance_usd: str,
        reply_markup=None,
    ) -> None:
        """يرسل إشعار رصيد غير كافٍ للمستخدم مع زر شحن الرصيد."""
        await self.notify_user(
            telegram_id=user_telegram_id,
            text=(
                "⚠️ <b>رصيدك غير كافٍ!</b>\n\n"
                f"💰 رصيدك الحالي: <b>{current_balance_usd}$</b>\n"
                f"💵 المبلغ المطلوب: <b>{required_usd}$</b>\n\n"
                "اشحن رصيدك للمتابعة."
            ),
            reply_markup=reply_markup,
        )

    async def notify_large_order_confirmation(
        self,
        user_telegram_id: int,
        product_name: str,
        amount_usd: str,
        reply_markup,
    ) -> None:
        """يطلب تأكيد الطلبات الكبيرة من المستخدم."""
        await self.notify_user(
            telegram_id=user_telegram_id,
            text=(
                "⚠️ <b>تأكيد الطلب</b>\n\n"
                f"🛒 المنتج: {product_name}\n"
                f"💰 المبلغ: <b>{amount_usd}$</b>\n\n"
                "هذا طلب بمبلغ كبير. هل أنت متأكد من المتابعة؟"
            ),
            reply_markup=reply_markup,
        )
