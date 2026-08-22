"""
صفحة حساب المستخدم.
تعرض الرصيد بالدولار، الطلبات، سجل المعاملات.
"""
from html import escape

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from database.models import (
    User, NumberOrder, UnifiedOrder, DigitalInventoryItem,
    OrderStatus, UnifiedOrderStatus
)
from services.balance_service import BalanceService
from services.cashback_service import CashbackService
from services.inventory_service import InventoryError, InventoryService

router = Router(name="account")

ORDER_STATUS_LABELS = {
    OrderStatus.PENDING: "⏳ قيد الانتظار",
    OrderStatus.CODE_RECEIVED: "✅ وصل الكود",
    OrderStatus.COMPLETED: "✅ مكتمل",
    OrderStatus.EXPIRED: "⌛ انتهت الصلاحية",
    OrderStatus.CANCELLED: "❌ ملغى",
    OrderStatus.REFUNDED: "↩️ مسترجَع",
}

UNIFIED_STATUS_LABELS = {
    UnifiedOrderStatus.PENDING: "⏳ قيد الانتظار",
    UnifiedOrderStatus.PROCESSING: "🔄 قيد التنفيذ",
    UnifiedOrderStatus.COMPLETED: "✅ مكتمل",
    UnifiedOrderStatus.FAILED: "❌ فشل",
    UnifiedOrderStatus.REFUNDED: "↩️ مسترجَع",
    UnifiedOrderStatus.PARTIAL: "⚠️ جزئي",
}

TRANSACTION_TYPE_LABELS = {
    "deposit": "💰 إيداع",
    "purchase": "🛒 شراء",
    "refund": "↩️ استرجاع",
    "referral_bonus": "💎 مكافأة إحالة",
    "transfer_in": "📥 تحويل وارد",
    "transfer_out": "📤 تحويل صادر",
    "admin_add": "➕ إضافة (أدمن)",
    "admin_deduct": "➖ خصم (أدمن)",
    "cashback": "🎁 كاشباك",
    "stars_deposit": "⭐ نجوم تليجرام",
    "coupon_bonus": "🎟 كوبون",
    "loyalty_redeem": "🎁 استبدال نقاط الولاء",
}


def _account_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 طلبات الأرقام", callback_data="my_num_orders:0")
    kb.button(text="🛒 طلبات أخرى", callback_data="my_uni_orders:0")
    kb.button(text="📊 سجل المعاملات", callback_data="my_transactions:0")
    kb.button(text="🔙 رجوع للقائمة", callback_data="back_to_main")
    kb.adjust(2, 1, 1)
    return kb


@router.message(F.text == "👤 حسابي")
async def account_handler(
    message: Message, session, db_user: User
):
    await _send_account(message, session, db_user)


@router.callback_query(F.data == "menu:account")
async def account_handler_cb(
    callback: CallbackQuery, session, db_user: User
):
    await callback.answer()
    await _send_account(callback.message, session, db_user)


async def _send_account(
    message: Message, session, db_user: User
):
    result = await session.execute(
        select(func.count(User.id)).where(
            User.referrer_id == db_user.id
        )
    )
    referrals_count = result.scalar_one()

    total_cashback = await CashbackService.get_user_total_cashback(
        session, db_user.id
    )

    kb = _account_kb()

    await message.answer(
        "👤 <b>حسابي</b>\n\n"
        f"🆔 آيديك: <code>{db_user.telegram_id}</code>\n"
        f"💰 رصيدك: <b>{db_user.balance:.2f}$</b>\n"
        f"🛒 إجمالي مشترياتك: <b>{db_user.total_spent_usd:.2f}$</b>\n"
        f"📦 عدد الطلبات: <b>{db_user.total_orders}</b>\n"
        f"🎁 كاشباك محصّل: <b>{total_cashback:.4f}$</b>\n"
        f"💎 نقاط الولاء: <b>{db_user.loyalty_points}</b>\n"
        f"👥 عدد إحالاتك: <b>{referrals_count}</b>\n"
        f"📅 تاريخ انضمامك: {db_user.joined_at.strftime('%Y-%m-%d')}",
        reply_markup=kb.as_markup(),
    )


# ══════════════ طلبات الأرقام ══════════════

