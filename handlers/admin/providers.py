"""
عرض معلومات مزودي الأرقام المبرمجين مسبقاً.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select

from database.models import ProviderStatus
from services.settings_service import SettingsService
from keyboards.admin import admin_back_kb
from filters.admin_filter import IsAdmin

router = Router(name="admin_providers")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "admin:providers")
async def providers_info(callback: CallbackQuery, session):
    result = await session.execute(select(ProviderStatus))
    providers = result.scalars().all()

    threshold = await SettingsService.get_decimal(
        "provider_low_balance_threshold"
    )

    text = "🌐 <b>مزودو الأرقام</b>\n\n"
    for p in providers:
        status_emoji = "🟢" if p.is_online else "🔴"
        balance_text = (
            f"{p.balance}$"
            if p.balance is not None
            else "غير معروف"
        )

        low_warning = ""
        if (
            p.balance is not None
            and p.is_online
            and p.balance < threshold
        ):
            low_warning = " ⚠️ رصيد منخفض!"

        text += (
            f"{status_emoji} <b>{p.provider.value}</b>\n"
            f"💰 الرصيد: {balance_text}{low_warning}\n"
            f"🕐 آخر تحديث: "
            f"{p.last_checked_at.strftime('%Y-%m-%d %H:%M') if p.last_checked_at else '—'}\n"
        )
        if p.last_error:
            text += f"⚠️ آخر خطأ: {p.last_error[:100]}\n"
        text += "\n"

    text += f"🚨 حد التنبيه: {threshold}$"

    await callback.message.edit_text(
        text, reply_markup=admin_back_kb()
    )
