"""
هاندلر شراء الأرقام.
ديناميكي بالكامل: الخدمات والدول تُقرأ من DB.
المزود يُختار تلقائياً (الأرخص).
العملة: دولار (USD).
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func

from database.models import (
    NumberOrder, OrderStatus, TransactionType,
    ProviderName, User
)
from providers.manager import (
    provider_manager, ProviderUnavailableError
)
from providers.countries import (
    get_active_countries, get_country_by_code,
    get_active_number_services, get_number_service_by_code,
)
from services.pricing_service import PricingService
from services.settings_service import SettingsService
from services.balance_service import BalanceService, InsufficientBalanceError
from services.notification_service import NotificationService
from services.cashback_service import CashbackService
from keyboards.numbers import (
    countries_kb, confirm_purchase_kb,
    order_actions_kb, code_received_kb,
    number_services_kb,
)
from keyboards.main_menu import insufficient_balance_kb

logger = logging.getLogger(__name__)

router = Router(name="numbers")

DEFAULT_ORDER_TIMEOUT_MINUTES = 5


async def _get_order_timeout() -> int:
    value = await SettingsService.get_int(
        "order_timeout_minutes", DEFAULT_ORDER_TIMEOUT_MINUTES
    )
    return value


async def _check_rate_limit(session, user_id: int) -> bool:
    """يتحقق من Rate Limiting."""
    from database.models import RateLimitLog
    rate_limit_seconds = await SettingsService.get_int(
        "rate_limit_seconds", 30
    )
    if rate_limit_seconds <= 0:
        return True

    cutoff = datetime.utcnow() - timedelta(seconds=rate_limit_seconds)
    result = await session.execute(
        select(func.count(RateLimitLog.id)).where(
            RateLimitLog.user_id == user_id,
            RateLimitLog.action == "buy_number",
            RateLimitLog.created_at >= cutoff,
        )
    )
    count = result.scalar_one()
    return count == 0


async def _log_rate_limit(session, user_id: int):
    from database.models import RateLimitLog
    session.add(RateLimitLog(
        user_id=user_id,
        action="buy_number",
    ))
    await session.commit()


async def _check_active_orders_limit(
    session, user_id: int
) -> bool:
    """يتحقق من حد الطلبات النشطة."""
    max_orders = await SettingsService.get_int(
        "max_active_orders", 3
    )
    result = await session.execute(
        select(func.count(NumberOrder.id)).where(
            NumberOrder.user_id == user_id,
            NumberOrder.status == OrderStatus.PENDING,
        )
    )
    active_count = result.scalar_one()
    return active_count < max_orders


# ══════════════ اختيار الخدمة ══════════════

@router.callback_query(F.data.startswith("num_svc:"))
async def number_service_selected(
    callback: CallbackQuery, session
):
    service_code = callback.data.split(":")[1]
    service = await get_number_service_by_code(
        session, service_code
    )
    if service is None or not service.is_active:
        await callback.answer(
            "⚠️ هذه الخدمة غير متاحة حالياً.",
            show_alert=True,
        )
        return

    await callback.answer()
    countries = await get_active_countries(session)
    if not countries:
        await callback.message.edit_text(
            "⚠️ لا توجد دول مفعّلة حالياً. "
            "الرجاء المحاولة لاحقاً.",
        )
        return

    await callback.message.edit_text(
        f"{service.emoji} <b>أرقام {service.name_ar}</b>\n\n"
        "اختر الدولة:",
        reply_markup=countries_kb(service_code, countries),
    )


# ══════════════ Pagination الدول ══════════════

@router.callback_query(F.data.startswith("num_page:"))
async def countries_page(
    callback: CallbackQuery, session
):
    parts = callback.data.split(":")
    service_code = parts[1]
    page = int(parts[2])

    service = await get_number_service_by_code(
        session, service_code
    )
    if service is None:
        await callback.answer("⚠️ خدمة غير موجودة.", show_alert=True)
        return

    await callback.answer()
    countries = await get_active_countries(session)
    await callback.message.edit_text(
        f"{service.emoji} <b>أرقام {service.name_ar}</b>\n\n"
        "اختر الدولة:",
        reply_markup=countries_kb(service_code, countries, page),
    )


# ══════════════ عرض السعر ══════════════

@router.callback_query(F.data.startswith("num_country:"))
async def show_price(callback: CallbackQuery, session):
    parts = callback.data.split(":")
    service_code = parts[1]
    country_code = parts[2]

    service = await get_number_service_by_code(
        session, service_code
    )
    country = await get_country_by_code(session, country_code)

    if not service or not country or not country.is_active:
        await callback.answer(
            "⚠️ هذه الخدمة/الدولة غير متاحة.",
            show_alert=True,
        )
        return

    await callback.answer("⏳ جاري جلب السعر...")

    try:
        prices = await provider_manager.get_cheapest_price(
            service, country, session
        )
    except Exception as e:
        logger.error(f"خطأ جلب الأسعار: {e}")
        await callback.message.answer(
            "⚠️ تعذّر الاتصال بالمزودين حالياً. "
            "حاول مجدداً خلال دقيقة."
        )
        return

    if not prices:
        await callback.message.answer(
            f"❌ لا توجد أرقام متاحة حالياً لـ "
            f"{country.flag} {country.name_ar} "
            f"لخدمة {service.name_ar}.\n"
            "جرّب دولة أخرى أو حاول لاحقاً."
        )
        return

    cheapest_provider = min(prices, key=prices.get)
    cost_usd = prices[cheapest_provider]

    margin_type, margin_value = await PricingService.get_margin(
        session, service_code, country_code, cheapest_provider
    )
    sell_price = PricingService.apply_margin(
        cost_usd, margin_type, margin_value
    )

    await callback.message.edit_text(
        f"🌍 الدولة: {country.flag} {country.name_ar}\n"
        f"{service.emoji} الخدمة: {service.name_ar}\n"
        f"💰 السعر: <b>{sell_price}$</b>\n\n"
        "هل تريد تأكيد الشراء؟",
        reply_markup=confirm_purchase_kb(
            service_code, country_code
        ),
    )


# ══════════════ تأكيد الشراء ══════════════

@router.callback_query(F.data.startswith("num_confirm:"))
async def confirm_buy(
    callback: CallbackQuery,
    session,
    db_user: User,
    bot,
):
    parts = callback.data.split(":")
    service_code = parts[1]
    country_code = parts[2]

    service = await get_number_service_by_code(
        session, service_code
    )
    country = await get_country_by_code(session, country_code)

    if not service or not country or not country.is_active:
        await callback.answer(
            "⚠️ غير متاح.", show_alert=True
        )
        return

    # ── Rate Limiting ──
    can_proceed = await _check_rate_limit(
        session, db_user.id
    )
    if not can_proceed:
        rate_seconds = await SettingsService.get_int(
            "rate_limit_seconds", 30
        )
        await callback.answer(
            f"⏳ انتظر {rate_seconds} ثانية بين كل طلب.",
            show_alert=True,
        )
        return

    # ── حد الطلبات النشطة ──
    can_order = await _check_active_orders_limit(
        session, db_user.id
    )
    if not can_order:
        max_orders = await SettingsService.get_int(
            "max_active_orders", 3
        )
        await callback.answer(
            f"⚠️ لديك {max_orders} طلبات نشطة كحد أقصى. "
            "انتظر حتى تنتهي أو ألغِ أحدها.",
            show_alert=True,
        )
        return

    await callback.answer("⏳ جاري تجهيز طلبك...")

    # ── جلب الأسعار ──
    try:
        prices = await provider_manager.get_cheapest_price(
            service, country, session
        )
    except Exception:
        await callback.message.answer(
            "⚠️ خطأ مؤقت بالاتصال بالمزود. "
            "أعد المحاولة."
        )
        return

    if not prices:
        await callback.message.answer(
            "❌ نفذت الأرقام المتاحة. "
            "حاول لاحقاً أو اختر دولة أخرى."
        )
        return

    cheapest_provider = min(prices, key=prices.get)
    cost_usd = prices[cheapest_provider]
    margin_type, margin_value = await PricingService.get_margin(
        session, service_code, country_code, cheapest_provider
    )
    sell_price = PricingService.apply_margin(
        cost_usd, margin_type, margin_value
    )

    # ── فحص الرصيد ──
    if db_user.balance < sell_price:
        notifier = NotificationService(bot)
        await notifier.notify_insufficient_balance(
            user_telegram_id=db_user.telegram_id,
            required_usd=str(sell_price),
            current_balance_usd=f"{db_user.balance:.2f}",
            reply_markup=insufficient_balance_kb(),
        )
        return

    # ── خصم الرصيد ──
    try:
        await BalanceService.deduct_balance(
            session, db_user.id, sell_price,
            TransactionType.PURCHASE,
            description=(
                f"شراء رقم {service.name_ar} - "
                f"{country.name_ar}"
            ),
            is_purchase=True,
        )
    except InsufficientBalanceError:
        await callback.message.answer(
            "⚠️ رصيدك غير كافٍ.",
        )
        return

    # ── شراء الرقم ──
    try:
        buy_result = await provider_manager.buy_number(
            service, country, session
        )
    except ProviderUnavailableError:
        await BalanceService.add_balance(
            session, db_user.id, sell_price,
            TransactionType.REFUND,
            description="استرجاع - فشل الشراء",
        )
        await callback.message.answer(
            "❌ نفذت الأرقام عند كل المزودين. "
            "تم استرجاع رصيدك بالكامل."
        )
        return
    except Exception as e:
        logger.error(f"خطأ غير متوقع بالشراء: {e}")
        await BalanceService.add_balance(
            session, db_user.id, sell_price,
            TransactionType.REFUND,
            description="استرجاع - خطأ تقني",
        )
        await callback.message.answer(
            "❌ خطأ تقني غير متوقع. "
            "تم استرجاع رصيدك بالكامل."
        )
        return

    # ── تسجيل Rate Limit ──
    await _log_rate_limit(session, db_user.id)

    # ── حفظ الطلب ──
    timeout_minutes = await _get_order_timeout()
    expires_at = datetime.utcnow() + timedelta(
        minutes=timeout_minutes
    )

    order = NumberOrder(
        user_id=db_user.id,
        provider=buy_result.provider,
        provider_order_id=buy_result.provider_order_id,
        service=service_code,
        country_code=country_code,
        phone_number=buy_result.phone_number,
        price_provider_usd=buy_result.cost_usd,
        price_sell_usd=sell_price,
        status=OrderStatus.PENDING,
        expires_at=expires_at,
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)

    # ── رسالة الانتظار ──
    status_msg = await callback.message.answer(
        f"✅ <b>تم شراء الرقم بنجاح!</b>\n\n"
        f"📱 الرقم: <code>{buy_result.phone_number}</code>\n"
        f"⏳ بانتظار الكود... "
        f"الوقت المتبقي: {timeout_minutes}:00\n\n"
        "سيتم تحديث هذه الرسالة تلقائياً.",
        reply_markup=order_actions_kb(order.id),
    )
    order.status_chat_id = status_msg.chat.id
    order.status_message_id = status_msg.message_id
    await session.commit()

    # ── إشعار الأدمن ──
    notifier = NotificationService(bot)
    await notifier.notify_admin(
        "🛒 <b>شراء رقم جديد</b>\n\n"
        f"👤 المستخدم: {db_user.telegram_id} "
        f"(@{db_user.username or '-'})\n"
        f"{service.emoji} الخدمة: {service.name_ar}\n"
        f"🌍 الدولة: {country.flag} {country.name_ar}\n"
        f"📱 الرقم: {buy_result.phone_number}\n"
        f"🏭 المزود: {buy_result.provider.value}\n"
        f"💰 سعر البيع: {sell_price}$ | "
        f"التكلفة: {buy_result.cost_usd}$"
    )


# ══════════════ تحديث يدوي ══════════════

@router.callback_query(F.data.startswith("num_refresh:"))
async def refresh_order(
    callback: CallbackQuery, session, db_user: User
):
    order_id = int(callback.data.split(":")[1])
    order = await session.get(NumberOrder, order_id)

    if not order or order.user_id != db_user.id:
        await callback.answer("⚠️ طلب غير موجود.", show_alert=True)
        return

    if order.status != OrderStatus.PENDING:
        await callback.answer("ℹ️ هذا الطلب لم يعد نشطاً.", show_alert=True)
        return

    await callback.answer("🔄 جاري التحديث...")


# ══════════════ إلغاء الطلب ══════════════

@router.callback_query(F.data.startswith("num_cancel:"))
async def cancel_order_manual(
    callback: CallbackQuery, session, db_user: User
):
    order_id = int(callback.data.split(":")[1])
    order = await session.get(NumberOrder, order_id)

    if not order or order.user_id != db_user.id:
        await callback.answer(
            "⚠️ الطلب غير موجود.", show_alert=True
        )
        return

    if order.status != OrderStatus.PENDING:
        await callback.answer(
            "⚠️ لا يمكن إلغاء هذا الطلب.",
            show_alert=True,
        )
        return

    try:
        await provider_manager.cancel_order(
            order.provider, order.provider_order_id
        )
    except Exception:
        pass

    order.status = OrderStatus.CANCELLED
    await session.commit()

    await BalanceService.add_balance(
        session, db_user.id, order.price_sell_usd,
        TransactionType.REFUND,
        description=f"استرجاع - إلغاء يدوي #{order.id}",
        related_table="number_orders",
        related_id=order.id,
    )
    order.status = OrderStatus.REFUNDED
    await session.commit()

    try:
        await callback.message.edit_text(
            f"❌ تم إلغاء الطلب واسترجاع "
            f"<b>{order.price_sell_usd}$</b> إلى رصيدك."
        )
    except TelegramBadRequest:
        pass
    await callback.answer("✅ تم الإلغاء والاسترجاع.")


# ══════════════ كود إضافي ══════════════

@router.callback_query(F.data.startswith("num_extra:"))
async def wait_extra_code(
    callback: CallbackQuery, session, db_user: User
):
    order_id = int(callback.data.split(":")[1])
    order = await session.get(NumberOrder, order_id)

    if not order or order.user_id != db_user.id:
        await callback.answer(
            "⚠️ الطلب غير موجود.", show_alert=True
        )
        return

    order.awaiting_extra_code = True
    order.status = OrderStatus.PENDING
    order.expires_at = datetime.utcnow() + timedelta(minutes=2)
    await session.commit()

    await callback.message.answer(
        "🔄 تم تمديد الانتظار لمدة دقيقتين "
        "لاستقبال كود إضافي."
    )
    await callback.answer()


# ══════════════ إنهاء الطلب ══════════════

@router.callback_query(F.data.startswith("num_finish:"))
async def finish_order_manual(
    callback: CallbackQuery, session, db_user: User
):
    order_id = int(callback.data.split(":")[1])
    order = await session.get(NumberOrder, order_id)

    if not order or order.user_id != db_user.id:
        await callback.answer(
            "⚠️ الطلب غير موجود.", show_alert=True
        )
        return

    order.awaiting_extra_code = False
    if order.status == OrderStatus.PENDING:
        order.status = OrderStatus.COMPLETED
    await session.commit()

    await callback.answer("✅ تم إنهاء الطلب.")
    try:
        await callback.message.edit_reply_markup(
            reply_markup=None
        )
    except TelegramBadRequest:
        pass
