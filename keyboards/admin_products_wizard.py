"""
كل أزرار Wizard إنشاء منتج جديد.

يدعم مسارين:
1) إنشاء سريع (افتراضيات ذكية)
2) إنشاء مخصص (كل الخيارات)
"""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import (
    ApiProvider,
    ProviderService,
)


# ══════════════ اختيار وضع الإنشاء ══════════════

def creation_mode_kb(
    sub_category_id: int,
) -> InlineKeyboardMarkup:
    """
    اختيار وضع إنشاء المنتج.
    - سريع: افتراضيات ذكية (اسم من الخدمة، ربح 50%)
    - مخصص: كل الخيارات (وصف، صورة، تسعير، عرض)
    - يدوي: بدون ربط مزود
    """
    b = InlineKeyboardBuilder()

    b.button(
        text="⚡ إنشاء سريع (افتراضيات ذكية)",
        callback_data=(
            f"admin:pw_mode:quick:{sub_category_id}"
        ),
    )
    b.button(
        text="🛠 إنشاء مخصص (كل الخيارات)",
        callback_data=(
            f"admin:pw_mode:custom:{sub_category_id}"
        ),
    )
    b.button(
        text="✋ إنشاء يدوي (بدون مزود)",
        callback_data=(
            f"admin:pw_mode:manual:{sub_category_id}"
        ),
    )
    b.button(
        text="🔙 رجوع",
        callback_data=f"admin:subcat_view:{sub_category_id}",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ اختيار المزود ══════════════

def select_provider_kb(
    providers: list[ApiProvider],
    sub_category_id: int,
) -> InlineKeyboardMarkup:
    """اختيار المزود لإنشاء منتج من خدماته."""
    b = InlineKeyboardBuilder()

    for p in providers:
        if not p.is_active:
            continue

        services_count = p.total_services or 0
        b.button(
            text=(
                f"🔌 {p.name} "
                f"({services_count} خدمة)"
            ),
            callback_data=f"admin:pw_prov:{p.id}",
        )

    b.button(
        text="🔙 رجوع",
        callback_data=(
            f"admin:prod_wizard_start:{sub_category_id}"
        ),
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ خيارات تصفح خدمات المزود ══════════════

def browse_services_options_kb(
    provider_id: int,
) -> InlineKeyboardMarkup:
    """خيارات تصفح خدمات المزود."""
    b = InlineKeyboardBuilder()

    b.button(
        text="📋 عرض كل الخدمات",
        callback_data=(
            f"admin:pw_svc_page:{provider_id}:0"
        ),
    )
    b.button(
        text="🔍 البحث في الخدمات",
        callback_data=(
            f"admin:pw_svc_search:{provider_id}"
        ),
    )
    b.button(
        text="📂 تصفية بالتصنيف",
        callback_data=(
            f"admin:pw_svc_cats:{provider_id}"
        ),
    )
    b.button(
        text="🔙 رجوع",
        callback_data="admin:pw_back_to_providers",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ اختيار تصنيف ══════════════

def select_category_filter_kb(
    provider_id: int,
    categories: list[tuple[str, int]],
    current_page: int = 0,
) -> InlineKeyboardMarkup:
    """اختيار تصنيف من تصنيفات المزود."""
    b = InlineKeyboardBuilder()

    CATS_PER_PAGE = 10
    start = current_page * CATS_PER_PAGE
    end = start + CATS_PER_PAGE
    page_cats = categories[start:end]
    total_pages = max(
        1,
        (len(categories) + CATS_PER_PAGE - 1) // CATS_PER_PAGE,
    )

    for cat_name, count in page_cats:
        display = cat_name
        if len(display) > 35:
            display = display[:32] + "..."
        b.button(
            text=f"📁 {display} ({count})",
            callback_data=(
                f"admin:pw_svc_cat:{provider_id}:"
                f"{hash(cat_name) % 1000000}"
            ),
        )

    nav_count = 0
    if current_page > 0:
        b.button(
            text="◀️ السابق",
            callback_data=(
                f"admin:pw_cats_page:{provider_id}:"
                f"{current_page - 1}"
            ),
        )
        nav_count += 1

    if total_pages > 1:
        b.button(
            text=f"📄 {current_page + 1}/{total_pages}",
            callback_data="noop",
        )
        nav_count += 1

    if current_page < total_pages - 1:
        b.button(
            text="التالي ▶️",
            callback_data=(
                f"admin:pw_cats_page:{provider_id}:"
                f"{current_page + 1}"
            ),
        )
        nav_count += 1

    b.button(
        text="🔙 رجوع",
        callback_data=(
            f"admin:pw_svc_options:{provider_id}"
        ),
    )

    rows = [1] * len(page_cats)
    if nav_count > 0:
        rows.append(nav_count)
    rows.append(1)
    b.adjust(*rows)
    return b.as_markup()


# ══════════════ عرض الخدمات مع Pagination ══════════════

SERVICES_WIZARD_PER_PAGE = 6


def wizard_services_kb(
    provider_id: int,
    services: list[ProviderService],
    current_page: int,
    total_count: int,
    search_query: str | None = None,
    category_filter: str | None = None,
) -> InlineKeyboardMarkup:
    """قائمة خدمات المزود لاختيار واحدة لإنشاء منتج."""
    b = InlineKeyboardBuilder()

    for svc in services:
        display_name = svc.name
        if len(display_name) > 45:
            display_name = display_name[:42] + "..."

        b.button(
            text=(
                f"#{svc.external_service_id} - "
                f"{display_name} - {svc.rate_usd:.4f}$"
            ),
            callback_data=f"admin:pw_pick:{svc.id}",
        )

    total_pages = max(
        1,
        (total_count + SERVICES_WIZARD_PER_PAGE - 1)
        // SERVICES_WIZARD_PER_PAGE,
    )

    nav_count = 0

    if current_page > 0:
        if search_query:
            cb = (
                f"admin:pw_search_page:{provider_id}:"
                f"{current_page - 1}"
            )
        elif category_filter:
            cb = (
                f"admin:pw_cat_page:{provider_id}:"
                f"{current_page - 1}"
            )
        else:
            cb = (
                f"admin:pw_svc_page:{provider_id}:"
                f"{current_page - 1}"
            )
        b.button(text="◀️ السابق", callback_data=cb)
        nav_count += 1

    b.button(
        text=f"📄 {current_page + 1}/{total_pages}",
        callback_data="noop",
    )
    nav_count += 1

    if current_page < total_pages - 1:
        if search_query:
            cb = (
                f"admin:pw_search_page:{provider_id}:"
                f"{current_page + 1}"
            )
        elif category_filter:
            cb = (
                f"admin:pw_cat_page:{provider_id}:"
                f"{current_page + 1}"
            )
        else:
            cb = (
                f"admin:pw_svc_page:{provider_id}:"
                f"{current_page + 1}"
            )
        b.button(text="التالي ▶️", callback_data=cb)
        nav_count += 1

    b.button(
        text="🔍 بحث جديد",
        callback_data=(
            f"admin:pw_svc_search:{provider_id}"
        ),
    )
    b.button(
        text="🔙 رجوع لخيارات التصفح",
        callback_data=(
            f"admin:pw_svc_options:{provider_id}"
        ),
    )

    rows = [1] * len(services)
    rows.append(nav_count)
    rows.append(1)
    rows.append(1)
    b.adjust(*rows)
    return b.as_markup()


# ══════════════ تأكيد اختيار خدمة ══════════════

def confirm_service_selection_kb(
    service_id: int,
    provider_id: int,
) -> InlineKeyboardMarkup:
    """تأكيد اختيار الخدمة قبل بدء الـ Wizard."""
    b = InlineKeyboardBuilder()

    b.button(
        text="✅ نعم، أنشئ منتج من هذه الخدمة",
        callback_data=f"admin:pw_confirm:{service_id}",
    )
    b.button(
        text="🔙 اختيار خدمة أخرى",
        callback_data=(
            f"admin:pw_svc_page:{provider_id}:0"
        ),
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ خيارات الصورة ══════════════

def wizard_image_options_kb() -> InlineKeyboardMarkup:
    """خيارات إضافة صورة للمنتج."""
    b = InlineKeyboardBuilder()

    b.button(
        text="📤 رفع صورة",
        callback_data="admin:pw_img:upload",
    )
    b.button(
        text="🔗 إدخال رابط صورة",
        callback_data="admin:pw_img:url",
    )
    b.button(
        text="⏭ بدون صورة",
        callback_data="admin:pw_img:skip",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ اختيار نوع التسعير ══════════════

def select_pricing_type_kb() -> InlineKeyboardMarkup:
    """اختيار نوع التسعير."""
    b = InlineKeyboardBuilder()

    b.button(
        text="💰 نسبة ربح % (موصى به)",
        callback_data="admin:pw_pricing:margin",
    )
    b.button(
        text="💵 سعر ثابت",
        callback_data="admin:pw_pricing:fixed",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ اختيار طريقة عرض السعر ══════════════

def select_wizard_display_type_kb(
    supports_quantity: bool = True,
) -> InlineKeyboardMarkup:
    """اختيار طريقة عرض السعر للمستخدم."""
    b = InlineKeyboardBuilder()

    if supports_quantity:
        b.button(
            text="📊 السعر لكل 1000 (SMM)",
            callback_data="admin:pw_display:per_1000",
        )
        b.button(
            text="📦 السعر للحد الأدنى",
            callback_data="admin:pw_display:per_min",
        )

    b.button(
        text="💵 سعر ثابت للطلب (ألعاب)",
        callback_data="admin:pw_display:fixed",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ استخدام حدود المزود أو تخصيص ══════════════

def quantity_limits_kb() -> InlineKeyboardMarkup:
    """استخدام حدود المزود أو تخصيصها."""
    b = InlineKeyboardBuilder()

    b.button(
        text="✅ استخدام حدود المزود",
        callback_data="admin:pw_qty:use_provider",
    )
    b.button(
        text="✏️ تعديل الحدود",
        callback_data="admin:pw_qty:customize",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ تأكيد إنشاء المنتج النهائي ══════════════

def confirm_creation_kb() -> InlineKeyboardMarkup:
    """تأكيد نهائي قبل إنشاء المنتج."""
    b = InlineKeyboardBuilder()

    b.button(
        text="✅ نعم، أنشئ المنتج الآن",
        callback_data="admin:pw_create_final",
    )
    b.button(
        text="❌ إلغاء (لن يُحفظ شيء)",
        callback_data="admin:pw_cancel",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ تخطي حقل ══════════════

def skip_field_kb(field_name: str) -> InlineKeyboardMarkup:
    """زر تخطي حقل اختياري."""
    b = InlineKeyboardBuilder()

    b.button(
        text="⏭ تخطي",
        callback_data=f"admin:pw_skip:{field_name}",
    )
    b.button(
        text="❌ إلغاء الـ Wizard",
        callback_data="admin:pw_cancel",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ زر إلغاء الـ Wizard ══════════════

def cancel_wizard_kb() -> InlineKeyboardMarkup:
    """زر إلغاء الـ Wizard في أي مرحلة."""
    b = InlineKeyboardBuilder()

    b.button(
        text="❌ إلغاء الـ Wizard",
        callback_data="admin:pw_cancel",
    )
    return b.as_markup()


# ══════════════ خيارات "منتج يدوي" ══════════════

def manual_product_requires_kb() -> InlineKeyboardMarkup:
    """
    في المنتج اليدوي: اختيار ما يحتاجه المستخدم.
    """
    b = InlineKeyboardBuilder()

    b.button(
        text="🎮 يحتاج آيدي لاعب",
        callback_data="admin:pw_manual_req:player_id",
    )
    b.button(
        text="🔗 يحتاج رابط",
        callback_data="admin:pw_manual_req:link",
    )
    b.button(
        text="📊 يحتاج كمية",
        callback_data="admin:pw_manual_req:quantity",
    )
    b.button(
        text="📦 لا يحتاج شيء (منتج ثابت)",
        callback_data="admin:pw_manual_req:none",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ بعد نجاح الإنشاء ══════════════

def after_creation_kb(
    product_id: int,
    sub_category_id: int,
) -> InlineKeyboardMarkup:
    """أزرار بعد نجاح إنشاء المنتج."""
    b = InlineKeyboardBuilder()

    b.button(
        text="👁 عرض المنتج",
        callback_data=f"admin:prod_view:{product_id}",
    )
    b.button(
        text="➕ إضافة منتج آخر",
        callback_data=(
            f"admin:prod_wizard_start:{sub_category_id}"
        ),
    )
    b.button(
        text="📦 عرض كل المنتجات",
        callback_data=f"admin:prod_list:{sub_category_id}",
    )
    b.button(
        text="🔙 رجوع للقسم الفرعي",
        callback_data=f"admin:subcat_view:{sub_category_id}",
    )
    b.adjust(1)
    return b.as_markup()
