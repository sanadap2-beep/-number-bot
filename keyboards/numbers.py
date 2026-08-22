"""
أزرار خدمة الأرقام.
تعمل مع النظام الديناميكي بالكامل.
"""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import Country, NumberService

COUNTRIES_PER_PAGE = 12


def number_services_kb(
    services: list[NumberService],
) -> InlineKeyboardMarkup:
    """قائمة خدمات الأرقام الديناميكية."""
    b = InlineKeyboardBuilder()
    for svc in services:
        b.button(
            text=f"{svc.emoji} أرقام {svc.name_ar}",
            callback_data=f"num_svc:{svc.code}",
        )
    b.button(
        text="🔙 رجوع للقائمة",
        callback_data="back_to_main",
    )
    b.adjust(2)
    return b.as_markup()


def countries_kb(
    service_code: str,
    countries: list[Country],
    page: int = 0,
) -> InlineKeyboardMarkup:
    """
    قائمة الدول مع Pagination.
    تعرض COUNTRIES_PER_PAGE دولة في كل صفحة.
    """
    b = InlineKeyboardBuilder()

    start = page * COUNTRIES_PER_PAGE
    end = start + COUNTRIES_PER_PAGE
    page_countries = countries[start:end]
    total_pages = (
        (len(countries) + COUNTRIES_PER_PAGE - 1)
        // COUNTRIES_PER_PAGE
    )

    for c in page_countries:
        b.button(
            text=f"{c.flag} {c.name_ar}",
            callback_data=(
                f"num_country:{service_code}:{c.code}"
            ),
        )

    # ── أزرار التنقل ──
    nav_buttons = []
    if page > 0:
        b.button(
            text="◀️ السابق",
            callback_data=(
                f"num_page:{service_code}:{page - 1}"
            ),
        )
        nav_buttons.append(1)
    if page < total_pages - 1:
        b.button(
            text="التالي ▶️",
            callback_data=(
                f"num_page:{service_code}:{page + 1}"
            ),
        )
        nav_buttons.append(1)

    b.button(
        text="🔙 رجوع",
        callback_data="back_to_main",
    )

    rows = [2] * (len(page_countries) // 2)
    if len(page_countries) % 2:
        rows.append(1)
    if nav_buttons:
        rows.append(len(nav_buttons))
    rows.append(1)

    b.adjust(*rows)
    return b.as_markup()


def confirm_purchase_kb(
    service_code: str,
    country_code: str,
) -> InlineKeyboardMarkup:
    """تأكيد شراء رقم مع عرض السعر."""
    b = InlineKeyboardBuilder()
    b.button(
        text="✅ تأكيد الشراء",
        callback_data=(
            f"num_confirm:{service_code}:{country_code}"
        ),
    )
    b.button(
        text="❌ إلغاء",
        callback_data="back_to_main",
    )
    b.adjust(1)
    return b.as_markup()


def order_actions_kb(order_id: int) -> InlineKeyboardMarkup:
    """أزرار أثناء انتظار الكود."""
    b = InlineKeyboardBuilder()
    b.button(
        text="🔄 تحديث",
        callback_data=f"num_refresh:{order_id}",
    )
    b.button(
        text="❌ إلغاء واسترجاع الرصيد",
        callback_data=f"num_cancel:{order_id}",
    )
    b.adjust(1)
    return b.as_markup()


def code_received_kb(
    order_id: int,
) -> InlineKeyboardMarkup:
    """تظهر بعد استلام الكود."""
    b = InlineKeyboardBuilder()
    b.button(
        text="🔄 انتظار كود إضافي",
        callback_data=f"num_extra:{order_id}",
    )
    b.button(
        text="✅ انتهيت",
        callback_data=f"num_finish:{order_id}",
    )
    b.adjust(1)
    return b.as_markup()
