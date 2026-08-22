"""
تحويل الرصيد بين المستخدمين.
"""
import logging
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from database.models import User
from services.balance_service import (
    BalanceService, InsufficientBalanceError
)
from services.notification_service import NotificationService
from services.settings_service import SettingsService
from states.states import TransferStates
from keyboards.main_menu import back_to_main_kb

logger = logging.getLogger(__name__)
router = Router(name="transfer")


@router.message(F.text == "🔄 تحويل الرصيد")
async def transfer_start(
    message: Message, state: FSMContext, db_user: User
):
    await state.clear()
    await message.answer(
        f"🔄 <b>تحويل الرصيد</b>\n\n"
        f"💰 رصيدك الحالي: <b>{db_user.balance:.2f}$</b>\n\n"
        "أرسل آيدي المستخدم (Telegram ID) "
        "الذي تريد التحويل له:",
        reply_markup=back_to_main_kb(),
    )
    await state.set_state(TransferStates.waiting_recipient_id)


@router.callback_query(F.data == "menu:transfer")
async def transfer_start_cb(
    callback: CallbackQuery, state: FSMContext, db_user: User
):
    await callback.answer()
    await state.clear()
    await callback.message.answer(
        f"🔄 <b>تحويل الرصيد</b>\n\n"
        f"💰 رصيدك الحالي: <b>{db_user.balance:.2f}$</b>\n\n"
        "أرسل آيدي المستخدم (Telegram ID) "
        "الذي تريد التحويل له:",
        reply_markup=back_to_main_kb(),
    )
    await state.set_state(TransferStates.waiting_recipient_id)


@router.message(TransferStates.waiting_recipient_id)
async def transfer_recipient_received(
    message: Message,
    state: FSMContext,
    session,
    db_user: User,
):
    try:
        recipient_tg_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            "⚠️ الرجاء إرسال آيدي صحيح (أرقام فقط)."
        )
        return

    if recipient_tg_id == db_user.telegram_id:
        await message.answer("⚠️ لا يمكنك التحويل لنفسك.")
        return

    result = await session.execute(
        select(User).where(
            User.telegram_id == recipient_tg_id
        )
    )
    recipient = result.scalar_one_or_none()
    if recipient is None:
        await message.answer(
            "⚠️ لا يوجد مستخدم بهذا الآيدي في البوت."
        )
        return

    await state.update_data(
        recipient_id=recipient.id,
        recipient_tg_id=recipient.telegram_id,
    )
    await message.answer(
        f"💰 رصيدك الحالي: <b>{db_user.balance:.2f}$</b>\n"
        "أرسل المبلغ المراد تحويله بالدولار:"
    )
    await state.set_state(TransferStates.waiting_amount)


@router.message(TransferStates.waiting_amount)
async def transfer_amount_received(
    message: Message,
    state: FSMContext,
    session,
    db_user: User,
    bot,
):
    try:
        amount = Decimal(message.text.strip())
        if not amount.is_finite() or amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, AttributeError):
        await message.answer(
            "⚠️ المبلغ يجب أن يكون رقماً صحيحاً أكبر من صفر."
        )
        return

    data = await state.get_data()
    recipient_id = data["recipient_id"]
    recipient_tg_id = data["recipient_tg_id"]

    try:
        _, _, _ = await BalanceService.transfer(
            session,
            from_user_id=db_user.id,
            to_user_id=recipient_id,
            amount=amount,
        )
    except InsufficientBalanceError:
        await message.answer(
            "⚠️ رصيدك غير كافٍ لإتمام هذا التحويل."
        )
        await state.clear()
        return
    except Exception:
        # The transfer method commits debit, credit and ledger rows as one
        # transaction. No separate refund is needed and no balance can be
        # lost between two commits.
        logger.exception("فشل التحويل إلى %s", recipient_tg_id)
        await message.answer(
            "⚠️ تعذّر إتمام التحويل. لم يتم خصم أي مبلغ، حاول لاحقاً."
        )
        await state.clear()
        return

    notifier = NotificationService(bot)
    await message.answer(
        f"✅ تم تحويل <b>{amount:.2f}$</b> "
        f"إلى المستخدم {recipient_tg_id} بنجاح."
    )
    await notifier.notify_user(
        recipient_tg_id,
        f"💰 استلمت تحويلاً بقيمة <b>{amount:.2f}$</b> "
        f"من المستخدم {db_user.telegram_id}."
    )

    large_threshold = await SettingsService.get_decimal(
        "large_transaction_threshold_usd", Decimal("20")
    )
    if amount >= large_threshold:
        await notifier.notify_admin(
            f"🚨 <b>تحويل كبير!</b>\n\n"
            f"من: {db_user.telegram_id}\n"
            f"إلى: {recipient_tg_id}\n"
            f"المبلغ: {amount:.2f}$"
        )

    await state.clear()
