"""
كل أزرار إدارة المنتجات.
"""
from decimal import Decimal

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import Product, ProductStatus


# ══════════════ قائمة المنتجات ══════════════

PRODUCTS_PER_PAGE = 8


def products_list_kb(
    sub_category_id: int,
    products: list[Product],
    current_page: int = 0,
    total_count: int = 0,
) -> InlineKeyboardMarkup:
    """قائمة منتجات قسم فرعي مع Pagination."""
    b = InlineKeyboardBuilder()

    for p in products:
        status_icon = (
            "🟢" if p.status == ProductStatus.ACTIVE
            else "🔴"
        )
        featured = "⭐" if p.is_featured else ""
        bestseller = "🔥" if p.is_bestseller else ""

        display_name = p.name_ar
        if len(display_name) > 40:
            display_name = display_name[:37] + "..."

        b.button(
            text=(
                f"{status_icon}{featured}{bestseller} "
                f"{display_name} - {p.price_usd}$"
            ),
            callback_data=f"admin:prod_view:{p.id}",
        )

    total_pages = max(
        1,
        (total_count + PRODUCTS_PER_PAGE - 1)
        // PRODUCTS_PER_PAGE,
    )

    nav_count = 0
    if current_page > 0:
        b.button(
            text="◀️ السابق",
            callback_data=(
                f"admin:prod_page:{sub_category_id}:"
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
                f"admin:prod_page:{sub_category_id}:"
                f"{current_page + 1}"
            ),
        )
        nav_count += 1

    b.button(
        text="➕ إضافة منتج جديد",
        callback_data=(
            f"admin:prod_wizard_start:{sub_category_id}"
        ),
    )
    b.button(
        text="🔙 رجوع للقسم الفرعي",
        callback_data=f"admin:subcat_view:{sub_category_id}",
    )

    rows = [1] * len(products)
    if nav_count > 0:
        rows.append(nav_count)
    rows.append(1)
    rows.append(1)
    b.adjust(*rows)

    return b.as_markup()


# ══════════════ تفاصيل المنتج ══════════════

def product_detail_kb(
    product: Product,
) -> InlineKeyboardMarkup:
    """أزرار تفاصيل المنتج."""
    b = InlineKeyboardBuilder()

    if product.status == ProductStatus.ACTIVE:
        b.button(
            text="🔴 تعطيل المنتج",
            callback_data=f"admin:prod_toggle:{product.id}",
        )
    else:
        b.button(
            text="🟢 تفعيل المنتج",
            callback_data=f"admin:prod_toggle:{product.id}",
        )

    if product.is_featured:
        b.button(
            text="⭐ إلغاء تمييز",
            callback_data=(
                f"admin:prod_toggle_featured:{product.id}"
            ),
        )
    else:
        b.button(
            text="⭐ تمييز المنتج",
            callback_data=(
                f"admin:prod_toggle_featured:{product.id}"
            ),
        )

    if product.is_bestseller:
        b.button(
            text="🔥 إلغاء الأكثر مبيعاً",
            callback_data=(
                f"admin:prod_toggle_bestseller:{product.id}"
            ),
        )
    else:
        b.button(
            text="🔥 الأكثر مبيعاً",
            callback_data=(
                f"admin:prod_toggle_bestseller:{product.id}"
            ),
        )

    b.button(
        text="💰 تعديل السعر",
        callback_data=f"admin:prod_edit:price:{product.id}",
    )
    b.button(
        text="✏️ تعديل الاسم",
        callback_data=f"admin:prod_edit:name:{product.id}",
    )
    b.button(
        text="📝 تعديل الوصف",
        callback_data=f"admin:prod_edit:desc:{product.id}",
    )

    b.button(
        text="🖼 تعديل الصورة",
        callback_data=f"admin:prod_edit:image:{product.id}",
    )
    b.button(
        text="📊 تعديل الحدود",
        callback_data=(
            f"admin:prod_edit:limits:{product.id}"
        ),
    )
    b.button(
        text="🎨 طريقة عرض السعر",
        callback_data=(
            f"admin:prod_edit:display:{product.id}"
        ),
    )
    b.button(
        text="🔢 تعديل الترتيب",
        callback_data=f"admin:prod_edit:sort:{product.id}",
    )

    b.button(
        text="📊 إحصائيات المنتج",
        callback_data=f"admin:prod_stats:{product.id}",
    )

    b.button(
        text="🗑 حذف المنتج",
        callback_data=(
            f"admin:prod_delete_confirm:{product.id}"
        ),
    )
    b.button(
        text="🔙 رجوع لقائمة المنتجات",
        callback_data=(
            f"admin:prod_list:{product.sub_category_id}"
        ),
    )

    b.adjust(1, 2, 3, 2, 2, 1, 1, 1)
    return b.as_markup()


# ══════════════ اختيار طريقة عرض السعر ══════════════

def select_display_type_kb(
    product_id: int,
) -> InlineKeyboardMarkup:
    """اختيار طريقة عرض السعر للمستخدم."""
    b = InlineKeyboardBuilder()

    b.button(
        text="📊 السعر لكل 1000",
        callback_data=(
            f"admin:prod_display:per_1000:{product_id}"
        ),
    )
    b.button(
        text="📦 السعر للحد الأدنى",
        callback_data=(
            f"admin:prod_display:per_min:{product_id}"
        ),
    )
    b.button(
        text="💵 سعر ثابت للطلب",
        callback_data=(
            f"admin:prod_display:fixed:{product_id}"
        ),
    )
    b.button(
        text="🔙 رجوع",
        callback_data=f"admin:prod_view:{product_id}",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ تأكيد تغيير السعر الكبير ══════════════

def confirm_price_change_kb(
    product_id: int,
    new_price: Decimal,
) -> InlineKeyboardMarkup:
    """تأكيد تغيير سعر كبير (>50% تغيير)."""
    b = InlineKeyboardBuilder()

    b.button(
        text="⚠️ نعم، غيّر السعر",
        callback_data=(
            f"admin:prod_confirm_price:{product_id}:"
            f"{new_price}"
        ),
    )
    b.button(
        text="❌ لا، إلغاء",
        callback_data=f"admin:prod_view:{product_id}",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ تأكيد حذف منتج ══════════════

def confirm_delete_product_kb(
    product_id: int,
) -> InlineKeyboardMarkup:
    """تأكيد حذف منتج."""
    b = InlineKeyboardBuilder()

    b.button(
        text="⚠️ نعم، احذف نهائياً",
        callback_data=f"admin:prod_delete:{product_id}",
    )
    b.button(
        text="🔙 لا، إلغاء",
        callback_data=f"admin:prod_view:{product_id}",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ إلغاء تعديل ══════════════

def cancel_edit_kb(product_id: int) -> InlineKeyboardMarkup:
    """زر إلغاء أثناء التعديل."""
    b = InlineKeyboardBuilder()
    b.button(
        text="❌ إلغاء",
        callback_data=f"admin:prod_view:{product_id}",
    )
    return b.as_markup()
