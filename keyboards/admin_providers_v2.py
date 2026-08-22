"""
كل أزرار إدارة المزودين (V2 - محسّنة).
"""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import (
    ApiProvider,
    ProviderService,
)


# ══════════════ قائمة المزودين ══════════════

def providers_list_kb(
    providers: list[ApiProvider],
) -> InlineKeyboardMarkup:
    """قائمة كل المزودين المسجلين."""
    b = InlineKeyboardBuilder()

    for p in providers:
        status_icon = "🟢" if p.is_active else "🔴"
        type_emoji = {
            "smm": "📈",
            "games": "🎮",
            "numbers": "📞",
        }.get(p.type.value, "🔌")

        services_count = p.total_services or 0
        b.button(
            text=(
                f"{status_icon} {type_emoji} {p.name} "
                f"({services_count} خدمة)"
            ),
            callback_data=f"admin:aprov_view:{p.id}",
        )

    b.button(
        text="➕ إضافة مزود جديد",
        callback_data="admin:aprov_add",
    )
    b.button(
        text="🔙 رجوع",
        callback_data="admin:main",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ اختيار البروتوكول ══════════════

def select_protocol_kb() -> InlineKeyboardMarkup:
    """اختيار نوع البروتوكول عند إضافة مزود."""
    b = InlineKeyboardBuilder()

    b.button(
        text="📈 SMM V2 (رشق سوشيال) - قياسي ✅",
        callback_data="admin:aprov_proto:smm_v2",
    )
    b.button(
        text="🎮 Games (شحن ألعاب) - JSON ✅",
        callback_data="admin:aprov_proto:games_generic",
    )
    b.button(
        text="🛠 Custom JSON (مسارات وحقول قابلة للضبط) ✅",
        callback_data="admin:aprov_proto:custom",
    )
    b.button(
        text="🔙 رجوع",
        callback_data="admin:api_providers",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ اختيار نوع المزود ══════════════

def select_provider_type_kb() -> InlineKeyboardMarkup:
    """اختيار نوع المزود (SMM / Games / Apps)."""
    b = InlineKeyboardBuilder()

    b.button(
        text="📈 رشق سوشيال ميديا (SMM)",
        callback_data="admin:aprov_ptype:smm",
    )
    b.button(
        text="🎮 شحن ألعاب",
        callback_data="admin:aprov_ptype:games",
    )
    b.button(
        text="🔙 رجوع",
        callback_data="admin:api_providers",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ اختيار العملة ══════════════

COMMON_CURRENCIES = [
    ("USD", "🇺🇸 دولار"),
    ("EUR", "🇪🇺 يورو"),
    ("RUB", "🇷🇺 روبل"),
    ("TRY", "🇹🇷 ليرة تركية"),
    ("SAR", "🇸🇦 ريال سعودي"),
    ("AED", "🇦🇪 درهم إماراتي"),
    ("EGP", "🇪🇬 جنيه مصري"),
    ("SYP", "🇸🇾 ليرة سورية"),
    ("IQD", "🇮🇶 دينار عراقي"),
    ("CNY", "🇨🇳 يوان صيني"),
    ("INR", "🇮🇳 روبية هندية"),
    ("BRL", "🇧🇷 ريال برازيلي"),
]


def select_currency_kb() -> InlineKeyboardMarkup:
    """اختيار عملة المزود."""
    b = InlineKeyboardBuilder()

    for code, name in COMMON_CURRENCIES:
        b.button(
            text=name,
            callback_data=f"admin:aprov_curr:{code}",
        )

    b.button(
        text="✏️ عملة أخرى (يدوي)",
        callback_data="admin:aprov_curr:custom",
    )
    b.button(
        text="🔙 رجوع",
        callback_data="admin:api_providers",
    )
    b.adjust(2, 2, 2, 2, 2, 2, 1, 1)
    return b.as_markup()


# ══════════════ اختبار الاتصال بعد الإدخال ══════════════

def test_connection_kb() -> InlineKeyboardMarkup:
    """أزرار بعد إدخال بيانات المزود."""
    b = InlineKeyboardBuilder()

    b.button(
        text="🧪 اختبار الاتصال + حفظ",
        callback_data="admin:aprov_test",
    )
    b.button(
        text="❌ إلغاء",
        callback_data="admin:api_providers",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ سؤال سحب الخدمات ══════════════

def ask_sync_now_kb(provider_id: int) -> InlineKeyboardMarkup:
    """يسأل الأدمن هل يريد سحب الخدمات الآن."""
    b = InlineKeyboardBuilder()

    b.button(
        text="✅ نعم، اسحب الخدمات الآن",
        callback_data=f"admin:aprov_sync:{provider_id}",
    )
    b.button(
        text="⏰ لاحقاً",
        callback_data=f"admin:aprov_view:{provider_id}",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ تفاصيل المزود ══════════════

def provider_detail_kb(
    provider: ApiProvider,
) -> InlineKeyboardMarkup:
    """أزرار تفاصيل المزود المحسّنة."""
    b = InlineKeyboardBuilder()

    if provider.is_active:
        b.button(
            text="🔴 تعطيل المزود",
            callback_data=(
                f"admin:aprov_toggle:{provider.id}"
            ),
        )
    else:
        b.button(
            text="🟢 تفعيل المزود",
            callback_data=(
                f"admin:aprov_toggle:{provider.id}"
            ),
        )

    b.button(
        text="💰 تحديث الرصيد",
        callback_data=(
            f"admin:aprov_balance:{provider.id}"
        ),
    )
    b.button(
        text=(
            f"🔄 مزامنة الخدمات "
            f"({provider.total_services or 0})"
        ),
        callback_data=f"admin:aprov_sync:{provider.id}",
    )
    b.button(
        text="📋 عرض الخدمات",
        callback_data=(
            f"admin:aprov_services:{provider.id}:0"
        ),
    )
    b.button(
        text="🔍 البحث في الخدمات",
        callback_data=(
            f"admin:aprov_search:{provider.id}"
        ),
    )

    b.button(
        text="📝 تعديل الاسم",
        callback_data=(
            f"admin:aprov_edit_name:{provider.id}"
        ),
    )
    b.button(
        text="🔑 تعديل API Key",
        callback_data=(
            f"admin:aprov_edit_key:{provider.id}"
        ),
    )
    b.button(
        text="🔗 تعديل API URL",
        callback_data=(
            f"admin:aprov_edit_url:{provider.id}"
        ),
    )
    b.button(
        text="💱 تعديل سعر الصرف",
        callback_data=(
            f"admin:aprov_edit_rate:{provider.id}"
        ),
    )

    b.button(
        text="🗑 حذف المزود",
        callback_data=(
            f"admin:aprov_delete_confirm:{provider.id}"
        ),
    )
    b.button(
        text="🔙 رجوع لقائمة المزودين",
        callback_data="admin:api_providers",
    )

    b.adjust(1, 2, 1, 2, 2, 1, 1)
    return b.as_markup()


# ══════════════ تأكيد الحذف ══════════════

def confirm_delete_provider_kb(
    provider_id: int,
) -> InlineKeyboardMarkup:
    """تأكيد حذف مزود."""
    b = InlineKeyboardBuilder()

    b.button(
        text="⚠️ نعم، احذف نهائياً",
        callback_data=(
            f"admin:aprov_delete:{provider_id}"
        ),
    )
    b.button(
        text="🔙 لا، إلغاء",
        callback_data=(
            f"admin:aprov_view:{provider_id}"
        ),
    )
    b.adjust(1)
    return b.as_markup()
    # ══════════════ عرض الخدمات مع Pagination ══════════════

SERVICES_PER_PAGE = 8


def provider_services_kb(
    provider_id: int,
    services: list[ProviderService],
    current_page: int,
    total_count: int,
    search_query: str | None = None,
) -> InlineKeyboardMarkup:
    """
    قائمة خدمات المزود مع Pagination.
    """
    b = InlineKeyboardBuilder()

    for svc in services:
        display_name = svc.name
        if len(display_name) > 45:
            display_name = display_name[:42] + "..."

        price_display = f"{svc.rate_usd:.4f}$"
        b.button(
            text=(
                f"#{svc.external_service_id} - "
                f"{display_name} - {price_display}"
            ),
            callback_data=(
                f"admin:aprov_svc:{svc.id}"
            ),
        )

    total_pages = max(
        1,
        (total_count + SERVICES_PER_PAGE - 1)
        // SERVICES_PER_PAGE,
    )

    nav_buttons_count = 0

    if current_page > 0:
        prev_page = current_page - 1
        if search_query:
            cb = (
                f"admin:aprov_search_page:"
                f"{provider_id}:{prev_page}"
            )
        else:
            cb = (
                f"admin:aprov_services:"
                f"{provider_id}:{prev_page}"
            )
        b.button(text="◀️ السابق", callback_data=cb)
        nav_buttons_count += 1

    b.button(
        text=f"📄 {current_page + 1}/{total_pages}",
        callback_data="noop",
    )
    nav_buttons_count += 1

    if current_page < total_pages - 1:
        next_page = current_page + 1
        if search_query:
            cb = (
                f"admin:aprov_search_page:"
                f"{provider_id}:{next_page}"
            )
        else:
            cb = (
                f"admin:aprov_services:"
                f"{provider_id}:{next_page}"
            )
        b.button(text="التالي ▶️", callback_data=cb)
        nav_buttons_count += 1

    b.button(
        text="🔍 بحث جديد",
        callback_data=(
            f"admin:aprov_search:{provider_id}"
        ),
    )
    b.button(
        text="🔙 رجوع للمزود",
        callback_data=(
            f"admin:aprov_view:{provider_id}"
        ),
    )

    rows = [1] * len(services)
    rows.append(nav_buttons_count)
    rows.append(1)
    rows.append(1)
    b.adjust(*rows)

    return b.as_markup()


# ══════════════ تفاصيل خدمة معينة ══════════════

def provider_service_detail_kb(
    service: ProviderService,
) -> InlineKeyboardMarkup:
    """أزرار تفاصيل خدمة معينة."""
    b = InlineKeyboardBuilder()

    b.button(
        text="➕ إنشاء منتج من هذه الخدمة",
        callback_data=(
            f"admin:aprov_create_product:{service.id}"
        ),
    )
    b.button(
        text="📋 المنتجات المرتبطة",
        callback_data=(
            f"admin:aprov_svc_products:{service.id}"
        ),
    )
    b.button(
        text=(
            "🔙 رجوع لخدمات المزود"
        ),
        callback_data=(
            f"admin:aprov_services:"
            f"{service.api_provider_id}:0"
        ),
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ إلغاء البحث ══════════════

def cancel_search_kb(
    provider_id: int,
) -> InlineKeyboardMarkup:
    """زر إلغاء أثناء إدخال البحث."""
    b = InlineKeyboardBuilder()

    b.button(
        text="❌ إلغاء",
        callback_data=(
            f"admin:aprov_view:{provider_id}"
        ),
    )
    return b.as_markup()


# ══════════════ عرض التزامن الجاري ══════════════

def sync_in_progress_kb(
    provider_id: int,
) -> InlineKeyboardMarkup:
    """يظهر أثناء التزامن (زر واحد للرجوع)."""
    b = InlineKeyboardBuilder()

    b.button(
        text="🔙 رجوع",
        callback_data=(
            f"admin:aprov_view:{provider_id}"
        ),
    )
    return b.as_markup()
