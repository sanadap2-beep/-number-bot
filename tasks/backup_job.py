"""
مهمة البكاب اليومي لقاعدة البيانات.
تُرسل نسخة من قاعدة البيانات لقناة البكاب الخاصة.
"""
import logging
from datetime import datetime
from pathlib import Path

from services.notification_service import NotificationService

logger = logging.getLogger(__name__)


def _database_path() -> Path:
    """Resolve the SQLite path from DATABASE_URL for local and Docker runs."""
    from config import settings

    prefix = "sqlite+aiosqlite:///"
    if settings.DATABASE_URL.startswith(prefix):
        raw_path = settings.DATABASE_URL[len(prefix):]
        # Four slashes in a URL encode an absolute filesystem path.
        path = Path(raw_path)
        return path if path.is_absolute() else Path.cwd() / path
    return Path("bot_database.db")


async def daily_backup(bot):
    """
    يأخذ نسخة احتياطية من قاعدة البيانات
    ويرسلها لقناة البكاب.
    """
    notifier = NotificationService(bot)

    db_path = _database_path()
    if not db_path.exists() or not db_path.is_file():
        logger.warning(
            f"ملف قاعدة البيانات غير موجود: {db_path}"
        )
        return

    try:
        with db_path.open("rb") as f:
            db_bytes = f.read()

        file_size_mb = len(db_bytes) / (1024 * 1024)
        now = datetime.utcnow()
        filename = (
            f"backup_{now.strftime('%Y%m%d_%H%M%S')}.db"
        )

        caption = (
            f"💾 <b>نسخة احتياطية تلقائية</b>\n\n"
            f"📅 التاريخ: {now.strftime('%Y-%m-%d %H:%M')} UTC\n"
            f"📦 الحجم: {file_size_mb:.2f} MB\n"
            f"📂 الملف: {filename}"
        )

        success = await notifier.notify_backup_channel(
            document_bytes=db_bytes,
            filename=filename,
            caption=caption,
        )

        if success:
            logger.info(
                f"✅ تم إرسال البكاب بنجاح: {filename} "
                f"({file_size_mb:.2f} MB)"
            )
        else:
            logger.warning(
                "⚠️ فشل إرسال البكاب. "
                "تحقق من backup_channel_id في الإعدادات."
            )

    except Exception as e:
        logger.error(f"خطأ في مهمة البكاب: {e}")
