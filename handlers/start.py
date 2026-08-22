"""
أوامر البداية والقائمة الرئيسية.
"""
from decimal import Decimal

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from keyboards.main_menu import build_main_menu
from keyboards.common import check_subscription_kb
from services.subscription_service import SubscriptionService
from services.settings_service import SettingsService
from services.dynamic_service import DynamicService
from providers.countries import get_active_number_services

router = Router(name="start")


async def _build_menu(session, db_user):
    """يبني القائمة الرئيسية الديناميكية."""
    number_services = await get_active_number_services(session)
    categories = await DynamicService.get_active_categories(session)
    return build_main_menu(
        number_services=number_services,
        categories=categories,
        balance_usd=f"{db_user.balance:.2f}",
    )


@router.message(CommandStart())
async def cmd_start(message: Message, session, db_user):
    is_ok, missing = await SubscriptionService.is_user_subscribed_all(
        message.bot, session, db_user.telegram_id
    )

    if not is_ok and not db_user.is_admin:
        await message.answer(
            "👋 أهلاً بك!\n\n"
            "⚠️ للمتابعة يرجى الاشتراك بالقنوات التالية أولاً:",
            reply_markup=check_subscription_kb(missing),
        )
        return

    if not db_user.is_activated:
        db_user.is_activated = True
        await session.commit()
        await _try_pay_referral_bonus(session, db_user, message.bot)

    welcome_msg = await SettingsService.get(
        "welcome_message",
        f"👋 أهلاً بك <b>{message.from_user.full_name}</b>!"
    )
    welcome_msg = welcome_msg.replace(
        "{name}", message.from_user.full_name or "عزيزي"
    )

    menu_kb = await _build_menu(session, db_user)
    await message.answer(welcome_msg, reply_markup=menu_kb)


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, session, db_user):
    """زر الرجوع للقائمة الرئيسية."""
    await callback.answer()
    menu_kb = await _build_menu(session, db_user)
    try:
        await callback.message.edit_text(
            f"🏠 <b>القائمة الرئيسية</b>\n\n"
            f"💰 رصيدك: <b>{db_user.balance:.2f}$</b>",
            reply_markup=menu_kb,
        )
    except Exception:
        await callback.message.answer(
            f"🏠 <b>القائمة الرئيسية</b>\n\n"
            f"💰 رصيدك: <b>{db_user.balance:.2f}$</b>",
            reply_markup=menu_kb,
        )


async def _try_pay_referral_bonus(session, user, bot):
    """يدفع مكافأة الإحالة بالدولار."""
    from database.models import User, TransactionType
    from services.balance_service import BalanceService
    from services.notification_service import NotificationService

    if user.referrer_id is None or user.referral_bonus_paid:
        return

    require_sub = await SettingsService.get_bool(
        "require_subscription_for_referral", True
    )
    if require_sub and not user.is_activated:
        return

    referrer = await session.get(User, user.referrer_id)
    if referrer is None:
        return

    bonus_usd = await SettingsService.get_decimal(
        "referral_bonus_usd", Decimal("0.015")
    )

    if bonus_usd <= 0:
        return

    await BalanceService.add_balance(
        session,
        referrer.id,
        bonus_usd,
        TransactionType.REFERRAL_BONUS,
        description=(
            f"مكافأة إحالة عن المستخدم "
            f"{user.telegram_id}"
        ),
    )
    user.referral_bonus_paid = True
    await session.commit()

    notifier = NotificationService(bot)
    await notifier.notify_user(
        referrer.telegram_id,
        f"💎 حصلت على مكافأة إحالة بقيمة "
        f"<b>{bonus_usd}$</b> لانضمام مستخدم جديد "
        f"عبر رابطك!"
    )


@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(
    callback: CallbackQuery, session, db_user, bot
):
    is_ok, missing = await SubscriptionService.is_user_subscribed_all(
        bot, session, db_user.telegram_id
    )

    if is_ok:
        if not db_user.is_activated:
            db_user.is_activated = True
            await session.commit()
            await _try_pay_referral_bonus(session, db_user, bot)

        await callback.message.edit_text(
            "✅ تم التحقق من اشتراكك بنجاح!"
        )
        menu_kb = await _build_menu(session, db_user)
        await callback.message.answer(
            f"🏠 <b>القائمة الرئيسية</b>\n\n"
            f"💰 رصيدك: <b>{db_user.balance:.2f}$</b>",
            reply_markup=menu_kb,
        )
    else:
        await callback.answer(
            "❌ ما زلت غير مشترك بكل القنوات المطلوبة.",
            show_alert=True,
        )
