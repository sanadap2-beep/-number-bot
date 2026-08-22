"""
هاندلر شحن الرصيد الرئيسي.
يعرض قائمة طرق الدفع الست ويعالج:
1) نجوم تليجرام (تلقائي)
2) الإيداع اليدوي التقليدي (للتوافق مع القديم)
3) القبول/الرفض من الأدمن

طرق الدفع الست الأخرى (شام كاش يدوي، شام كاش تلقائي،
USDT يدوي، USDT تلقائي، طرق أخرى) في handlers/deposit_methods.py
"""
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery
from sqlalchemy import select

from database.models import (
    DepositRequest, DepositStatus, User, TransactionType
)
from services.settings_service import SettingsService
from services.balance_service import BalanceService
from services.notification_service import NotificationService
from services.stars_service import StarsService
from services.dynamic_service import DynamicService
from states.states import DepositStates
from keyboards.admin import deposit_decision_kb
from keyboards.main_menu import (
    deposit_menu_kb, stars_packages_kb, back_to_main_kb
)

logger = logging.getLogger(__name__)

router = Router(name="deposit")


def _parse_positive_amount(value: str | None) -> Decimal:
    """Parse a finite positive monetary amount from user input."""
    if not value:
        raise InvalidOperation
    amount = Decimal(value.strip())
    if not amount.is_finite() or amount <= 0:
        raise InvalidOperation
    return amount


async def _get_admin_user(session, telegram_id: int) -> User | None:
    """Resolve the Telegram admin to the internal users.id value."""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if user and user.is_admin:
        return user
    return None


# ══════════════ قائمة الشحن الرئيسية ══════════════

@router.message(F.text == "💰 شحن الرصيد")
async def deposit_start(message: Message, state: FSMContext):
    await state.clear()
    await _show_deposit_methods(message)


@router.callback_query(F.data == "menu:deposit")
async def deposit_start_cb(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await _show_deposit_methods(callback)


async def _show_deposit_methods(target):
    """يعرض قائمة طرق الدفع الست."""
    shamcash_manual = await SettingsService.get_bool(
        "payment_shamcash_manual_enabled", True
    )
    stars = await SettingsService.get_bool(
        "payment_stars_enabled", True
    )
    usdt_manual = await SettingsService.get_bool(
        "payment_usdt_manual_enabled", True
    )
    shamcash_auto = await SettingsService.get_bool(
        "payment_shamcash_auto_enabled", True
    )
    usdt_auto = await SettingsService.get_bool(
        "payment_usdt_auto_enabled", True
    )
    other = await SettingsService.get_bool(
        "payment_other_enabled", True
    )

    text = (
        "💰 <b>شحن الرصيد</b>\n\n"
        "اختر طريقة الشحن المناسبة لك:"
    )
    kb = deposit_menu_kb(
        shamcash_manual_enabled=shamcash_manual,
        stars_enabled=stars,
        usdt_manual_enabled=usdt_manual,
        shamcash_auto_enabled=shamcash_auto,
        usdt_auto_enabled=usdt_auto,
        other_enabled=other,
    )

    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=kb)
        except Exception:
            await target.message.answer(text, reply_markup=kb)
    else:
        await target.answer(text, reply_markup=kb)


# ══════════════ نجوم تليجرام ══════════════

@router.callback_query(F.data == "deposit:stars")
async def deposit_stars_menu(
    callback: CallbackQuery, session
):
    await callback.answer()
    packages = await DynamicService.get_active_stars_packages(
        session
    )
    if not packages:
        await callback.message.edit_text(
            "⚠️ لا توجد باقات نجوم متاحة حالياً.",
            reply_markup=back_to_main_kb(),
        )
        return

    await callback.message.edit_text(
        "⭐ <b>شحن بنجوم تليجرام</b>\n\n"
        "اختر الباقة المناسبة:\n"
        "الرصيد يُضاف تلقائياً فور الدفع.",
        reply_markup=stars_packages_kb(packages),
    )


