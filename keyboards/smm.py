"""
أزرار رشق السوشيال ميديا.
تُبنى ديناميكياً من قاعدة البيانات.
نفس بنية أزرار الألعاب لأنها تعتمد على نفس النظام
(categories → sub_categories → products).
"""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import SubCategory, Product


def smm_platforms_kb(
    category_id: int,
    sub_categories: list[SubCategory],
) -> InlineKeyboardMarkup:
    """قائمة منصات السوشيال ميديا."""
    b = InlineKeyboardBuilder()
    for sub in sub_categories:
        b.button(
            text=f"{sub.emoji} {sub.name_ar}",
            callback_data=f"subcat:{sub.id}",
        )
    b.button(
        text="🔙 رجوع للقائمة",
        callback_data="back_to_main",
    )
    b.adjust(2)
    return b.as_markup()


def smm_services_kb(
    sub_category_id: int,
    products: list[Product],
    category_id: int,
) -> InlineKeyboardMarkup:
    """قائمة خدمات الرشق مع الأسعار والكميات."""
    b = InlineKeyboardBuilder()
    for p in products:
        if p.requires_quantity:
            price_text = f"{p.price_usd}$ / {p.min_quantity}"
            b.button(
                text=f"{p.name_ar} - {price_text}",
                callback_data=f"prod:{p.id}",
            )
        else:
            b.button(
                text=f"{p.name_ar} - {p.price_usd}$",
                callback_data=f"prod:{p.id}",
            )
    b.button(
        text="🔙 رجوع",
        callback_data=f"cat:{category_id}",
    )
    b.adjust(1)
    return b.as_markup()


def smm_confirm_kb(
    product_id: int,
    sub_category_id: int,
) -> InlineKeyboardMarkup:
    """تأكيد طلب رشق."""
    b = InlineKeyboardBuilder()
    b.button(
        text="✅ تأكيد الطلب",
        callback_data=f"prod_confirm:{product_id}",
    )
    b.button(
        text="🎟 لدي كوبون خصم",
        callback_data=f"prod_coupon:{product_id}",
    )
    b.button(
        text="🔙 رجوع",
        callback_data=f"subcat:{sub_category_id}",
    )
    b.adjust(1)
    return b.as_markup()
