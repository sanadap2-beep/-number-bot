"""
إعدادات البوت العامة.
"""
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from services.settings_service import SettingsService
from states.states import (
    AdminSupportStates, AdminPaymentStates,
    AdminLargeTxStates, AdminOrderTimeoutStates,
    AdminSettingsStates, AdminWelcomeStates,
)
from keyboards.admin import admin_settings_kb, admin_back_kb
from filters.admin_filter import IsAdmin

router = Router(name="admin_settings")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "admin:settings")
async def settings_menu(callback: CallbackQuery):
    support = await SettingsService.get("support_username")
    payment = await SettingsService.get("payment_method_text")
    threshold = await SettingsService.get_decimal(
        "large_transaction_threshold_usd"
    )
    order_timeout = await SettingsService.get_int(
        "order_timeout_minutes", 5
    )
    cashback = await SettingsService.get_decimal("cashback_percent")
    referral = await SettingsService.get_decimal("referral_percent")
    rate_limit = await SettingsService.get_int("rate_limit_seconds", 30)
    public_ch = await SettingsService.get("public_channel_id", "غير محدد")
    backup_ch = await SettingsService.get("backup_channel_id", "غير محدد")

    await callback.message.edit_text(
        "⚙️ <b>الإعدادات العامة</b>\n\n"
        f"🛠 يوزر الدعم: {support}\n"
        f"💳 طريقة الدفع: {payment}\n"
        f"🚨 حد التحويل الكبير: {threshold}$\n"
        f"⏳ مهلة انتظار الكود: {order_timeout} دقيقة\n"
        f"💰 نسبة الكاشباك: {cashback}%\n"
        f"💎 نسبة الإحالة: {referral}%\n"
        f"⏱ Rate Limit: {rate_limit} ثانية\n"
        f"📢 قناة الإشعارات العامة: {public_ch}\n"
        f"💾 قناة البكاب: {backup_ch}\n",
        reply_markup=admin_settings_kb(),
    )


# ── يوزر الدعم ──