@router.callback_query(F.data.startswith("stars_buy:"))
async def stars_buy(
    callback: CallbackQuery, session, bot
):
    package_id = int(callback.data.split(":")[1])
    await callback.answer()
    success = await StarsService.send_stars_invoice(
        bot=bot,
        chat_id=callback.message.chat.id,
        package_id=package_id,
        session=session,
    )
    if not success:
        await callback.message.answer(
            "⚠️ تعذر إنشاء فاتورة الدفع. "
            "حاول مجدداً لاحقاً."
        )


@router.pre_checkout_query()
async def pre_checkout_handler(
    pre_checkout_query: PreCheckoutQuery,
):
    await StarsService.handle_pre_checkout(pre_checkout_query)


@router.message(F.successful_payment)
async def successful_payment_handler(
    message: Message, session, db_user, bot
):
    await StarsService.handle_successful_payment(
        message=message,
        session=session,
        db_user=db_user,
        bot=bot,
    )


# ══════════════ قبول/رفض الإيداع (من قناة الأدمن) ══════════════

@router.callback_query(F.data.startswith("deposit_accept:"))
async def deposit_accept(
    callback: CallbackQuery, session, bot
):
    if not callback.from_user:
        return

    admin_user = await _get_admin_user(
        session, callback.from_user.id
    )
    if admin_user is None:
        await callback.answer(
            "⛔ غير مصرّح لك بهذا الإجراء.",
            show_alert=True,
        )
        return

    deposit_id = int(callback.data.split(":")[1])
    deposit = await session.get(DepositRequest, deposit_id)

    if deposit is None or deposit.status != DepositStatus.PENDING:
        await callback.answer(
            "⚠️ هذا الطلب تمت معالجته مسبقاً.",
            show_alert=True,
        )
        return

    user = await BalanceService.add_balance(
        session,
        deposit.user_id,
        deposit.amount_usd,
        TransactionType.DEPOSIT,
        description=f"شحن رصيد - طلب #{deposit.id}",
        related_table="deposit_requests",
        related_id=deposit.id,
        payment_reference=f"deposit:{deposit.id}",
    )

    deposit.status = DepositStatus.APPROVED
    deposit.admin_id = admin_user.id
    deposit.processed_at = datetime.utcnow()
    await session.commit()

    notifier = NotificationService(bot)
    await notifier.notify_deposit_approved(
        user_telegram_id=user.telegram_id,
        amount_usd=str(deposit.amount_usd),
    )

    try:
        await callback.message.edit_caption(
            caption=(
                (callback.message.caption or "")
                + f"\n\n✅ <b>تم القبول</b> بواسطة "
                f"{callback.from_user.full_name}"
            ),
            reply_markup=None,
        )
    except Exception:
        pass

    await callback.answer("✅ تم قبول الطلب وإضافة الرصيد.")
    logger.info(
        f"الأدمن {callback.from_user.id} قبل "
        f"إيداع #{deposit.id} "
        f"({deposit.amount_usd}$)"
    )


@router.callback_query(F.data.startswith("deposit_reject:"))
async def deposit_reject(
    callback: CallbackQuery, session, bot
):
    if not callback.from_user:
        return

    admin_user = await _get_admin_user(
        session, callback.from_user.id
    )
    if admin_user is None:
        await callback.answer(
            "⛔ غير مصرّح لك بهذا الإجراء.",
            show_alert=True,
        )
        return

    deposit_id = int(callback.data.split(":")[1])
    deposit = await session.get(DepositRequest, deposit_id)

    if deposit is None or deposit.status != DepositStatus.PENDING:
        await callback.answer(
            "⚠️ هذا الطلب تمت معالجته مسبقاً.",
            show_alert=True,
        )
        return

    deposit.status = DepositStatus.REJECTED
    deposit.admin_id = admin_user.id
    deposit.processed_at = datetime.utcnow()
    await session.commit()

    user = await session.get(User, deposit.user_id)
    notifier = NotificationService(bot)
    await notifier.notify_deposit_rejected(
        user_telegram_id=user.telegram_id,
    )

    try:
        await callback.message.edit_caption(
            caption=(
                (callback.message.caption or "")
                + f"\n\n❌ <b>تم الرفض</b> بواسطة "
                f"{callback.from_user.full_name}"
            ),
            reply_markup=None,
        )
    except Exception:
        pass

    await callback.answer("❌ تم رفض الطلب.")
    logger.info(
        f"الأدمن {callback.from_user.id} رفض "
        f"إيداع #{deposit.id}"
    )


