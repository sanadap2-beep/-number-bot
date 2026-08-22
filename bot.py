"""
الملف الرئيسي لتشغيل البوت.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from database.seed import init_db

from middlewares.db_session import DbSessionMiddleware
from middlewares.user_middleware import UserMiddleware
from middlewares.subscription_middleware import SubscriptionMiddleware
from middlewares.state_reset_middleware import StateResetMiddleware

from handlers import (
    start, support, account, referral,
    deposit, transfer, numbers, loyalty, promotions,
)
from handlers.deposit_methods import router as deposit_methods_router
from handlers.games import router as games_router
from handlers.admin import (
    panel as admin_panel,
    broadcast as admin_broadcast,
    channels as admin_channels,
    countries as admin_countries,
    deposits as admin_deposits,
    users as admin_users,
    pricing as admin_pricing,
    providers as admin_providers,
    stats as admin_stats,
    settings as admin_settings,
    support as admin_support,
    categories as admin_categories,
    products as admin_products,
    api_providers as admin_api_providers,
    audit as admin_audit,
    health as admin_health,
    inventory as admin_inventory,
    loyalty as admin_loyalty,
    promotions as admin_promotions,
    coupons as admin_coupons,
    multi_admin as admin_multi_admin,
    number_services as admin_number_services,
    number_orders as admin_number_orders,
    orders as admin_orders,
    stars as admin_stars,
)

from tasks.order_monitor import (
    check_pending_orders,
    update_provider_status,
    cleanup_balance_locks,
)
from tasks.unified_order_monitor import check_unified_orders
from tasks.invoice_monitor import check_pending_invoices
from tasks.backup_job import daily_backup
from services.plisio_service import plisio_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
storage = (
    RedisStorage.from_url(settings.REDIS_URL)
    if settings.REDIS_URL
    else MemoryStorage()
)
dp = Dispatcher(storage=storage)


def register_middlewares():
    db_mw = DbSessionMiddleware()
    user_mw = UserMiddleware()
    state_reset_mw = StateResetMiddleware()
    sub_mw = SubscriptionMiddleware(bot)

    for observer in (dp.message, dp.callback_query):
        observer.outer_middleware(db_mw)
        observer.outer_middleware(user_mw)
        observer.outer_middleware(state_reset_mw)
        observer.outer_middleware(sub_mw)


def register_routers():
    # ── هاندلرز المستخدم ──
    dp.include_router(start.router)
    dp.include_router(support.router)
    dp.include_router(account.router)
    dp.include_router(referral.router)
    dp.include_router(deposit.router)
    dp.include_router(deposit_methods_router)
    dp.include_router(transfer.router)
    dp.include_router(numbers.router)
    dp.include_router(loyalty.router)
    dp.include_router(promotions.router)
    dp.include_router(games_router)

    # ── هاندلرز الأدمن ──
    dp.include_router(admin_panel.router)
    dp.include_router(admin_broadcast.router)
    dp.include_router(admin_channels.router)
    dp.include_router(admin_countries.router)
    dp.include_router(admin_deposits.router)
    dp.include_router(admin_users.router)
    dp.include_router(admin_pricing.router)
    dp.include_router(admin_providers.router)
    dp.include_router(admin_stats.router)
    dp.include_router(admin_settings.router)
    dp.include_router(admin_support.router)
    dp.include_router(admin_categories.router)
    dp.include_router(admin_products.router)
    dp.include_router(admin_api_providers.router)
    dp.include_router(admin_audit.router)
    dp.include_router(admin_health.router)
    dp.include_router(admin_inventory.router)
    dp.include_router(admin_loyalty.router)
    dp.include_router(admin_promotions.router)
    dp.include_router(admin_coupons.router)
    dp.include_router(admin_multi_admin.router)
    dp.include_router(admin_number_services.router)
    dp.include_router(admin_number_orders.router)
    dp.include_router(admin_orders.router)
    dp.include_router(admin_stars.router)


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        check_pending_orders,
        "interval",
        seconds=15,
        args=[bot],
    )

    scheduler.add_job(
        check_unified_orders,
        "interval",
        minutes=2,
        args=[bot],
    )

    scheduler.add_job(
        check_pending_invoices,
        "interval",
        seconds=max(5, settings.PLISIO_POLLING_INTERVAL_SECONDS),
        args=[bot],
    )

    scheduler.add_job(
        update_provider_status,
        "interval",
        minutes=10,
        args=[bot],
    )

    scheduler.add_job(
        cleanup_balance_locks,
        "interval",
        minutes=5,
    )

    scheduler.add_job(
        daily_backup,
        "cron",
        hour=3,
        minute=0,
        args=[bot],
    )

    scheduler.start()
    return scheduler


async def main():
    logger.info("⏳ جاري تهيئة قاعدة البيانات...")
    await init_db()
    logger.info(
        f"🔑 آيديات الأدمن: {settings.admin_ids_list}"
    )
    logger.info("✅ قاعدة البيانات جاهزة.")

    register_middlewares()
    register_routers()
    scheduler = start_scheduler()

    logger.info("🚀 البوت يعمل الآن...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await plisio_client.close()
        await bot.session.close()
        if hasattr(storage, "close"):
            await storage.close()
        logger.info("🛑 البوت توقف.")


if __name__ == "__main__":
    asyncio.run(main())