@router.callback_query(F.data.startswith("my_num_orders:"))
async def my_number_orders(
    callback: CallbackQuery, session, db_user: User
):
    page = int(callback.data.split(":")[1])
    per_page = 5

    result = await session.execute(
        select(NumberOrder)
        .where(NumberOrder.user_id == db_user.id)
        .order_by(desc(NumberOrder.purchased_at))
        .limit(per_page)
        .offset(page * per_page)
    )
    orders = result.scalars().all()

    total_result = await session.execute(
        select(func.count(NumberOrder.id)).where(
            NumberOrder.user_id == db_user.id
        )
    )
    total = total_result.scalar_one()
    total_pages = max(1, (total + per_page - 1) // per_page)

    if not orders and page == 0:
        await callback.message.edit_text(
            "📋 لا يوجد لديك طلبات أرقام بعد.",
        )
        await callback.answer()
        return

    lines = [f"📋 <b>طلبات الأرقام ({page + 1}/{total_pages})</b>\n"]
    for o in orders:
        status_label = ORDER_STATUS_LABELS.get(
            o.status, o.status.value
        )
        line = (
            f"\n📱 <code>{o.phone_number}</code>\n"
            f"📲 الخدمة: {o.service}\n"
            f"الحالة: {status_label} | السعر: {o.price_sell_usd}$\n"
            f"التاريخ: {o.purchased_at.strftime('%Y-%m-%d %H:%M')}"
        )
        if o.sms_code:
            line += f"\n🔑 الكود: <code>{o.sms_code}</code>"
        if o.extra_codes:
            line += f"\n🔑 أكواد إضافية: <code>{o.extra_codes}</code>"
        lines.append(line)

    kb = InlineKeyboardBuilder()
    if page > 0:
        kb.button(text="◀️ السابق", callback_data=f"my_num_orders:{page - 1}")
    if page < total_pages - 1:
        kb.button(text="التالي ▶️", callback_data=f"my_num_orders:{page + 1}")
    kb.button(text="🔙 رجوع لحسابي", callback_data="menu:account")
    kb.adjust(2, 1)

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


# ══════════════ طلبات الألعاب/التطبيقات/SMM ══════════════

@router.callback_query(F.data.startswith("my_uni_orders:"))
async def my_unified_orders(
    callback: CallbackQuery, session, db_user: User
):
    page = int(callback.data.split(":")[1])
    per_page = 5

    result = await session.execute(
        select(UnifiedOrder)
        .options(selectinload(UnifiedOrder.product))
        .where(UnifiedOrder.user_id == db_user.id)
        .order_by(desc(UnifiedOrder.created_at))
        .limit(per_page)
        .offset(page * per_page)
    )
    orders = result.scalars().all()

    total_result = await session.execute(
        select(func.count(UnifiedOrder.id)).where(
            UnifiedOrder.user_id == db_user.id
        )
    )
    total = total_result.scalar_one()
    total_pages = max(1, (total + per_page - 1) // per_page)

    if not orders and page == 0:
        await callback.message.edit_text(
            "🛒 لا يوجد لديك طلبات ألعاب/تطبيقات/رشق بعد.",
        )
        await callback.answer()
        return

    lines = [f"🛒 <b>طلبات أخرى ({page + 1}/{total_pages})</b>\n"]
    for o in orders:
        status_label = UNIFIED_STATUS_LABELS.get(
            o.status, o.status.value
        )
        product_name = "—"
        if o.product:
            product_name = o.product.name_ar

        line = (
            f"\n🆔 #{o.id}\n"
            f"📦 المنتج: {product_name}\n"
            f"الحالة: {status_label} | السعر: {o.price_usd}$\n"
            f"التاريخ: {o.created_at.strftime('%Y-%m-%d %H:%M')}"
        )
        if o.target:
            line += f"\n🎯 الهدف: <code>{o.target}</code>"
        lines.append(line)

    kb = InlineKeyboardBuilder()
    for order in orders:
        kb.button(
            text=f"🔎 تفاصيل الطلب #{order.id}",
            callback_data=f"my_uni_order:{order.id}",
        )
    if page > 0:
        kb.button(text="◀️ السابق", callback_data=f"my_uni_orders:{page - 1}")
    if page < total_pages - 1:
        kb.button(text="التالي ▶️", callback_data=f"my_uni_orders:{page + 1}")
    kb.button(text="🔙 رجوع لحسابي", callback_data="menu:account")
    kb.adjust(1, 2, 1)

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("my_uni_order:"))
async def unified_order_detail(
    callback: CallbackQuery,
    session,
    db_user: User,
):
    order_id = int(callback.data.split(":")[1])
    result = await session.execute(
        select(UnifiedOrder)
        .options(selectinload(UnifiedOrder.product))
        .where(
            UnifiedOrder.id == order_id,
            UnifiedOrder.user_id == db_user.id,
        )
    )
    order = result.scalar_one_or_none()
    if order is None:
        await callback.answer("⚠️ الطلب غير موجود.", show_alert=True)
        return

    status_label = UNIFIED_STATUS_LABELS.get(
        order.status, getattr(order.status, "value", str(order.status))
    )
    product_name = order.product.name_ar if order.product else "—"
    text = (
        f"🛒 <b>تفاصيل الطلب #{order.id}</b>\n\n"
        f"📦 المنتج: <b>{product_name}</b>\n"
        f"📊 الحالة: {status_label}\n"
        f"💰 المبلغ: <b>{order.price_usd}$</b>\n"
        f"🎯 الهدف: <code>{order.target or '—'}</code>\n"
        f"📊 الكمية: {order.quantity}\n"
        f"🆔 رقم المزود: <code>{order.external_order_id or '—'}</code>\n"
        f"📝 الحالة التفصيلية: {order.status_message or '—'}\n"
        f"📅 التاريخ: {order.created_at.strftime('%Y-%m-%d %H:%M')}"
    )
    if order.remains is not None:
        text += f"\n⏳ المتبقي: {order.remains}"

    delivery_result = await session.execute(
        select(DigitalInventoryItem).where(
            DigitalInventoryItem.unified_order_id == order.id
        )
    )
    delivery_item = delivery_result.scalar_one_or_none()
    if delivery_item is not None:
        try:
            delivery_value = InventoryService.decrypt_value(
                delivery_item.encrypted_value
            )
            text += (
                "\n\n🎁 <b>بيانات التسليم:</b>\n"
                f"<code>{escape(delivery_value)}</code>"
            )
        except InventoryError:
            text += "\n\n⚠️ تعذر عرض بيانات التسليم حالياً."

    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 رجوع للطلبات", callback_data="my_uni_orders:0")
    kb.button(text="🏠 القائمة الرئيسية", callback_data="back_to_main")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())
    await callback.answer()


