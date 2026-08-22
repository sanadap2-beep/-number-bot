"""العروض الحية للمستخدمين."""
from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery

from keyboards.promotions import promotions_kb
from services.promotion_service import PromotionService

router = Router(name="promotions")


def _discount_text(promotion) -> str:
    if promotion.discount_type.value == "percent":
        return f"{promotion.discount_value:g}%"
    return f"{promotion.discount_value:g}$"


@router.callback_query(F.data == "menu:promotions")
async def promotions_page(callback: CallbackQuery, session):
    promotions = await PromotionService.get_active_promotions(session)
    await callback.answer()
    if not promotions:
        await callback.message.edit_text(
            "🔥 <b>العروض الحية</b>\n\n"
            "لا توجد عروض فعالة الآن. تابع البوت ليصلك الجديد!",
            reply_markup=promotions_kb([]),
        )
        return

    lines = ["🔥 <b>العروض الحية</b>\n"]
    for promotion in promotions:
        name = promotion.product.name_ar if promotion.product else promotion.name
        lines.append(
            f"🔥 <b>{escape(promotion.name)}</b> — "
            f"{escape(name)} — خصم {_discount_text(promotion)}"
        )
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=promotions_kb(promotions),
    )
