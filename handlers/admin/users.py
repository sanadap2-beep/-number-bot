"""
إدارة المستخدمين.
"""
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from database.models import User, TransactionType
from services.balance_service import BalanceService, InsufficientBalanceError
from services.notification_service import NotificationService
from states.states import (
    AdminUserSearchStates, AdminSendMessageStates,
)
from keyboards.admin import user_manage_kb, admin_back_kb
from filters.admin_filter import IsAdmin

router = Router(name="admin_users")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "admin:users")
async def users_search_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.message.edit_text(
        "🔍 أرسل آيدي المستخدم (Telegram ID) للبحث:",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(
        AdminUserSearchStates.waiting_user_id
    )


@router.message(AdminUserSearchStates.waiting_user_id)
async def user_search_result(
    message: Message, state: FSMContext, session
):
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ آيدي غير صحيح.")
        return

    result = await session.execute(
        select(User).where(User.telegram_id == tg_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        await message.answer("⚠️ لا يوجد مستخدم بهذا الآيدي.")
        return

    await message.answer(
        "👤 <b>معلومات المستخدم</b>\n\n"
        f"🆔 آيدي: {user.telegram_id}\n"
        f"👤 يوزر: @{user.username or '-'}\n"
        f"📛 الاسم: {user.full_name or '-'}\n"
        f"💰 الرصيد: <b>{user.balance:.2f}$</b>\n"
        f"🛒 إجمالي الشراء: {user.total_spent_usd:.2f}$\n"
        f"📦 عدد الطلبات: {user.total_orders}\n"
        f"🎁 كاشباك: {user.cashback_earned_usd:.4f}$\n"
        f"🚫 محظور: {'نعم' if user.is_banned else 'لا'}\n"
        f"👑 أدمن: {'نعم' if user.is_admin else 'لا'}\n"
        f"📅 الانضمام: {user.joined_at.strftime('%Y-%m-%d')}",
        reply_markup=user_manage_kb(user.id, user.is_banned),
    )
    await state.clear()


# ── إضافة/خصم رصيد ──

@router.callback_query(
    F.data.startswith("admin:user_add_balance:")
)
async def user_add_balance_start(
    callback: CallbackQuery, state: FSMContext
):
    user_id = int(callback.data.split(":")[2])
    await state.update_data(
        target_user_id=user_id, action="add"
    )
    await callback.message.answer(
        "💰 أرسل المبلغ المراد إضافته بالدولار:"
    )
    await state.set_state(
        AdminUserSearchStates.waiting_balance_amount
    )


@router.callback_query(
    F.data.startswith("admin:user_deduct_balance:")
)
async def user_deduct_balance_start(
    callback: CallbackQuery, state: FSMContext
):
    user_id = int(callback.data.split(":")[2])
    await state.update_data(
        target_user_id=user_id, action="deduct"
    )
    await callback.message.answer(
        "💰 أرسل المبلغ المراد خصمه بالدولار:"
    )
    await state.set_state(
        AdminUserSearchStates.waiting_balance_amount
    )


@router.message(AdminUserSearchStates.waiting_balance_amount)
async def balance_amount_received(
    message: Message,
    state: FSMContext,
    session,
    bot,
):
    data = await state.get_data()
    try:
        amount = Decimal(message.text.strip())
        if amount <= 0:
            raise InvalidOperation
    except InvalidOperation:
        await message.answer("⚠️ أرسل رقماً صحيحاً أكبر من صفر.")
        return

    target_user = await session.get(User, data["target_user_id"])
    if not target_user:
        await message.answer("⚠️ المستخدم غير موجود.")
        await state.clear()
        return

    notifier = NotificationService(bot)

    if data["action"] == "add":
        await BalanceService.add_balance(
            session, target_user.id, amount,
            TransactionType.ADMIN_ADD,
            description="إضافة رصيد يدوية من الأدمن",
        )
        await notifier.notify_user(
            target_user.telegram_id,
            f"💰 تمت إضافة <b>{amount:.2f}$</b> "
            f"إلى رصيدك من الإدارة."
        )
        await message.answer(
            f"✅ تمت إضافة {amount:.2f}$ لرصيد المستخدم."
        )
    else:
        try:
            await BalanceService.deduct_balance(
                session, target_user.id, amount,
                TransactionType.ADMIN_DEDUCT,
                description="خصم رصيد يدوي من الأدمن",
            )
        except InsufficientBalanceError:
            await message.answer(
                "⚠️ رصيد المستخدم أقل من المبلغ المطلوب."
            )
            await state.clear()
            return
        await notifier.notify_user(
            target_user.telegram_id,
            f"⚠️ تم خصم <b>{amount:.2f}$</b> "
            f"من رصيدك من قبل الإدارة."
        )
        await message.answer(
            f"✅ تم خصم {amount:.2f}$ من رصيد المستخدم."
        )
    await state.clear()


# ── الحظر ──

@router.callback_query(
    F.data.startswith("admin:user_ban:")
)
async def user_ban(
    callback: CallbackQuery, session, bot
):
    user_id = int(callback.data.split(":")[2])
    user = await session.get(User, user_id)
    if not user:
        await callback.answer("⚠️ المستخدم غير موجود.", show_alert=True)
        return
    user.is_banned = True
    await session.commit()
    await NotificationService(bot).notify_user(
        user.telegram_id,
        "🚫 تم حظرك من استخدام البوت من قبل الإدارة."
    )
    await callback.answer("✅ تم الحظر.")
    await callback.message.edit_reply_markup(
        reply_markup=user_manage_kb(user.id, True)
    )


@router.callback_query(
    F.data.startswith("admin:user_unban:")
)
async def user_unban(
    callback: CallbackQuery, session, bot
):
    user_id = int(callback.data.split(":")[2])
    user = await session.get(User, user_id)
    if not user:
        await callback.answer("⚠️ المستخدم غير موجود.", show_alert=True)
        return
    user.is_banned = False
    await session.commit()
    await NotificationService(bot).notify_user(
        user.telegram_id,
        "✅ تم فك حظرك. يمكنك استخدام البوت الآن."
    )
    await callback.answer("✅ تم فك الحظر.")
    await callback.message.edit_reply_markup(
        reply_markup=user_manage_kb(user.id, False)
    )


# ── سجل معاملات المستخدم (للأدمن) ──

@router.callback_query(
    F.data.startswith("admin:user_transactions:")
)
async def user_transactions(
    callback: CallbackQuery, session
):
    user_id = int(callback.data.split(":")[2])
    user = await session.get(User, user_id)
    if not user:
        await callback.answer("⚠️ المستخدم غير موجود.", show_alert=True)
        return

    transactions = await BalanceService.get_transactions(
        session, user_id, limit=10
    )

    if not transactions:
        await callback.message.answer(
            "📊 لا يوجد معاملات لهذا المستخدم."
        )
        await callback.answer()
        return

    lines = [
        f"📊 <b>آخر 10 معاملات للمستخدم "
        f"{user.telegram_id}</b>\n"
    ]
    for tx in transactions:
        sign = "+" if tx.amount > 0 else ""
        lines.append(
            f"\n{tx.type.value}: {sign}{tx.amount:.4f}$\n"
            f"الرصيد بعدها: {tx.balance_after:.2f}$\n"
            f"{tx.created_at.strftime('%Y-%m-%d %H:%M')}"
        )

    await callback.message.answer("\n".join(lines))
    await callback.answer()


# ── إرسال رسالة لمستخدم ──

@router.callback_query(
    F.data.startswith("admin:user_send_msg:")
)
async def user_send_msg_start(
    callback: CallbackQuery, state: FSMContext
):
    user_id = int(callback.data.split(":")[2])
    await state.update_data(send_to_user_id=user_id)
    await callback.message.answer(
        "📩 أرسل الرسالة التي تريد إرسالها لهذا المستخدم:"
    )
    await state.set_state(
        AdminSendMessageStates.waiting_message
    )
    await callback.answer()


@router.message(AdminSendMessageStates.waiting_message)
async def user_send_msg_received(
    message: Message, state: FSMContext, session, bot
):
    data = await state.get_data()
    user_id = data["send_to_user_id"]
    user = await session.get(User, user_id)
    if not user:
        await message.answer("⚠️ المستخدم غير موجود.")
        await state.clear()
        return

    notifier = NotificationService(bot)
    success = await notifier.notify_user(
        user.telegram_id,
        f"📩 <b>رسالة من الإدارة:</b>\n\n{message.text}"
    )
    if success:
        await message.answer("✅ تم إرسال الرسالة بنجاح.")
    else:
        await message.answer(
            "⚠️ فشل إرسال الرسالة. "
            "ربما المستخدم حظر البوت."
        )
    await state.clear()
