"""
القائمة الرئيسية الديناميكية.
تُبنى تلقائياً من:
1) خدمات الأرقام المفعلة (جدول number_services)
2) الأقسام المفعلة (جدول categories)
3) أزرار ثابتة (شحن رصيد، حسابي، إلخ)
"""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import NumberService, Category


def build_main_menu(
    number_services: list[NumberService],
    categories: list[Category],
    balance_usd: str = "0.00",
) -> InlineKeyboardMarkup:
    """
    يبني القائمة الرئيسية ديناميكياً.
    number_services: خدمات الأرقام المفعلة من DB
    categories: الأقسام الرئيسية المفعلة من DB
    balance_usd: رصيد المستخدم لعرضه
    """
    b = InlineKeyboardBuilder()

    # ── خدمات الأرقام الديناميكية ──
    for svc in number_services:
        b.button(
            text=f"{svc.emoji} أرقام {svc.name_ar}",
            callback_data=f"num_svc:{svc.code}",
        )

    # ── الأقسام الرئيسية الديناميكية ──
    for cat in categories:
        b.button(
            text=f"{cat.emoji} {cat.name_ar}",
            callback_data=f"cat:{cat.id}",
        )

    # ── أزرار ثابتة ──
    b.button(
        text="💰 شحن الرصيد",
        callback_data="menu:deposit",
    )
    b.button(
        text=f"👤 حسابي ({balance_usd}$)",
        callback_data="menu:account",
    )
    b.button(
        text="💎 دعوة أصدقاء",
        callback_data="menu:referral",
    )
    b.button(
        text="🔄 تحويل رصيد",
        callback_data="menu:transfer",
    )
    b.button(
        text="🔎 البحث عن خدمة",
        callback_data="menu:search",
    )
    b.button(
        text="⭐ المفضلة",
        callback_data="menu:favorites",
    )
    b.button(
        text="🎁 الولاء والمكافآت",
        callback_data="menu:loyalty",
    )
    b.button(
        text="🔥 العروض الحية",
        callback_data="menu:promotions",
    )
    b.button(
        text="📣 اطلب خدمة",
        callback_data="menu:product_request",
    )
    b.button(
        text="🎁 بطاقة هدية",
        callback_data="menu:gift",
    )
    b.button(
        text="🧠 المساعد الذكي",
        callback_data="menu:assistant",
    )
    b.button(
        text="📡 حالة الخدمات",
        callback_data="menu:status",
    )
    b.button(
        text="🛠 الدعم الفني",
        callback_data="menu:support",
    )

    # ── ترتيب الأزرار ──
    num_svc_count = len(number_services)
    cat_count = len(categories)

    rows = []
    if num_svc_count > 0:
        rows.append(min(num_svc_count, 2))
        if num_svc_count > 2:
            rows.append(min(num_svc_count - 2, 2))
    if cat_count > 0:
        remaining = cat_count
        while remaining > 0:
            rows.append(min(remaining, 2))
            remaining -= 2

    rows.extend([2, 2, 2, 2, 2, 2, 1])
    b.adjust(*rows)

    return b.as_markup()


def deposit_menu_kb(
    shamcash_manual_enabled: bool = True,
    stars_enabled: bool = True,
    usdt_manual_enabled: bool = True,
    shamcash_auto_enabled: bool = True,
    usdt_auto_enabled: bool = True,
    other_enabled: bool = True,
) -> InlineKeyboardMarkup:
    """
    قائمة طرق شحن الرصيد (6 طرق).
    كل طريقة تظهر فقط إذا كانت مفعلة من لوحة الأدمن.
    """
    b = InlineKeyboardBuilder()

    if shamcash_manual_enabled:
        b.button(
            text="💵 شام كاش يدوي",
            callback_data="deposit:shamcash_manual",
        )

    if stars_enabled:
        b.button(
            text="⭐ نجوم تليجرام",
            callback_data="deposit:stars",
        )

    if shamcash_auto_enabled:
        b.button(
            text="💳 شام كاش تلقائي",
            callback_data="deposit:shamcash_auto",
        )

    if usdt_auto_enabled:
        b.button(
            text="₮ USDT تلقائي",
            callback_data="deposit:usdt_auto",
        )

    if usdt_manual_enabled:
        b.button(
            text="₮ USDT يدوي",
            callback_data="deposit:usdt_manual",
        )

    if other_enabled:
        b.button(
            text="📞 طرق دفع أخرى",
            callback_data="deposit:other",
        )

    b.button(
        text="🔙 رجوع للقائمة الرئيسية",
        callback_data="back_to_main",
    )

    b.adjust(2, 2, 2, 1)
    return b.as_markup()


def stars_packages_kb(
    packages: list,
) -> InlineKeyboardMarkup:
    """قائمة باقات النجوم المتاحة."""
    b = InlineKeyboardBuilder()
    for pkg in packages:
        b.button(
            text=f"{pkg.label} = {pkg.usd_amount}$",
            callback_data=f"stars_buy:{pkg.id}",
        )
    b.button(
        text="🔙 رجوع",
        callback_data="menu:deposit",
    )
    b.adjust(2)
    return b.as_markup()


def insufficient_balance_kb() -> InlineKeyboardMarkup:
    """زر شحن الرصيد عند عدم كفاية الرصيد."""
    b = InlineKeyboardBuilder()
    b.button(
        text="💰 شحن رصيد الآن",
        callback_data="menu:deposit",
    )
    b.button(
        text="🔙 رجوع للقائمة",
        callback_data="back_to_main",
    )
    b.adjust(1)
    return b.as_markup()


def confirm_large_order_kb(
    confirm_data: str,
) -> InlineKeyboardMarkup:
    """تأكيد الطلبات الكبيرة."""
    b = InlineKeyboardBuilder()
    b.button(
        text="✅ نعم، متأكد",
        callback_data=confirm_data,
    )
    b.button(
        text="❌ إلغاء",
        callback_data="back_to_main",
    )
    b.adjust(2)
    return b.as_markup()


def back_to_main_kb() -> InlineKeyboardMarkup:
    """زر رجوع للقائمة الرئيسية فقط."""
    b = InlineKeyboardBuilder()
    b.button(
        text="🔙 رجوع للقائمة الرئيسية",
        callback_data="back_to_main",
    )
    return b.as_markup()