# ══════════════ سجل المعاملات المالية ══════════════

@router.callback_query(F.data.startswith("my_transactions:"))
async def my_transactions(
    callback: CallbackQuery, session, db_user: User
):
    page = int(callback.data.split(":")[1])
    per_page = 8

    transactions = await BalanceService.get_transactions(
        session, db_user.id,
        limit=per_page,
        offset=page * per_page,
    )

    from sqlalchemy import select as sa_select, func as sa_func
    from database.models import Transaction
    total_result = await session.execute(
        sa_select(sa_func.count(Transaction.id)).where(
            Transaction.user_id == db_user.id
        )
    )
    total = total_result.scalar_one()
    total_pages = max(1, (total + per_page - 1) // per_page)

    if not transactions and page == 0:
        await callback.message.edit_text(
            "📊 لا يوجد لديك معاملات مالية بعد.",
        )
        await callback.answer()
        return

    lines = [
        f"📊 <b>سجل المعاملات ({page + 1}/{total_pages})</b>\n"
    ]
    for tx in transactions:
        tx_label = TRANSACTION_TYPE_LABELS.get(
            tx.type.value, tx.type.value
        )
        sign = "+" if tx.amount > 0 else ""
        line = (
            f"\n{tx_label}\n"
            f"المبلغ: {sign}{tx.amount:.4f}$\n"
            f"الرصيد بعدها: {tx.balance_after:.2f}$\n"
            f"التاريخ: {tx.created_at.strftime('%Y-%m-%d %H:%M')}"
        )
        if tx.description:
            line += f"\n📝 {tx.description[:50]}"
        lines.append(line)

    kb = InlineKeyboardBuilder()
    if page > 0:
        kb.button(
            text="◀️ السابق",
            callback_data=f"my_transactions:{page - 1}",
        )
    if page < total_pages - 1:
        kb.button(
            text="التالي ▶️",
            callback_data=f"my_transactions:{page + 1}",
        )
    kb.button(
        text="🔙 رجوع لحسابي",
        callback_data="menu:account",
    )
    kb.adjust(2, 1)

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=kb.as_markup(),
    )
    await callback.answer()