@router.callback_query(F.data == "admin:set_support")
async def set_support_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.message.edit_text(
        "🛠 أرسل يوزر الدعم الجديد (مثال: @support):",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(
        AdminSupportStates.waiting_support_username
    )


@router.message(AdminSupportStates.waiting_support_username)
async def set_support_received(
    message: Message, state: FSMContext, session
):
    await SettingsService.set(
        session, "support_username", message.text.strip()
    )
    await message.answer("✅ تم تحديث يوزر الدعم.")
    await state.clear()


# ── طريقة الدفع ──

@router.callback_query(F.data == "admin:set_payment")
async def set_payment_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.message.edit_text(
        "💳 أرسل نص طريقة الدفع الجديد:",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(
        AdminPaymentStates.waiting_payment_text
    )


@router.message(AdminPaymentStates.waiting_payment_text)
async def set_payment_received(
    message: Message, state: FSMContext, session
):
    await SettingsService.set(
        session, "payment_method_text", message.text
    )
    await message.answer("✅ تم تحديث طريقة الدفع.")
    await state.clear()


# ── حد التحويل الكبير ──

@router.callback_query(F.data == "admin:set_large_tx")
async def set_large_tx_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.message.edit_text(
        "🚨 أرسل الحد الجديد للتحويل الكبير بالدولار:",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(AdminLargeTxStates.waiting_threshold)


@router.message(AdminLargeTxStates.waiting_threshold)
async def set_large_tx_received(
    message: Message, state: FSMContext, session
):
    try:
        val = Decimal(message.text.strip())
    except InvalidOperation:
        await message.answer("⚠️ أرسل رقماً صحيحاً.")
        return
    await SettingsService.set(
        session, "large_transaction_threshold_usd", str(val)
    )
    await message.answer("✅ تم تحديث الحد.")
    await state.clear()


# ── مهلة انتظار الكود ──

@router.callback_query(F.data == "admin:set_order_timeout")
async def set_order_timeout_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.message.edit_text(
        "⏳ أرسل مهلة انتظار الكود بالدقائق:",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(
        AdminOrderTimeoutStates.waiting_minutes
    )


@router.message(AdminOrderTimeoutStates.waiting_minutes)
async def set_order_timeout_received(
    message: Message, state: FSMContext, session
):
    try:
        val = int(message.text.strip())
        if val <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "⚠️ أرسل رقماً صحيحاً أكبر من صفر."
        )
        return
    await SettingsService.set(
        session, "order_timeout_minutes", str(val)
    )
    await message.answer(
        f"✅ تم تحديث المهلة إلى {val} دقيقة."
    )
    await state.clear()


# ── رسالة الترحيب ──

@router.callback_query(F.data == "admin:set_welcome")
async def set_welcome_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.message.edit_text(
        "📝 أرسل رسالة الترحيب الجديدة:\n\n"
        "💡 يمكنك استخدام {name} لإظهار اسم المستخدم.",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(
        AdminWelcomeStates.waiting_message
    )


@router.message(AdminWelcomeStates.waiting_message)
async def set_welcome_received(
    message: Message, state: FSMContext, session
):
    await SettingsService.set(
        session, "welcome_message", message.text
    )
    await message.answer("✅ تم تحديث رسالة الترحيب.")
    await state.clear()


# ── نسبة الكاشباك ──

@router.callback_query(F.data == "admin:set_cashback")
async def set_cashback_start(
    callback: CallbackQuery, state: FSMContext
):
    current = await SettingsService.get_decimal("cashback_percent")
    await callback.message.edit_text(
        f"💰 نسبة الكاشباك الحالية: {current}%\n\n"
        "أرسل النسبة الجديدة (0 لتعطيل الكاشباك):",
        reply_markup=admin_back_kb(),
    )
    await state.update_data(setting_key="cashback_percent")
    await state.set_state(AdminSettingsStates.waiting_value)


# ── نسبة الإحالة ──

@router.callback_query(F.data == "admin:set_referral_percent")
async def set_referral_percent_start(
    callback: CallbackQuery, state: FSMContext
):
    current = await SettingsService.get_decimal("referral_percent")
    await callback.message.edit_text(
        f"💎 نسبة الإحالة الحالية: {current}%\n\n"
        "أرسل النسبة الجديدة (0 لتعطيل):",
        reply_markup=admin_back_kb(),
    )
    await state.update_data(setting_key="referral_percent")
    await state.set_state(AdminSettingsStates.waiting_value)


# ── Rate Limit ──

@router.callback_query(F.data == "admin:set_rate_limit")
async def set_rate_limit_start(
    callback: CallbackQuery, state: FSMContext
):
    current = await SettingsService.get_int("rate_limit_seconds", 30)
    await callback.message.edit_text(
        f"⏱ Rate Limit الحالي: {current} ثانية\n\n"
        "أرسل القيمة الجديدة بالثواني (0 لتعطيل):",
        reply_markup=admin_back_kb(),
    )
    await state.update_data(setting_key="rate_limit_seconds")
    await state.set_state(AdminSettingsStates.waiting_value)


# ── قناة الإشعارات العامة ──

@router.callback_query(F.data == "admin:set_public_channel")
async def set_public_channel_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.message.edit_text(
        "📢 أرسل آيدي قناة الإشعارات العامة:\n"
        "(مثال: -1001234567890)\n"
        "أو أرسل 0 لتعطيل الإشعارات العامة.",
        reply_markup=admin_back_kb(),
    )
    await state.update_data(setting_key="public_channel_id")
    await state.set_state(AdminSettingsStates.waiting_value)


# ── قناة البكاب ──

@router.callback_query(F.data == "admin:set_backup_channel")
async def set_backup_channel_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.message.edit_text(
        "💾 أرسل آيدي قناة البكاب:\n"
        "(مثال: -1001234567890)\n"
        "أو أرسل 0 لتعطيل البكاب التلقائي.",
        reply_markup=admin_back_kb(),
    )
    await state.update_data(setting_key="backup_channel_id")
    await state.set_state(AdminSettingsStates.waiting_value)


# ── معالج موحد للإعدادات الرقمية ──

@router.message(AdminSettingsStates.waiting_value)
async def generic_setting_received(
    message: Message, state: FSMContext, session
):
    data = await state.get_data()
    key = data.get("setting_key")

    if not key:
        await state.clear()
        return

    value = message.text.strip()
    try:
        Decimal(value)
    except InvalidOperation:
        try:
            int(value)
        except ValueError:
            await message.answer("⚠️ أرسل قيمة صحيحة.")
            return

    await SettingsService.set(session, key, value)
    await message.answer(
        f"✅ تم تحديث الإعداد <b>{key}</b> "
        f"إلى: <b>{value}</b>"
    )
    await state.clear()
