import logging
from aiogram.filters import BaseFilter

logger = logging.getLogger(__name__)


class IsAdmin(BaseFilter):
    async def __call__(self, event, db_user=None) -> bool:
        result = bool(db_user and db_user.is_admin)
        logger.info(
            f"🔍 DEBUG IsAdmin: db_user موجود؟ {db_user is not None} | "
            f"telegram_id={getattr(db_user, 'telegram_id', None)} | "
            f"is_admin={getattr(db_user, 'is_admin', None)} | النتيجة النهائية={result}"
        )
        return result
