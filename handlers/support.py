"""
الدعم الفني.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from services.settings_service import SettingsService
from keyboards.main_menu import back_to_main_kb

router = Router(name="support")


@router.message(F.text == "🛠 الدعم الفني")
async def support_handler(message: Message):
    await _send_support(message)


@router.callback_query(F.data == "menu:support")
async def support_handler_cb(callback: CallbackQuery):
    await callback.answer()
    await _send_support(callback.message)


async def _send_support(message: Message):
    support_username = await SettingsService.get(
        "support_username", "@support"
    )
    await message.answer(
        f"🛠 <b>الدعم الفني</b>\n\n"
        f"للتواصل مع فريق الدعم اضغط: "
        f"{support_username}\n\n"
        "⏰ أوقات الاستجابة: خلال 24 ساعة",
        reply_markup=back_to_main_kb(),
    )