# ══════════════ الإيداع اليدوي القديم (للتوافق) ══════════════

@router.message(DepositStates.waiting_amount)
async def deposit_amount_received(
    message: Message, state: FSMContext
):
    """
    ملاحظة: هذا للتوافق فقط مع أي مستخدم عالق في
    الحالة القديمة. الطرق الجديدة في deposit_methods.py
    """
    try:
        amount = _parse_positive_amount(message.text)
    except (InvalidOperation, AttributeError):
        await message.answer(
            "⚠️ الرجاء إرسال رقم صحيح، مثال: 5"
        )
        return

    min_deposit = await SettingsService.get_decimal(
        "min_deposit_shamcash_usd", Decimal("0.5")
    )
    if amount < min_deposit:
        await message.answer(
            f"⚠️ الحد الأدنى للشحن هو {min_deposit}$"
        )
        return

    await state.update_data(amount_usd=str(amount))

    payment_text = await SettingsService.get(
        "payment_method_text",
        "سيتم إضافة طريقة الدفع قريباً"
    )
    await message.answer(
        f"💳 <b>طريقة الدفع:</b>\n\n"
        f"{payment_text}\n\n"
        "بعد التحويل، أرسل <b>صورة إثبات التحويل</b>:"
    )
    await state.set_state(DepositStates.waiting_proof_photo)


@router.message(DepositStates.waiting_proof_photo, F.photo)
async def deposit_photo_received(
    message: Message, state: FSMContext
):
    await state.update_data(
        photo_file_id=message.photo[-1].file_id
    )
    await message.answer(
        "🔢 الآن أرسل <b>رقم عملية التحويل</b>:"
    )
    await state.set_state(DepositStates.waiting_tx_number)


@router.message(DepositStates.waiting_proof_photo)
async def deposit_photo_invalid(message: Message):
    await message.answer(
        "⚠️ الرجاء إرسال صورة إثبات التحويل (وليس نصاً)."
    )


@router.message(DepositStates.waiting_tx_number)
async def deposit_tx_number_received(
    message: Message,
    state: FSMContext,
    session,
    db_user: User,
    bot,
):
    data = await state.get_data()
    amount_usd = Decimal(data["amount_usd"])
    photo_file_id = data["photo_file_id"]
    tx_number = message.text.strip()

    deposit = DepositRequest(
        user_id=db_user.id,
        amount_usd=amount_usd,
        proof_photo_file_id=photo_file_id,
        proof_tx_number=tx_number,
        payment_method="Manual (Legacy)",
        status=DepositStatus.PENDING,
    )
    session.add(deposit)
    await session.commit()
    await session.refresh(deposit)

    notifier = NotificationService(bot)
    sent_msg_id = await notifier.notify_new_deposit(
        user_telegram_id=db_user.telegram_id,
        username=db_user.username,
        amount_usd=str(amount_usd),
        tx_number=tx_number,
        deposit_id=deposit.id,
        photo_file_id=photo_file_id,
        reply_markup=deposit_decision_kb(deposit.id),
    )

    if sent_msg_id:
        deposit.admin_chat_message_id = sent_msg_id
        await session.commit()
        logger.info(
            f"إشعار إيداع #{deposit.id} أُرسل بنجاح"
        )
    else:
        logger.error(
            f"فشل إرسال إشعار إيداع #{deposit.id} للأدمن!"
        )

    await message.answer(
        "✅ تم إرسال طلب الشحن بنجاح!\n"
        "بانتظار موافقة الإدارة."
    )
    await state.clear()
