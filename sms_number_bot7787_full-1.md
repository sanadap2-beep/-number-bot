# مشروع sms_number_bot7787 - الكود الكامل

هذا الملف يحتوي على شجرة المجلدات الكاملة وكود كل ملف في المشروع، لتسهيل فهمه من قبل أي أداة ذكاء اصطناعي.

## شجرة المجلدات

```
sms_number_bot7787/
    .env (مستثنى - يحتوي أسرار)
    .env.example
    .gitignore
    Dockerfile
    bot.py
    config.py
    docker-compose.yml
    migrate_to_usd.py
    requirements.txt
    database/
        __init__.py
        engine.py
        models.py
        seed.py
    filters/
        __init__.py
        admin_filter.py
    handlers/
        __init__.py
        account.py
        deposit.py
        deposit_methods.py
        games.py
        numbers.py
        referral.py
        start.py
        support.py
        transfer.py
        admin/
            __init__.py
            api_providers.py
            broadcast.py
            categories.py
            channels.py
            countries.py
            coupons.py
            multi_admin.py
            number_services.py
            panel.py
            pricing.py
            products.py
            providers.py
            settings.py
            stars.py
            stats.py
            users.py
    keyboards/
        __init__.py
        admin.py
        admin_categories_v2.py
        admin_products_v2.py
        admin_products_wizard.py
        admin_providers_v2.py
        common.py
        deposit_methods.py
        games.py
        main_menu.py
        numbers.py
        smm.py
    middlewares/
        __init__.py
        db_session.py
        state_reset_middleware.py
        subscription_middleware.py
        user_middleware.py
    protocols/
        __init__.py
        base.py
        factory.py
        provider_sync_service.py
        smm_v2.py
    providers/
        __init__.py
        base.py
        countries.py
        fivesim.py
        games_provider.py
        herosms.py
        manager.py
        smm_provider.py
        sms_activate.py
        smshub.py
    services/
        __init__.py
        audit_service.py
        balance_service.py
        cashback_service.py
        coupon_service.py
        currency_service.py
        dynamic_service.py
        notification_service.py
        plisio_service.py
        pricing_service.py
        product_service.py
        provider_sync_service.py
        sam_api_service.py
        settings_service.py
        stars_service.py
        subscription_service.py
    states/
        __init__.py
        states.py
    tasks/
        __init__.py
        backup_job.py
        invoice_monitor.py
        order_monitor.py
        unified_order_monitor.py
```

## محتوى الملفات

### `.env`

> تم استثناء محتوى هذا الملف لأنه يحتوي على مفاتيح/أسرار حساسة (.env).

### `.env.example`

```bash
BOT_TOKEN=
BOT_USERNAME=
ADMIN_IDS=
ADMIN_NOTIFY_CHAT_ID=

FIVESIM_API_KEY=
HEROSMS_API_KEY=

DATABASE_URL=sqlite+aiosqlite:///./bot_database.db

DEFAULT_EXCHANGE_RATE=30
DEFAULT_PROFIT_MARGIN_PERCENT=50
MIN_DEPOSIT_USD=0.5
LARGE_TRANSACTION_THRESHOLD_USD=20
REFERRAL_BONUS_USD=0.015
REQUIRE_SUBSCRIPTION_FOR_REFERRAL=true

SUPPORT_USERNAME=
PAYMENT_METHOD_TEXT=
```

### `.gitignore`

```text
.env
*.db
__pycache__/
*.pyc
venv/
.venv/
.idea/
.vscode/
*.log
```

### `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
```

### `bot.py`

```python
"""
الملف الرئيسي لتشغيل البوت.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from database.seed import init_db

from middlewares.db_session import DbSessionMiddleware
from middlewares.user_middleware import UserMiddleware
from middlewares.subscription_middleware import SubscriptionMiddleware
from middlewares.state_reset_middleware import StateResetMiddleware

from handlers import (
    start, support, account, referral,
    deposit, transfer, numbers,
)
from handlers.deposit_methods import router as deposit_methods_router
from handlers.games import router as games_router
from handlers.admin import (
    panel as admin_panel,
    broadcast as admin_broadcast,
    channels as admin_channels,
    countries as admin_countries,
    users as admin_users,
    pricing as admin_pricing,
    providers as admin_providers,
    stats as admin_stats,
    settings as admin_settings,
    categories as admin_categories,
    products as admin_products,
    api_providers as admin_api_providers,
    coupons as admin_coupons,
    multi_admin as admin_multi_admin,
    number_services as admin_number_services,
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher(storage=MemoryStorage())


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
    dp.include_router(games_router)

    # ── هاندلرز الأدمن ──
    dp.include_router(admin_panel.router)
    dp.include_router(admin_broadcast.router)
    dp.include_router(admin_channels.router)
    dp.include_router(admin_countries.router)
    dp.include_router(admin_users.router)
    dp.include_router(admin_pricing.router)
    dp.include_router(admin_providers.router)
    dp.include_router(admin_stats.router)
    dp.include_router(admin_settings.router)
    dp.include_router(admin_categories.router)
    dp.include_router(admin_products.router)
    dp.include_router(admin_api_providers.router)
    dp.include_router(admin_coupons.router)
    dp.include_router(admin_multi_admin.router)
    dp.include_router(admin_number_services.router)
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
        seconds=15,
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
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        logger.info("🛑 البوت توقف.")


if __name__ == "__main__":
    asyncio.run(main())
```

### `config.py`

```python
"""
إعدادات المشروع — تُقرأ من ملف .env
القيم المالية هنا تُستخدم فقط كـ "بذرة أولية" (seed) عند أول تشغيل،
وبعدها تُدار بالكامل من قاعدة البيانات (جدول settings) عبر لوحة الأدمن.
"""
from decimal import Decimal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # ── البوت الأساسي ──
    BOT_TOKEN: str
    BOT_USERNAME: str
    ADMIN_IDS: str

    # ── قنوات الإشعارات ──
    ADMIN_NOTIFY_CHAT_ID: int
    PUBLIC_CHANNEL_ID: int = 0
    BACKUP_CHANNEL_ID: int = 0

    # ── مزودو الأرقام ──
    FIVESIM_API_KEY: str = ""
    HEROSMS_API_KEY: str = ""
    SMS_ACTIVATE_API_KEY: str = ""
    SMSHUB_API_KEY: str = ""

    # ── Sam API (شام كاش تلقائي) ──
    SAM_API_KEY: str = ""
    SAM_API_WALLET_ADDRESS: str = ""
    SAM_API_URL: str = "https://www.sam-api.pro/api"

    # ── Plisio (USDT تلقائي) ──
    PLISIO_SECRET_KEY: str = ""
    PLISIO_API_URL: str = "https://api.plisio.net/api/v1"
    PLISIO_FEE_PERCENT: Decimal = Decimal("3.0")
    PLISIO_MIN_AMOUNT_USD: Decimal = Decimal("2.0")
    PLISIO_MAX_AMOUNT_USD: Decimal = Decimal("500.0")
    PLISIO_INVOICE_EXPIRE_MINUTES: int = 30
    PLISIO_POLLING_INTERVAL_SECONDS: int = 30

    # ── عناوين محافظ USDT اليدوي ──
    USDT_TRC20_ADDRESS: str = ""
    USDT_ERC20_ADDRESS: str = ""
    USDT_BEP20_ADDRESS: str = ""

    # ── عنوان شام كاش اليدوي ──
    SHAMCASH_MANUAL_ADDRESS: str = ""
    SHAMCASH_MANUAL_NAME: str = ""

    # ── قاعدة البيانات ──
    DATABASE_URL: str = "sqlite+aiosqlite:///./bot_database.db"

    # ── الإعدادات المالية الافتراضية (بالدولار فقط) ──
    DEFAULT_PROFIT_MARGIN_PERCENT: Decimal = Decimal("50")

    # الحدود الدنيا لكل طريقة دفع
    MIN_DEPOSIT_SHAMCASH_USD: Decimal = Decimal("0.5")
    MIN_DEPOSIT_USDT_USD: Decimal = Decimal("2")
    MIN_DEPOSIT_STARS_USD: Decimal = Decimal("1")

    # سعر صرف افتراضي USD → SYP (يُدار من لوحة الأدمن)
    DEFAULT_USD_TO_SYP_RATE: Decimal = Decimal("15000")

    LARGE_TRANSACTION_THRESHOLD_USD: Decimal = Decimal("20")
    REFERRAL_BONUS_USD: Decimal = Decimal("0.015")
    REFERRAL_PERCENT: Decimal = Decimal("5")
    CASHBACK_PERCENT: Decimal = Decimal("0")
    STARS_RATE_USD: Decimal = Decimal("0.013")
    MAX_ACTIVE_ORDERS: int = 3
    RATE_LIMIT_SECONDS: int = 30
    PROVIDER_LOW_BALANCE_THRESHOLD: Decimal = Decimal("10")
    LARGE_ORDER_CONFIRM_USD: Decimal = Decimal("20")

    # ── إعدادات عامة ──
    REQUIRE_SUBSCRIPTION_FOR_REFERRAL: bool = True
    SUPPORT_USERNAME: str = "@support"
    PAYMENT_METHOD_TEXT: str = "سيتم إضافة طريقة الدفع قريباً"
    ORDER_TIMEOUT_MINUTES: int = 5

    @property
    def admin_ids_list(self) -> list[int]:
        return [
            int(x.strip())
            for x in self.ADMIN_IDS.split(",")
            if x.strip()
        ]


settings = Settings()
```

### `docker-compose.yml`

```yaml
version: "3.9"
services:
  bot:
    build: .
    env_file: .env
    volumes:
      - ./bot_database.db:/app/bot_database.db
    restart: unless-stopped
```

### `migrate_to_usd.py`

```python
"""
سكريبت ترحيل البيانات من الروبل إلى الدولار.

⚠️ تعليمات مهمة قبل التشغيل:
1. خذ نسخة احتياطية من قاعدة البيانات أولاً:
   cp bot_database.db bot_database_backup.db
2. تأكد من إيقاف البوت قبل تشغيل هذا السكريبت.
3. شغّل السكريبت مرة واحدة فقط:
   python migrate_to_usd.py
4. بعد نجاح الترحيل، شغّل البوت من جديد.

ما يفعله هذا السكريبت:
- يحول كل أرصدة المستخدمين من روبل إلى دولار
- يحول كل مبالغ transactions من روبل إلى دولار
- يحول كل مبالغ deposit_requests من روبل إلى دولار
- يحول كل أسعار number_orders من روبل إلى دولار
- يحول كل مبالغ transfers من روبل إلى دولار
- يحذف إعداد exchange_rate_usd_rub من settings
- يضيف الإعدادات الجديدة المطلوبة
"""

import asyncio
import logging
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

DATABASE_URL = "sqlite+aiosqlite:///./bot_database.db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

# ─── سعر الصرف المستخدم للترحيل ───
# غيّر هذا الرقم إذا كان سعر الصرف الحالي مختلفاً
MIGRATION_EXCHANGE_RATE = Decimal("30")


def rub_to_usd(amount_rub: Decimal, rate: Decimal) -> Decimal:
    if rate == 0:
        return Decimal("0")
    return (amount_rub / rate).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


async def migrate():
    logger.info("=" * 60)
    logger.info("بدء ترحيل البيانات من الروبل إلى الدولار")
    logger.info(f"سعر الصرف المستخدم: 1$ = {MIGRATION_EXCHANGE_RATE} روبل")
    logger.info("=" * 60)

    async with async_session_maker() as session:

        # ── 1. ترحيل أرصدة المستخدمين ──
        logger.info("⏳ جاري ترحيل أرصدة المستخدمين...")
        users_result = await session.execute(text("SELECT id, balance FROM users"))
        users = users_result.fetchall()
        migrated_users = 0
        for user_id, balance_rub in users:
            balance_rub = Decimal(str(balance_rub))
            balance_usd = rub_to_usd(balance_rub, MIGRATION_EXCHANGE_RATE)
            await session.execute(
                text("UPDATE users SET balance = :bal WHERE id = :uid"),
                {"bal": str(balance_usd), "uid": user_id}
            )
            migrated_users += 1
        logger.info(f"✅ تم ترحيل {migrated_users} مستخدم")

        # ── 2. ترحيل transactions ──
        logger.info("⏳ جاري ترحيل سجلات المعاملات...")
        tx_result = await session.execute(
            text("SELECT id, amount, balance_after FROM transactions")
        )
        transactions = tx_result.fetchall()
        migrated_tx = 0
        for tx_id, amount_rub, balance_after_rub in transactions:
            amount_rub = Decimal(str(amount_rub))
            balance_after_rub = Decimal(str(balance_after_rub))
            amount_usd = rub_to_usd(amount_rub, MIGRATION_EXCHANGE_RATE)
            balance_after_usd = rub_to_usd(balance_after_rub, MIGRATION_EXCHANGE_RATE)
            await session.execute(
                text(
                    "UPDATE transactions SET amount = :amt, balance_after = :ba "
                    "WHERE id = :tid"
                ),
                {"amt": str(amount_usd), "ba": str(balance_after_usd), "tid": tx_id}
            )
            migrated_tx += 1
        logger.info(f"✅ تم ترحيل {migrated_tx} معاملة مالية")

        # ── 3. ترحيل deposit_requests ──
        logger.info("⏳ جاري ترحيل طلبات الإيداع...")
        deposits_result = await session.execute(
            text("SELECT id, amount_usd, amount_rub FROM deposit_requests")
        )
        deposits = deposits_result.fetchall()
        migrated_deposits = 0
        for dep_id, amount_usd_raw, amount_rub_raw in deposits:
            if amount_rub_raw is not None:
                amount_rub = Decimal(str(amount_rub_raw))
                real_usd = rub_to_usd(amount_rub, MIGRATION_EXCHANGE_RATE)
            else:
                real_usd = Decimal(str(amount_usd_raw)) if amount_usd_raw else Decimal("0")
            await session.execute(
                text(
                    "UPDATE deposit_requests SET amount_usd = :usd "
                    "WHERE id = :did"
                ),
                {"usd": str(real_usd), "did": dep_id}
            )
            migrated_deposits += 1
        logger.info(f"✅ تم ترحيل {migrated_deposits} طلب إيداع")

        # ── 4. ترحيل number_orders ──
        logger.info("⏳ جاري ترحيل طلبات الأرقام...")
        try:
            orders_result = await session.execute(
                text(
                    "SELECT id, price_provider_rub, price_sell_rub "
                    "FROM number_orders"
                )
            )
            orders = orders_result.fetchall()
            migrated_orders = 0
            for order_id, cost_rub, sell_rub in orders:
                cost_rub = Decimal(str(cost_rub))
                sell_rub = Decimal(str(sell_rub))
                cost_usd = rub_to_usd(cost_rub, MIGRATION_EXCHANGE_RATE)
                sell_usd = rub_to_usd(sell_rub, MIGRATION_EXCHANGE_RATE)
                await session.execute(
                    text(
                        "UPDATE number_orders "
                        "SET price_provider_rub = :cost, price_sell_rub = :sell "
                        "WHERE id = :oid"
                    ),
                    {"cost": str(cost_usd), "sell": str(sell_usd), "oid": order_id}
                )
                migrated_orders += 1
            logger.info(f"✅ تم ترحيل {migrated_orders} طلب رقم")
        except Exception as e:
            logger.warning(f"⚠️ تخطي ترحيل number_orders: {e}")

        # ── 5. ترحيل transfers ──
        logger.info("⏳ جاري ترحيل التحويلات...")
        try:
            transfers_result = await session.execute(
                text("SELECT id, amount FROM transfers")
            )
            transfers = transfers_result.fetchall()
            migrated_transfers = 0
            for tr_id, amount_rub in transfers:
                amount_rub = Decimal(str(amount_rub))
                amount_usd = rub_to_usd(amount_rub, MIGRATION_EXCHANGE_RATE)
                await session.execute(
                    text("UPDATE transfers SET amount = :amt WHERE id = :tid"),
                    {"amt": str(amount_usd), "tid": tr_id}
                )
                migrated_transfers += 1
            logger.info(f"✅ تم ترحيل {migrated_transfers} تحويل")
        except Exception as e:
            logger.warning(f"⚠️ تخطي ترحيل transfers: {e}")

        # ── 6. تحديث جدول settings ──
        logger.info("⏳ جاري تحديث الإعدادات...")

        settings_to_delete = [
            "exchange_rate_usd_rub",
        ]
        for key in settings_to_delete:
            await session.execute(
                text("DELETE FROM settings WHERE key = :k"),
                {"k": key}
            )
            logger.info(f"🗑 تم حذف الإعداد: {key}")

        new_settings = {
            "maintenance_mode": "false",
            "maintenance_message": "⚙️ البوت تحت الصيانة حالياً، سيعود قريباً...",
            "public_channel_id": "",
            "backup_channel_id": "",
            "stars_rate_usd": "0.013",
            "max_active_orders": "3",
            "cashback_percent": "0",
            "referral_percent": "5",
            "rate_limit_seconds": "30",
            "provider_low_balance_threshold": "10",
            "large_order_confirm_usd": "20",
            "min_deposit_usd": "0.5",
            "welcome_message": "👋 أهلاً بك في البوت!",
            "order_timeout_minutes": "5",
            "default_profit_margin_percent": "50",
            "referral_bonus_usd": "0.015",
            "require_subscription_for_referral": "true",
        }

        for key, value in new_settings.items():
            existing = await session.execute(
                text("SELECT key FROM settings WHERE key = :k"),
                {"k": key}
            )
            if existing.fetchone() is None:
                await session.execute(
                    text("INSERT INTO settings (key, value) VALUES (:k, :v)"),
                    {"k": key, "v": value}
                )
                logger.info(f"➕ تم إضافة الإعداد: {key} = {value}")
            else:
                logger.info(f"⏭ موجود مسبقاً، تخطي: {key}")

        # ── 7. تحديث total_spent_usd و cashback_earned_usd ──
        logger.info("⏳ جاري إضافة الأعمدة الجديدة للمستخدمين...")
        try:
            await session.execute(
                text("ALTER TABLE users ADD COLUMN total_spent_usd NUMERIC(18,4) DEFAULT 0")
            )
            logger.info("✅ تم إضافة عمود total_spent_usd")
        except Exception:
            logger.info("⏭ عمود total_spent_usd موجود مسبقاً")

        try:
            await session.execute(
                text("ALTER TABLE users ADD COLUMN total_orders INTEGER DEFAULT 0")
            )
            logger.info("✅ تم إضافة عمود total_orders")
        except Exception:
            logger.info("⏭ عمود total_orders موجود مسبقاً")

        try:
            await session.execute(
                text(
                    "ALTER TABLE users ADD COLUMN cashback_earned_usd "
                    "NUMERIC(18,4) DEFAULT 0"
                )
            )
            logger.info("✅ تم إضافة عمود cashback_earned_usd")
        except Exception:
            logger.info("⏭ عمود cashback_earned_usd موجود مسبقاً")

        try:
            await session.execute(
                text(
                    "ALTER TABLE deposit_requests ADD COLUMN reject_reason "
                    "VARCHAR(255)"
                )
            )
            logger.info("✅ تم إضافة عمود reject_reason")
        except Exception:
            logger.info("⏭ عمود reject_reason موجود مسبقاً")

        try:
            await session.execute(
                text(
                    "ALTER TABLE countries ADD COLUMN sms_activate_code "
                    "VARCHAR(16)"
                )
            )
            logger.info("✅ تم إضافة عمود sms_activate_code للدول")
        except Exception:
            logger.info("⏭ عمود sms_activate_code موجود مسبقاً")

        try:
            await session.execute(
                text("ALTER TABLE countries ADD COLUMN smshub_code VARCHAR(16)")
            )
            logger.info("✅ تم إضافة عمود smshub_code للدول")
        except Exception:
            logger.info("⏭ عمود smshub_code موجود مسبقاً")

        try:
            await session.execute(
                text("ALTER TABLE countries ADD COLUMN sort_order INTEGER DEFAULT 0")
            )
            logger.info("✅ تم إضافة عمود sort_order للدول")
        except Exception:
            logger.info("⏭ عمود sort_order موجود مسبقاً")

        # ── 8. إضافة أكواد المزودين الجديدة لجدول provider_status ──
        logger.info("⏳ جاري تحديث جدول provider_status...")
        new_providers = ["sms_activate", "smshub"]
        for provider_name in new_providers:
            existing_provider = await session.execute(
                text("SELECT provider FROM provider_status WHERE provider = :p"),
                {"p": provider_name}
            )
            if existing_provider.fetchone() is None:
                await session.execute(
                    text(
                        "INSERT INTO provider_status (provider, is_online) "
                        "VALUES (:p, 0)"
                    ),
                    {"p": provider_name}
                )
                logger.info(f"➕ تم إضافة مزود: {provider_name}")

        await session.commit()
        logger.info("=" * 60)
        logger.info("✅ تم الترحيل بنجاح!")
        logger.info("=" * 60)
        logger.info("الخطوات التالية:")
        logger.info("1. تحقق من البيانات في قاعدة البيانات")
        logger.info("2. شغّل البوت من جديد")
        logger.info("3. احذف هذا الملف بعد التأكد من نجاح الترحيل")
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(migrate())
```

### `requirements.txt`

```text
aiogram==3.15.0
SQLAlchemy==2.0.36
aiosqlite==0.20.0
pydantic-settings==2.6.1
aiohttp>=3.9.0,<3.11
APScheduler==3.10.4
python-dotenv==1.0.1
cryptography==42.0.5
aiofiles==23.2.1
```

### `database/__init__.py`

```python

```

### `database/engine.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)

async_session_maker = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)
```

### `database/models.py`

```python
"""
نماذج قاعدة البيانات (SQLAlchemy 2.0 Async Style).

قرارات تصميم:
1) كل الحقول المالية Numeric(18,4) وتُعامل كـ Decimal حصراً (لا float أبداً).
2) العملة الداخلية: دولار أمريكي (USD) بالكامل - لا روبل.
3) transactions دفتر أستاذ كامل لكل حركة رصيد.
4) نظام ديناميكي كامل: categories, sub_categories, products, api_providers.
5) settings جدول key-value لكل الإعدادات القابلة للتعديل من لوحة الأدمن.
6) provider_services: يحفظ كل خدمات المزودين المسحوبة (ليست منتجات للبيع بعد).
7) products: مرتبطة بـ provider_service وتحتوي سعر البيع النهائي.
8) audit_logs: يسجل كل تعديلات الأدمن للمراجعة.
"""
from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum as SAEnum, ForeignKey,
    Integer, Numeric, String, Text, func, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

MONEY = Numeric(18, 4)


class Base(DeclarativeBase):
    pass


# ═══════════════════════════ Enums ═══════════════════════════

class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    PURCHASE = "purchase"
    REFUND = "refund"
    REFERRAL_BONUS = "referral_bonus"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    ADMIN_ADD = "admin_add"
    ADMIN_DEDUCT = "admin_deduct"
    CASHBACK = "cashback"
    STARS_DEPOSIT = "stars_deposit"
    COUPON_BONUS = "coupon_bonus"


class DepositStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CODE_RECEIVED = "code_received"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class ProviderName(str, enum.Enum):
    FIVESIM = "fivesim"
    HEROSMS = "herosms"
    SMS_ACTIVATE = "sms_activate"
    SMSHUB = "smshub"


class CategoryType(str, enum.Enum):
    NUMBERS = "numbers"
    GAMES = "games"
    APPS = "apps"
    SMM = "smm"


class ProductStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class UnifiedOrderStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIAL = "partial"


class ApiProviderType(str, enum.Enum):
    NUMBERS = "numbers"
    GAMES = "games"
    SMM = "smm"


class ApiProtocolType(str, enum.Enum):
    """نوع بروتوكول التواصل مع المزود."""
    SMS = "sms"
    SMM_V2 = "smm_v2"
    GAMES_GENERIC = "games_generic"
    CUSTOM = "custom"


class ProviderServiceStatus(str, enum.Enum):
    """حالة خدمة المزود المسحوبة."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED_FROM_PROVIDER = "deleted_from_provider"


class ProviderPriceType(str, enum.Enum):
    """نوع تسعير الخدمة عند المزود."""
    PER_1000 = "per_1000"
    PER_ITEM = "per_item"
    FIXED = "fixed"


class ProductPricingType(str, enum.Enum):
    """نوع تسعير المنتج للمستخدم."""
    FIXED = "fixed"
    MARGIN_PERCENT = "margin_percent"


class ProductDisplayType(str, enum.Enum):
    """كيف يُعرض السعر للمستخدم."""
    PER_1000 = "per_1000"
    PER_MIN_QUANTITY = "per_min_quantity"
    FIXED_TOTAL = "fixed_total"


class AutoInvoiceMethod(str, enum.Enum):
    SHAMCASH_AUTO = "shamcash_auto"
    USDT_AUTO = "usdt_auto"


class AutoInvoiceStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AuditAction(str, enum.Enum):
    """أنواع عمليات الأدمن المُسجّلة في Audit Log."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    SYNC = "sync"
    PRICE_CHANGE = "price_change"
    OTHER = "other"


# ═══════════════════════════ Models ═══════════════════════════

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    balance: Mapped[Decimal] = mapped_column(
        MONEY, default=Decimal("0"), nullable=False
    )

    referrer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    is_activated: Mapped[bool] = mapped_column(Boolean, default=False)
    referral_bonus_paid: Mapped[bool] = mapped_column(Boolean, default=False)

    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)

    total_spent_usd: Mapped[Decimal] = mapped_column(
        MONEY, default=Decimal("0")
    )
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    cashback_earned_usd: Mapped[Decimal] = mapped_column(
        MONEY, default=Decimal("0")
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    referrer: Mapped["User"] = relationship(
        remote_side=[id], backref="referrals"
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    type: Mapped[TransactionType] = mapped_column(SAEnum(TransactionType))
    amount: Mapped[Decimal] = mapped_column(MONEY)
    balance_after: Mapped[Decimal] = mapped_column(MONEY)

    related_table: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    related_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    description: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    user: Mapped["User"] = relationship()


class DepositRequest(Base):
    __tablename__ = "deposit_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    amount_usd: Mapped[Decimal] = mapped_column(MONEY)
    proof_photo_file_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    proof_tx_number: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    payment_method: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )

    status: Mapped[DepositStatus] = mapped_column(
        SAEnum(DepositStatus), default=DepositStatus.PENDING
    )

    admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    admin_chat_message_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    reject_reason: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    user: Mapped["User"] = relationship(foreign_keys=[user_id])


class NumberOrder(Base):
    __tablename__ = "number_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    provider: Mapped[ProviderName] = mapped_column(SAEnum(ProviderName))
    provider_order_id: Mapped[str] = mapped_column(String(64))

    service: Mapped[str] = mapped_column(String(64))
    country_code: Mapped[str] = mapped_column(String(32))
    operator: Mapped[str | None] = mapped_column(String(32), nullable=True)
    phone_number: Mapped[str] = mapped_column(String(32))

    price_provider_usd: Mapped[Decimal] = mapped_column(MONEY)
    price_sell_usd: Mapped[Decimal] = mapped_column(MONEY)

    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus), default=OrderStatus.PENDING
    )
    sms_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_sms_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    purchased_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    status_chat_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    status_message_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )

    awaiting_extra_code: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_codes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship()


class Transfer(Base):
    __tablename__ = "transfers"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[Decimal] = mapped_column(MONEY)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name_ar: Mapped[str] = mapped_column(String(64))
    flag: Mapped[str] = mapped_column(String(8), default="🌍")

    fivesim_code: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    herosms_code: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    sms_activate_code: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    smshub_code: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    added_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class NumberService(Base):
    """
    خدمات الأرقام الديناميكية.
    تُدار بالكامل من لوحة الأدمن بدل SERVICE_MAP الثابت.
    """
    __tablename__ = "number_services"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name_ar: Mapped[str] = mapped_column(String(64))
    emoji: Mapped[str] = mapped_column(String(8), default="📱")

    fivesim_code: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    herosms_code: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    sms_activate_code: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    smshub_code: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class MandatoryChannel(Base):
    __tablename__ = "mandatory_channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username_or_link: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class ServicePricing(Base):
    __tablename__ = "service_pricing"

    id: Mapped[int] = mapped_column(primary_key=True)
    service: Mapped[str] = mapped_column(String(64))
    country_code: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    provider: Mapped[ProviderName | None] = mapped_column(
        SAEnum(ProviderName), nullable=True
    )

    margin_type: Mapped[str] = mapped_column(String(16), default="percent")
    margin_value: Mapped[Decimal] = mapped_column(
        MONEY, default=Decimal("50")
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, onupdate=func.now(), server_default=func.now()
    )


class ProviderStatus(Base):
    __tablename__ = "provider_status"

    provider: Mapped[ProviderName] = mapped_column(
        SAEnum(ProviderName), primary_key=True
    )
    balance: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, onupdate=func.now(), server_default=func.now()
    )


class BroadcastLog(Base):
    __tablename__ = "broadcast_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    total_sent: Mapped[int] = mapped_column(Integer, default=0)
    total_failed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


# ══════════════ نظام الأقسام الديناميكي ══════════════

class Category(Base):
    """
    الأقسام الرئيسية الديناميكية.
    مثال: شحن ألعاب، رشق سوشيال، تطبيقات دردشة.
    تُنشأ وتُدار بالكامل من لوحة الأدمن.
    """
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_ar: Mapped[str] = mapped_column(String(64))
    emoji: Mapped[str] = mapped_column(String(8), default="📦")
    type: Mapped[CategoryType] = mapped_column(SAEnum(CategoryType))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    sub_categories: Mapped[list["SubCategory"]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan"
    )


class SubCategory(Base):
    """
    الأقسام الفرعية الديناميكية.
    مثال: ببجي، فري فاير، إنستقرام، تيك توك.
    """
    __tablename__ = "sub_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), index=True
    )
    name_ar: Mapped[str] = mapped_column(String(64))
    emoji: Mapped[str] = mapped_column(String(8), default="📱")
    description: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    image_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    image_file_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    category: Mapped["Category"] = relationship(
        back_populates="sub_categories"
    )
    products: Mapped[list["Product"]] = relationship(
        back_populates="sub_category",
        cascade="all, delete-orphan"
    )


class ApiProvider(Base):
    """
    مزودو الألعاب والـ SMM (محسّن).
    مختلف تماماً عن مزودي الأرقام (fivesim/herosms).
    يُدار بالكامل من لوحة الأدمن.
    """
    __tablename__ = "api_providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    type: Mapped[ApiProviderType] = mapped_column(SAEnum(ApiProviderType))
    protocol_type: Mapped[ApiProtocolType] = mapped_column(
        SAEnum(ApiProtocolType),
        default=ApiProtocolType.SMM_V2,
    )
    api_url: Mapped[str] = mapped_column(String(500))
    api_key: Mapped[str] = mapped_column(String(255))
    balance: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    rate_to_usd: Mapped[Decimal] = mapped_column(
        MONEY, default=Decimal("1")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    low_balance_threshold: Mapped[Decimal] = mapped_column(
        MONEY, default=Decimal("10")
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_services: Mapped[int] = mapped_column(Integer, default=0)
    custom_config: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    services: Mapped[list["ProviderService"]] = relationship(
        back_populates="api_provider",
        cascade="all, delete-orphan"
    )
    products: Mapped[list["Product"]] = relationship(
        back_populates="api_provider"
    )


class ProviderService(Base):
    """
    جدول خدمات المزودين المسحوبة.
    كل خدمة تكون متاحة للأدمن ليُنشئ منها منتجات للبيع.
    """
    __tablename__ = "provider_services"
    __table_args__ = (
        UniqueConstraint(
            "api_provider_id",
            "external_service_id",
            name="uq_provider_service",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    api_provider_id: Mapped[int] = mapped_column(
        ForeignKey("api_providers.id"), index=True
    )

    external_service_id: Mapped[str] = mapped_column(
        String(64), index=True
    )
    name: Mapped[str] = mapped_column(String(500))
    category: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    service_type: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )

    rate: Mapped[Decimal] = mapped_column(MONEY)
    rate_usd: Mapped[Decimal] = mapped_column(MONEY)
    price_type: Mapped[ProviderPriceType] = mapped_column(
        SAEnum(ProviderPriceType),
        default=ProviderPriceType.PER_1000,
    )

    min_quantity: Mapped[int] = mapped_column(Integer, default=1)
    max_quantity: Mapped[int] = mapped_column(Integer, default=1000000)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    requires_link: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_quantity: Mapped[bool] = mapped_column(
        Boolean, default=True
    )
    requires_player_id: Mapped[bool] = mapped_column(
        Boolean, default=False
    )

    supports_refill: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_cancel: Mapped[bool] = mapped_column(Boolean, default=False)

    status: Mapped[ProviderServiceStatus] = mapped_column(
        SAEnum(ProviderServiceStatus),
        default=ProviderServiceStatus.ACTIVE,
    )

    raw_data: Mapped[str | None] = mapped_column(Text, nullable=True)

    last_updated: Mapped[datetime] = mapped_column(
        DateTime,
        onupdate=func.now(),
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    api_provider: Mapped["ApiProvider"] = relationship(
        back_populates="services"
    )
    products: Mapped[list["Product"]] = relationship(
        back_populates="provider_service"
    )


class Product(Base):
    """
    المنتجات القابلة للشراء (محسّنة).
    تنتمي لقسم فرعي وترتبط بخدمة مزود (provider_service).
    """
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sub_category_id: Mapped[int] = mapped_column(
        ForeignKey("sub_categories.id"), index=True
    )
    api_provider_id: Mapped[int | None] = mapped_column(
        ForeignKey("api_providers.id"), nullable=True
    )
    provider_service_ref_id: Mapped[int | None] = mapped_column(
        ForeignKey("provider_services.id"), nullable=True
    )

    provider_service_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    name_ar: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    image_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    image_file_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    price_usd: Mapped[Decimal] = mapped_column(MONEY)
    cost_price_usd: Mapped[Decimal] = mapped_column(
        MONEY, default=Decimal("0")
    )
    pricing_type: Mapped[ProductPricingType] = mapped_column(
        SAEnum(ProductPricingType),
        default=ProductPricingType.FIXED,
    )
    profit_margin_percent: Mapped[Decimal | None] = mapped_column(
        MONEY, nullable=True
    )
    display_type: Mapped[ProductDisplayType] = mapped_column(
        SAEnum(ProductDisplayType),
        default=ProductDisplayType.PER_1000,
    )

    min_quantity: Mapped[int] = mapped_column(Integer, default=1)
    max_quantity: Mapped[int] = mapped_column(Integer, default=1)

    requires_player_id: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_link: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_quantity: Mapped[bool] = mapped_column(Boolean, default=False)

    status: Mapped[ProductStatus] = mapped_column(
        SAEnum(ProductStatus), default=ProductStatus.ACTIVE
    )
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_bestseller: Mapped[bool] = mapped_column(Boolean, default=False)

    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    total_sold: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    sub_category: Mapped["SubCategory"] = relationship(
        back_populates="products"
    )
    api_provider: Mapped["ApiProvider | None"] = relationship(
        back_populates="products"
    )
    provider_service: Mapped["ProviderService | None"] = relationship(
        back_populates="products"
    )


class UserFavorite(Base):
    """
    منتجات المفضلة عند المستخدم.
    """
    __tablename__ = "user_favorites"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "product_id",
            name="uq_user_product_favorite",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    user: Mapped["User"] = relationship()
    product: Mapped["Product"] = relationship()


class UnifiedOrder(Base):
    """
    الطلبات الموحدة للألعاب والتطبيقات والـ SMM.
    الأرقام لها جدول NumberOrder المنفصل.
    """
    __tablename__ = "unified_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    api_provider_id: Mapped[int | None] = mapped_column(
        ForeignKey("api_providers.id"), nullable=True
    )

    external_order_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    target: Mapped[str | None] = mapped_column(String(500), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    price_usd: Mapped[Decimal] = mapped_column(MONEY)
    cost_price_usd: Mapped[Decimal] = mapped_column(
        MONEY, default=Decimal("0")
    )

    status: Mapped[UnifiedOrderStatus] = mapped_column(
        SAEnum(UnifiedOrderStatus), default=UnifiedOrderStatus.PENDING
    )
    status_message: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    result_data: Mapped[str | None] = mapped_column(Text, nullable=True)

    start_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remains: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    user: Mapped["User"] = relationship()
    product: Mapped["Product"] = relationship()
    api_provider: Mapped["ApiProvider | None"] = relationship()


class StarsPackage(Base):
    """
    باقات شحن الرصيد بنجوم تليجرام.
    تُدار بالكامل من لوحة الأدمن.
    """
    __tablename__ = "stars_packages"

    id: Mapped[int] = mapped_column(primary_key=True)
    stars_amount: Mapped[int] = mapped_column(Integer)
    usd_amount: Mapped[Decimal] = mapped_column(MONEY)
    label: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    discount_type: Mapped[str] = mapped_column(String(16), default="percent")
    discount_value: Mapped[Decimal] = mapped_column(MONEY)
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    min_order_usd: Mapped[Decimal] = mapped_column(
        MONEY, default=Decimal("0")
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    usages: Mapped[list["CouponUsage"]] = relationship(
        back_populates="coupon"
    )


class CouponUsage(Base):
    __tablename__ = "coupon_usages"
    __table_args__ = (
        UniqueConstraint("coupon_id", "user_id", name="uq_coupon_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    coupon_id: Mapped[int] = mapped_column(
        ForeignKey("coupons.id"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    discount_applied: Mapped[Decimal] = mapped_column(MONEY)
    used_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    coupon: Mapped["Coupon"] = relationship(back_populates="usages")


class CashbackLog(Base):
    __tablename__ = "cashback_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    order_id: Mapped[int] = mapped_column(Integer)
    order_type: Mapped[str] = mapped_column(String(32))
    order_amount_usd: Mapped[Decimal] = mapped_column(MONEY)
    cashback_usd: Mapped[Decimal] = mapped_column(MONEY)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class AutoInvoice(Base):
    """
    الفواتير التلقائية لطرق الدفع الآلية.
    تُستخدم مع Sam API (شام كاش) و Cryptomus (USDT).
    """
    __tablename__ = "auto_invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True
    )

    method: Mapped[AutoInvoiceMethod] = mapped_column(
        SAEnum(AutoInvoiceMethod)
    )

    external_invoice_id: Mapped[str] = mapped_column(
        String(128), unique=True, index=True
    )

    amount_usd: Mapped[Decimal] = mapped_column(MONEY)
    amount_original: Mapped[Decimal] = mapped_column(MONEY)
    currency: Mapped[str] = mapped_column(String(8))

    network: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    payment_address: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    qr_code_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    payment_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    status: Mapped[AutoInvoiceStatus] = mapped_column(
        SAEnum(AutoInvoiceStatus),
        default=AutoInvoiceStatus.PENDING,
    )
    transaction_ref: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    status_chat_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    status_message_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )

    expires_at: Mapped[datetime] = mapped_column(DateTime)
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    raw_data: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    user: Mapped["User"] = relationship()


class RateLimitLog(Base):
    __tablename__ = "rate_limit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class AuditLog(Base):
    """
    سجل تعديلات الأدمن.
    يسجل كل تعديل مهم قام به أي أدمن.

    مثال:
    - أنشأ قسم جديد
    - عدل سعر منتج
    - حذف مزود
    - غيّر إعداد
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    action: Mapped[AuditAction] = mapped_column(
        SAEnum(AuditAction)
    )

    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    entity_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )
    entity_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    description: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )

    admin: Mapped["User"] = relationship()
```

### `database/seed.py`

```python
"""
تهيئة قاعدة البيانات عند أول تشغيل:
1) إنشاء كل الجداول.
2) زرع الإعدادات الافتراضية بالدولار.
3) تسجيل الأدمن من ADMIN_IDS.
4) صفوف مبدئية لحالة المزودين.
5) باقات نجوم افتراضية.
6) خدمات أرقام افتراضية.
"""
from sqlalchemy import select

from config import settings
from database.engine import engine, async_session_maker
from database.models import (
    Base, Setting, User, ProviderStatus, ProviderName,
    StarsPackage, NumberService
)

DEFAULT_SETTINGS = {
    # ── مالي ──
    "default_profit_margin_percent": str(settings.DEFAULT_PROFIT_MARGIN_PERCENT),
    "large_transaction_threshold_usd": str(settings.LARGE_TRANSACTION_THRESHOLD_USD),
    "referral_bonus_usd": str(settings.REFERRAL_BONUS_USD),
    "referral_percent": str(settings.REFERRAL_PERCENT),
    "cashback_percent": str(settings.CASHBACK_PERCENT),
    "stars_rate_usd": str(settings.STARS_RATE_USD),
    "large_order_confirm_usd": str(settings.LARGE_ORDER_CONFIRM_USD),

    # ── سعر الصرف USD → SYP ──
    "usd_to_syp_rate": str(settings.DEFAULT_USD_TO_SYP_RATE),

    # ── الحدود الدنيا لكل طريقة دفع ──
    "min_deposit_shamcash_usd": str(settings.MIN_DEPOSIT_SHAMCASH_USD),
    "min_deposit_usdt_usd": str(settings.MIN_DEPOSIT_USDT_USD),
    "min_deposit_stars_usd": str(settings.MIN_DEPOSIT_STARS_USD),

    # ── عناوين المحافظ اليدوية ──
    "shamcash_manual_address": settings.SHAMCASH_MANUAL_ADDRESS,
    "shamcash_manual_name": settings.SHAMCASH_MANUAL_NAME,
    "usdt_trc20_address": settings.USDT_TRC20_ADDRESS,
    "usdt_erc20_address": settings.USDT_ERC20_ADDRESS,
    "usdt_bep20_address": settings.USDT_BEP20_ADDRESS,

    # ── تفعيل/تعطيل طرق الدفع ──
    "payment_shamcash_manual_enabled": "true",
    "payment_stars_enabled": "true",
    "payment_usdt_manual_enabled": "true",
    "payment_shamcash_auto_enabled": "true",
    "payment_usdt_auto_enabled": "true",
    "payment_other_enabled": "true",

    # ── شروحات طرق الدفع ──
    "payment_shamcash_manual_description": (
        "💵 <b>الشحن اليدوي عبر شام كاش</b>\n\n"
        "1️⃣ أدخل المبلغ المراد إيداعه بالدولار\n"
        "2️⃣ سيظهر لك عنوان المحفظة\n"
        "3️⃣ حوّل المبلغ من تطبيق شام كاش\n"
        "4️⃣ أرسل صورة إثبات التحويل\n"
        "5️⃣ أرسل رقم العملية\n"
        "6️⃣ انتظر موافقة الإدارة\n\n"
        f"⏱ عادة تتم الموافقة خلال 5-15 دقيقة."
    ),
    "payment_usdt_manual_description": (
        "₮ <b>الشحن اليدوي عبر USDT</b>\n\n"
        "1️⃣ اختر الشبكة (TRC20 الأرخص)\n"
        "2️⃣ أدخل المبلغ بالدولار\n"
        "3️⃣ سيظهر لك عنوان المحفظة\n"
        "4️⃣ حوّل المبلغ\n"
        "5️⃣ أرسل صورة إثبات + رقم العملية (TX Hash)\n"
        "6️⃣ انتظر موافقة الإدارة\n\n"
        "⚠️ <b>تنبيه:</b> تأكد من اختيار الشبكة الصحيحة!\n"
        "الأموال المرسلة عبر شبكة خاطئة قد تُفقد نهائياً."
    ),
    "payment_shamcash_auto_description": (
        "💳 <b>الشحن الفوري عبر شام كاش (تلقائي)</b>\n\n"
        "1️⃣ اختر العملة (USD أو SYP)\n"
        "2️⃣ أدخل المبلغ\n"
        "3️⃣ سيظهر لك عنوان الاستلام مع QR Code\n"
        "4️⃣ حوّل المبلغ من تطبيق شام كاش\n"
        "5️⃣ أدخل رقم العملية\n"
        "6️⃣ سيتم التحقق تلقائياً وإضافة الرصيد فوراً\n\n"
        "⚡ <b>سريع وفوري - لا يحتاج انتظار الأدمن!</b>\n"
        "⏱ مهلة الفاتورة: 15 دقيقة"
    ),
    "payment_usdt_auto_description": (
        "₮ <b>الشحن الفوري عبر USDT (تلقائي)</b>\n\n"
        "1️⃣ أدخل المبلغ بالدولار\n"
        "2️⃣ سيظهر لك عنوان المحفظة\n"
        "3️⃣ حوّل المبلغ\n"
        "4️⃣ يتم فحص الدفع كل 15 ثانية\n"
        "5️⃣ عند وصول التحويل يُضاف الرصيد فوراً\n\n"
        "⚡ <b>لا حاجة لإدخال رقم العملية!</b>\n"
        "⏱ مهلة الفاتورة: 30 دقيقة"
    ),
    "payment_other_description": (
        "📞 <b>طرق دفع أخرى</b>\n\n"
        "إذا كنت تريد الدفع بطريقة غير متاحة حالياً "
        "(سيرياتل كاش، MTN كاش، تحويل بنكي، بايير، إلخ)\n\n"
        "تواصل مع الدعم الفني:\n"
        "{support_username}"
    ),

    # ── نظام الطلبات ──
    "order_timeout_minutes": str(settings.ORDER_TIMEOUT_MINUTES),
    "max_active_orders": str(settings.MAX_ACTIVE_ORDERS),
    "rate_limit_seconds": str(settings.RATE_LIMIT_SECONDS),
    "provider_low_balance_threshold": str(settings.PROVIDER_LOW_BALANCE_THRESHOLD),

    # ── إعدادات عامة ──
    "require_subscription_for_referral": (
        "true" if settings.REQUIRE_SUBSCRIPTION_FOR_REFERRAL else "false"
    ),
    "support_username": settings.SUPPORT_USERNAME,
    "payment_method_text": settings.PAYMENT_METHOD_TEXT,

    # ── الصيانة ──
    "maintenance_mode": "false",
    "maintenance_message": "⚙️ البوت تحت الصيانة حالياً، سيعود قريباً...",

    # ── القنوات ──
    "public_channel_id": str(settings.PUBLIC_CHANNEL_ID),
    "backup_channel_id": str(settings.BACKUP_CHANNEL_ID),

    # ── رسالة الترحيب ──
    "welcome_message": (
        "👋 أهلاً بك في البوت!\n\n"
        "اختر من القائمة للبدء."
    ),
}

DEFAULT_STARS_PACKAGES = [
    {"stars_amount": 50,   "usd_amount": "0.65",  "label": "⭐ 50 نجمة",    "sort_order": 1},
    {"stars_amount": 100,  "usd_amount": "1.30",  "label": "⭐ 100 نجمة",   "sort_order": 2},
    {"stars_amount": 250,  "usd_amount": "3.25",  "label": "⭐ 250 نجمة",   "sort_order": 3},
    {"stars_amount": 500,  "usd_amount": "6.50",  "label": "⭐ 500 نجمة",   "sort_order": 4},
    {"stars_amount": 1000, "usd_amount": "13.00", "label": "⭐ 1000 نجمة",  "sort_order": 5},
    {"stars_amount": 2500, "usd_amount": "32.50", "label": "⭐ 2500 نجمة",  "sort_order": 6},
]

DEFAULT_NUMBER_SERVICES = [
    {
        "code": "whatsapp",
        "name_ar": "واتساب",
        "emoji": "💬",
        "fivesim_code": "whatsapp",
        "herosms_code": "wa",
        "sms_activate_code": "wa",
        "smshub_code": "whatsapp",
        "sort_order": 1,
    },
    {
        "code": "telegram",
        "name_ar": "تيليجرام",
        "emoji": "✈️",
        "fivesim_code": "telegram",
        "herosms_code": "tg",
        "sms_activate_code": "tg",
        "smshub_code": "telegram",
        "sort_order": 2,
    },
]


async def init_db() -> None:
    # ── إنشاء الجداول ──
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:

        # ── زرع الإعدادات الافتراضية ──
        for key, value in DEFAULT_SETTINGS.items():
            existing = await session.get(Setting, key)
            if existing is None:
                session.add(Setting(key=key, value=value))

        # ── تسجيل الأدمن ──
        for admin_tg_id in settings.admin_ids_list:
            result = await session.execute(
                select(User).where(User.telegram_id == admin_tg_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                session.add(User(
                    telegram_id=admin_tg_id,
                    is_admin=True,
                    is_activated=True,
                    full_name="Admin",
                ))
            elif not user.is_admin:
                user.is_admin = True

        # ── زرع حالة المزودين ──
        for provider in ProviderName:
            existing = await session.get(ProviderStatus, provider)
            if existing is None:
                session.add(ProviderStatus(
                    provider=provider,
                    is_online=False
                ))

        # ── زرع باقات النجوم الافتراضية ──
        result = await session.execute(select(StarsPackage))
        existing_packages = result.scalars().all()
        if not existing_packages:
            for pkg in DEFAULT_STARS_PACKAGES:
                from decimal import Decimal as D
                session.add(StarsPackage(
                    stars_amount=pkg["stars_amount"],
                    usd_amount=D(pkg["usd_amount"]),
                    label=pkg["label"],
                    sort_order=pkg["sort_order"],
                    is_active=True,
                ))

        # ── زرع خدمات الأرقام الافتراضية ──
        for svc in DEFAULT_NUMBER_SERVICES:
            result = await session.execute(
                select(NumberService).where(NumberService.code == svc["code"])
            )
            existing_svc = result.scalar_one_or_none()
            if existing_svc is None:
                session.add(NumberService(
                    code=svc["code"],
                    name_ar=svc["name_ar"],
                    emoji=svc["emoji"],
                    fivesim_code=svc["fivesim_code"],
                    herosms_code=svc["herosms_code"],
                    sms_activate_code=svc["sms_activate_code"],
                    smshub_code=svc["smshub_code"],
                    sort_order=svc["sort_order"],
                    is_active=True,
                ))

        await session.commit()
```

### `filters/__init__.py`

```python

```

### `filters/admin_filter.py`

```python
import logging
from aiogram.filters import BaseFilter

logger = logging.getLogger(__name__)


class IsAdmin(BaseFilter):
    async def __call__(self, event, db_user=None) -> bool:
        result = bool(db_user and db_user.is_admin)
        logger.info(
            f"🔍 DEBUG IsAdmin: db_user موجود؟ {db_user is not None} | "
            f"telegram_id={getattr(db_user, 'telegram_id', None)} | "
            f"is_admin={getattr(db_user, 'is_admin', None)} | النتيجة النهائية={result}"
        )
        return result
```

### `handlers/__init__.py`

```python

```

### `handlers/account.py`

```python
"""
صفحة حساب المستخدم.
تعرض الرصيد بالدولار، الطلبات، سجل المعاملات.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, func, desc

from database.models import (
    User, NumberOrder, UnifiedOrder,
    OrderStatus, UnifiedOrderStatus
)
from services.balance_service import BalanceService
from services.cashback_service import CashbackService

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
    if page > 0:
        kb.button(text="◀️ السابق", callback_data=f"my_uni_orders:{page - 1}")
    if page < total_pages - 1:
        kb.button(text="التالي ▶️", callback_data=f"my_uni_orders:{page + 1}")
    kb.button(text="🔙 رجوع لحسابي", callback_data="menu:account")
    kb.adjust(2, 1)

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=kb.as_markup(),
    )
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
```

### `handlers/deposit.py`

```python
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

    from config import settings as cfg
    is_admin = callback.from_user.id in cfg.admin_ids_list
    if not is_admin:
        from sqlalchemy import select
        from database.models import User as UserModel
        result = await session.execute(
            select(UserModel).where(
                UserModel.telegram_id == callback.from_user.id
            )
        )
        admin_user = result.scalar_one_or_none()
        is_admin = admin_user and admin_user.is_admin

    if not is_admin:
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
    )

    deposit.status = DepositStatus.APPROVED
    deposit.admin_id = callback.from_user.id
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

    from config import settings as cfg
    is_admin = callback.from_user.id in cfg.admin_ids_list
    if not is_admin:
        from sqlalchemy import select
        from database.models import User as UserModel
        result = await session.execute(
            select(UserModel).where(
                UserModel.telegram_id == callback.from_user.id
            )
        )
        admin_user = result.scalar_one_or_none()
        is_admin = admin_user and admin_user.is_admin

    if not is_admin:
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
    deposit.admin_id = callback.from_user.id
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
        amount = Decimal(message.text.strip())
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
```

### `handlers/deposit_methods.py`

```python
"""
هاندلر طرق الدفع الست:
1) شام كاش يدوي
2) نجوم تليجرام (في handlers/deposit.py)
3) شام كاش تلقائي (Sam API)
4) USDT تلقائي (Plisio)
5) USDT يدوي
6) طرق دفع أخرى
"""
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database.models import (
    DepositRequest, DepositStatus, User, TransactionType,
    AutoInvoice, AutoInvoiceMethod, AutoInvoiceStatus,
)
from services.settings_service import SettingsService
from services.balance_service import BalanceService
from services.notification_service import NotificationService
from services.sam_api_service import (
    sam_api_client, SamApiError, SamApiExpiredError,
)
from services.plisio_service import (
    plisio_client, PlisioError,
)
from states.states import (
    ShamCashManualStates, UsdtManualStates,
    ShamCashAutoStates, UsdtAutoStates,
)
from keyboards.admin import deposit_decision_kb
from keyboards.deposit_methods import (
    deposit_methods_kb, start_deposit_kb,
    usdt_networks_kb, shamcash_currency_kb,
    shamcash_invoice_kb, usdt_auto_invoice_kb,
    cancel_deposit_kb,
)
from keyboards.main_menu import back_to_main_kb

logger = logging.getLogger(__name__)

router = Router(name="deposit_methods")


# ══════════════ قائمة طرق الدفع الست ══════════════

async def _show_deposit_menu(target, state: FSMContext):
    """يعرض قائمة طرق الدفع الست."""
    await state.clear()

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
    kb = deposit_methods_kb(
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


# ══════════════ 6) طرق دفع أخرى ══════════════

@router.callback_query(F.data == "deposit:other")
async def deposit_other(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    support = await SettingsService.get(
        "support_username", "@support"
    )
    description = await SettingsService.get(
        "payment_other_description",
        "📞 <b>طرق دفع أخرى</b>\n\n"
        "تواصل مع الدعم:\n{support_username}"
    )
    description = description.replace(
        "{support_username}", support
    )
    await callback.message.edit_text(
        description,
        reply_markup=back_to_main_kb(),
    )


# ══════════════════════════════════════════
# ══════════════ 1) شام كاش يدوي ══════════════
# ══════════════════════════════════════════

@router.callback_query(F.data == "deposit:shamcash_manual")
async def shamcash_manual_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.answer()
    await state.clear()
    description = await SettingsService.get(
        "payment_shamcash_manual_description",
        "💵 الشحن اليدوي عبر شام كاش"
    )
    await callback.message.edit_text(
        description,
        reply_markup=start_deposit_kb("shamcash_manual"),
    )


@router.callback_query(F.data == "deposit_start:shamcash_manual")
async def shamcash_manual_amount_ask(
    callback: CallbackQuery, state: FSMContext
):
    await callback.answer()
    min_deposit = await SettingsService.get_decimal(
        "min_deposit_shamcash_usd", Decimal("0.5")
    )
    await callback.message.edit_text(
        f"💵 <b>شام كاش يدوي</b>\n\n"
        f"الحد الأدنى للشحن: <b>{min_deposit}$</b>\n\n"
        "أرسل المبلغ بالدولار (مثال: 5):",
        reply_markup=cancel_deposit_kb(),
    )
    await state.set_state(ShamCashManualStates.waiting_amount)


@router.message(ShamCashManualStates.waiting_amount)
async def shamcash_manual_amount_received(
    message: Message, state: FSMContext
):
    try:
        amount = Decimal(message.text.strip())
    except (InvalidOperation, AttributeError):
        await message.answer("⚠️ أرسل رقماً صحيحاً، مثال: 5")
        return

    min_deposit = await SettingsService.get_decimal(
        "min_deposit_shamcash_usd", Decimal("0.5")
    )
    if amount < min_deposit:
        await message.answer(
            f"⚠️ الحد الأدنى هو {min_deposit}$"
        )
        return

    await state.update_data(amount_usd=str(amount))

    address = await SettingsService.get(
        "shamcash_manual_address", ""
    )
    name = await SettingsService.get(
        "shamcash_manual_name", ""
    )
    rate = await SettingsService.get_decimal(
        "usd_to_syp_rate", Decimal("15000")
    )
    amount_syp = (amount * rate).quantize(Decimal("1"))

    text = (
        f"💵 <b>تعليمات التحويل - شام كاش</b>\n\n"
        f"💰 المبلغ المطلوب: <b>{amount}$</b>\n"
        f"💰 يعادل: <b>{amount_syp:,} ل.س</b>\n\n"
        f"📬 عنوان المحفظة:\n"
        f"<code>{address}</code>\n"
    )
    if name:
        text += f"👤 الاسم: <b>{name}</b>\n"
    text += (
        "\n📱 <b>خطوات التحويل:</b>\n"
        "1) افتح تطبيق شام كاش\n"
        "2) اضغط على تحويل\n"
        "3) الصق عنوان المحفظة أعلاه\n"
        "4) أدخل المبلغ\n"
        "5) نفذ التحويل\n\n"
        "📸 <b>الآن أرسل صورة إثبات التحويل:</b>"
    )
    await message.answer(text, reply_markup=cancel_deposit_kb())
    await state.set_state(
        ShamCashManualStates.waiting_proof_photo
    )


@router.message(
    ShamCashManualStates.waiting_proof_photo, F.photo
)
async def shamcash_manual_photo_received(
    message: Message, state: FSMContext
):
    await state.update_data(
        photo_file_id=message.photo[-1].file_id
    )
    await message.answer(
        "🔢 الآن أرسل <b>رقم عملية التحويل</b>:"
    )
    await state.set_state(
        ShamCashManualStates.waiting_tx_number
    )


@router.message(ShamCashManualStates.waiting_proof_photo)
async def shamcash_manual_photo_invalid(message: Message):
    await message.answer(
        "⚠️ الرجاء إرسال صورة إثبات التحويل (وليس نصاً)."
    )


@router.message(ShamCashManualStates.waiting_tx_number)
async def shamcash_manual_tx_received(
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
        payment_method="ShamCash Manual",
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

    await message.answer(
        "✅ تم إرسال طلب الشحن بنجاح!\n\n"
        f"💰 المبلغ: <b>{amount_usd}$</b>\n"
        f"🔢 رقم العملية: <code>{tx_number}</code>\n\n"
        "⏳ بانتظار موافقة الإدارة.\n"
        "سيصلك إشعار فور مراجعة طلبك.",
        reply_markup=back_to_main_kb(),
    )
    await state.clear()


# ══════════════════════════════════════════
# ══════════════ 5) USDT يدوي ══════════════
# ══════════════════════════════════════════

@router.callback_query(F.data == "deposit:usdt_manual")
async def usdt_manual_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.answer()
    await state.clear()
    description = await SettingsService.get(
        "payment_usdt_manual_description",
        "₮ الشحن اليدوي عبر USDT"
    )
    await callback.message.edit_text(
        description,
        reply_markup=start_deposit_kb("usdt_manual"),
    )


@router.callback_query(F.data == "deposit_start:usdt_manual")
async def usdt_manual_network_ask(
    callback: CallbackQuery, state: FSMContext
):
    await callback.answer()
    await callback.message.edit_text(
        "₮ <b>USDT يدوي</b>\n\n"
        "اختر الشبكة التي ستحوّل عبرها:\n\n"
        "🟢 <b>TRC20</b> - الأرخص (رسوم منخفضة)\n"
        "🔵 <b>ERC20</b> - رسوم مرتفعة\n"
        "🟡 <b>BEP20</b> - رسوم متوسطة",
        reply_markup=usdt_networks_kb("manual"),
    )
    await state.set_state(UsdtManualStates.waiting_network)


@router.callback_query(F.data.startswith("usdt_net:manual:"))
async def usdt_manual_network_selected(
    callback: CallbackQuery, state: FSMContext
):
    network = callback.data.split(":")[2]
    await state.update_data(network=network)
    await callback.answer()

    min_deposit = await SettingsService.get_decimal(
        "min_deposit_usdt_usd", Decimal("2")
    )
    await callback.message.edit_text(
        f"₮ <b>USDT يدوي - {network}</b>\n\n"
        f"الحد الأدنى للشحن: <b>{min_deposit}$</b>\n\n"
        "أرسل المبلغ بالدولار (مثال: 10):",
        reply_markup=cancel_deposit_kb(),
    )
    await state.set_state(UsdtManualStates.waiting_amount)


@router.message(UsdtManualStates.waiting_amount)
async def usdt_manual_amount_received(
    message: Message, state: FSMContext
):
    try:
        amount = Decimal(message.text.strip())
    except (InvalidOperation, AttributeError):
        await message.answer("⚠️ أرسل رقماً صحيحاً.")
        return

    min_deposit = await SettingsService.get_decimal(
        "min_deposit_usdt_usd", Decimal("2")
    )
    if amount < min_deposit:
        await message.answer(
            f"⚠️ الحد الأدنى هو {min_deposit}$"
        )
        return

    data = await state.get_data()
    network = data["network"]
    await state.update_data(amount_usd=str(amount))

    address_key = f"usdt_{network.lower()}_address"
    address = await SettingsService.get(address_key, "")

    if not address:
        await message.answer(
            f"⚠️ عنوان محفظة {network} غير محدد. "
            "تواصل مع الدعم."
        )
        await state.clear()
        return

    text = (
        f"₮ <b>USDT {network} - تعليمات التحويل</b>\n\n"
        f"💰 المبلغ المطلوب: <b>{amount} USDT</b>\n\n"
        f"📬 عنوان المحفظة:\n"
        f"<code>{address}</code>\n\n"
        f"⚠️ <b>تنبيهات مهمة:</b>\n"
        f"• تأكد أنك تحول عبر شبكة <b>{network}</b>\n"
        f"• الأموال المرسلة عبر شبكة خاطئة تُفقد نهائياً\n"
        f"• أرسل المبلغ المحدد بالضبط\n\n"
        "📸 <b>الآن أرسل صورة إثبات التحويل:</b>"
    )
    await message.answer(text, reply_markup=cancel_deposit_kb())
    await state.set_state(UsdtManualStates.waiting_proof_photo)


@router.message(UsdtManualStates.waiting_proof_photo, F.photo)
async def usdt_manual_photo_received(
    message: Message, state: FSMContext
):
    await state.update_data(
        photo_file_id=message.photo[-1].file_id
    )
    await message.answer(
        "🔢 الآن أرسل <b>TX Hash</b> (رقم العملية على البلوكشين):"
    )
    await state.set_state(UsdtManualStates.waiting_tx_hash)


@router.message(UsdtManualStates.waiting_proof_photo)
async def usdt_manual_photo_invalid(message: Message):
    await message.answer(
        "⚠️ الرجاء إرسال صورة إثبات التحويل."
    )


@router.message(UsdtManualStates.waiting_tx_hash)
async def usdt_manual_tx_received(
    message: Message,
    state: FSMContext,
    session,
    db_user: User,
    bot,
):
    data = await state.get_data()
    amount_usd = Decimal(data["amount_usd"])
    photo_file_id = data["photo_file_id"]
    network = data["network"]
    tx_hash = message.text.strip()

    deposit = DepositRequest(
        user_id=db_user.id,
        amount_usd=amount_usd,
        proof_photo_file_id=photo_file_id,
        proof_tx_number=tx_hash,
        payment_method=f"USDT {network} Manual",
        status=DepositStatus.PENDING,
    )
    session.add(deposit)
    await session.commit()
    await session.refresh(deposit)

    notifier = NotificationService(bot)
    caption = (
        "🆕 <b>طلب شحن USDT جديد</b>\n\n"
        f"👤 المستخدم: {db_user.telegram_id} "
        f"(@{db_user.username or '-'})\n"
        f"💵 المبلغ: <b>{amount_usd} USDT</b>\n"
        f"🌐 الشبكة: <b>{network}</b>\n"
        f"🔢 TX Hash: <code>{tx_hash}</code>\n"
        f"🆔 رقم الطلب: #{deposit.id}\n"
        f"⏰ الوقت: "
        f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"
    )
    sent_msg_id = await notifier.notify_admin_photo(
        photo_file_id=photo_file_id,
        caption=caption,
        reply_markup=deposit_decision_kb(deposit.id),
    )

    if sent_msg_id:
        deposit.admin_chat_message_id = sent_msg_id
        await session.commit()

    await message.answer(
        "✅ تم إرسال طلب الشحن بنجاح!\n\n"
        f"💰 المبلغ: <b>{amount_usd} USDT</b>\n"
        f"🌐 الشبكة: <b>{network}</b>\n"
        f"🔢 TX Hash: <code>{tx_hash}</code>\n\n"
        "⏳ بانتظار موافقة الإدارة.\n"
        "سيصلك إشعار فور مراجعة طلبك.",
        reply_markup=back_to_main_kb(),
    )
    await state.clear()


# ══════════════════════════════════════════════
# ══════════════ 3) شام كاش تلقائي ══════════════
# ══════════════════════════════════════════════

@router.callback_query(F.data == "deposit:shamcash_auto")
async def shamcash_auto_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.answer()
    await state.clear()
    description = await SettingsService.get(
        "payment_shamcash_auto_description",
        "💳 الشحن الفوري عبر شام كاش"
    )
    await callback.message.edit_text(
        description,
        reply_markup=start_deposit_kb("shamcash_auto"),
    )


@router.callback_query(F.data == "deposit_start:shamcash_auto")
async def shamcash_auto_currency_ask(
    callback: CallbackQuery, state: FSMContext
):
    await callback.answer()
    await callback.message.edit_text(
        "💳 <b>شام كاش تلقائي</b>\n\n"
        "اختر العملة التي ستدفع بها:",
        reply_markup=shamcash_currency_kb(),
    )
    await state.set_state(ShamCashAutoStates.waiting_currency)


@router.callback_query(F.data.startswith("shamcash_curr:"))
async def shamcash_auto_currency_selected(
    callback: CallbackQuery, state: FSMContext
):
    currency = callback.data.split(":")[1]
    await state.update_data(currency=currency)
    await callback.answer()

    min_deposit_usd = await SettingsService.get_decimal(
        "min_deposit_shamcash_usd", Decimal("0.5")
    )

    if currency == "USD":
        text = (
            f"💳 <b>شام كاش تلقائي - USD</b>\n\n"
            f"الحد الأدنى: <b>{min_deposit_usd}$</b>\n\n"
            "أرسل المبلغ بالدولار (مثال: 5):"
        )
    else:
        rate = await SettingsService.get_decimal(
            "usd_to_syp_rate", Decimal("15000")
        )
        min_deposit_syp = (
            min_deposit_usd * rate
        ).quantize(Decimal("1"))
        text = (
            f"💳 <b>شام كاش تلقائي - SYP</b>\n\n"
            f"الحد الأدنى: <b>{min_deposit_syp:,} ل.س</b>\n\n"
            "أرسل المبلغ بالليرة السورية (مثال: 50000):"
        )

    await callback.message.edit_text(
        text, reply_markup=cancel_deposit_kb()
    )
    await state.set_state(ShamCashAutoStates.waiting_amount)


@router.message(ShamCashAutoStates.waiting_amount)
async def shamcash_auto_amount_received(
    message: Message,
    state: FSMContext,
    session,
    db_user: User,
    bot,
):
    try:
        amount = Decimal(message.text.strip())
    except (InvalidOperation, AttributeError):
        await message.answer("⚠️ أرسل رقماً صحيحاً.")
        return

    data = await state.get_data()
    currency = data["currency"]

    min_deposit_usd = await SettingsService.get_decimal(
        "min_deposit_shamcash_usd", Decimal("0.5")
    )
    rate = await SettingsService.get_decimal(
        "usd_to_syp_rate", Decimal("15000")
    )

    if currency == "USD":
        if amount < min_deposit_usd:
            await message.answer(
                f"⚠️ الحد الأدنى هو {min_deposit_usd}$"
            )
            return
        amount_usd = amount
    else:
        min_deposit_syp = min_deposit_usd * rate
        if amount < min_deposit_syp:
            await message.answer(
                f"⚠️ الحد الأدنى هو "
                f"{min_deposit_syp:,} ل.س"
            )
            return
        amount_usd = (amount / rate).quantize(
            Decimal("0.0001")
        )

    await message.answer("⏳ جاري إنشاء الفاتورة...")

    try:
        invoice_data = await sam_api_client.create_invoice(
            amount=amount,
            currency=currency,
        )
    except SamApiError as e:
        logger.error(f"فشل إنشاء فاتورة Sam API: {e}")
        await message.answer(
            f"❌ فشل إنشاء الفاتورة:\n<code>{e}</code>\n\n"
            "حاول مجدداً لاحقاً أو استخدم طريقة دفع أخرى.",
            reply_markup=back_to_main_kb(),
        )
        await state.clear()
        return

    external_id = invoice_data.get("invoiceId")
    payment_url = invoice_data.get("paymentUrl")
    expires_at_str = invoice_data.get("expiresAt")

    if not external_id:
        await message.answer(
            "❌ خطأ في استجابة الخادم.",
            reply_markup=back_to_main_kb(),
        )
        await state.clear()
        return

    try:
        expires_at = datetime.fromisoformat(
            expires_at_str.replace("Z", "+00:00")
        ).replace(tzinfo=None)
    except Exception:
        expires_at = datetime.utcnow() + timedelta(
            minutes=15
        )

    address = await SettingsService.get(
        "shamcash_manual_address", ""
    )

    invoice = AutoInvoice(
        user_id=db_user.id,
        method=AutoInvoiceMethod.SHAMCASH_AUTO,
        external_invoice_id=external_id,
        amount_usd=amount_usd,
        amount_original=amount,
        currency=currency,
        payment_address=address,
        payment_url=payment_url,
        status=AutoInvoiceStatus.PENDING,
        expires_at=expires_at,
        raw_data=json.dumps(
            invoice_data, ensure_ascii=False
        ),
    )
    session.add(invoice)
    await session.commit()
    await session.refresh(invoice)

    remaining = expires_at - datetime.utcnow()
    minutes = int(remaining.total_seconds() // 60)
    seconds = int(remaining.total_seconds() % 60)

    text = (
        "💳 <b>فاتورة شام كاش</b>\n\n"
        f"⏱ الوقت المتبقي: <b>{minutes}:{seconds:02d}</b>\n"
        f"💰 المبلغ المطلوب: <b>{amount} {currency}</b>\n"
        f"💵 يعادل: <b>{amount_usd}$</b>\n\n"
        f"📬 عنوان الاستلام:\n"
        f"<code>{address}</code>\n\n"
        f"📱 <b>خطوات الدفع:</b>\n"
        "1) افتح تطبيق شام كاش\n"
        "2) حوّل المبلغ للعنوان أعلاه\n"
        "3) انسخ رقم العملية من التطبيق\n"
        "4) أرسل رقم العملية هنا للتحقق\n\n"
        "🔢 <b>أرسل رقم العملية الآن:</b>"
    )

    status_msg = await message.answer(
        text,
        reply_markup=shamcash_invoice_kb(
            invoice.id, payment_url
        ),
    )
    invoice.status_chat_id = status_msg.chat.id
    invoice.status_message_id = status_msg.message_id
    await session.commit()

    await state.update_data(invoice_id=invoice.id)
    await state.set_state(
        ShamCashAutoStates.waiting_transaction_ref
    )


@router.message(
    ShamCashAutoStates.waiting_transaction_ref
)
async def shamcash_auto_tx_received(
    message: Message,
    state: FSMContext,
    session,
    db_user: User,
    bot,
):
    tx_ref = message.text.strip()
    if not tx_ref:
        await message.answer("⚠️ أرسل رقم العملية.")
        return

    data = await state.get_data()
    invoice_id = data.get("invoice_id")
    invoice = await session.get(AutoInvoice, invoice_id)

    if not invoice:
        await message.answer("⚠️ الفاتورة غير موجودة.")
        await state.clear()
        return

    if invoice.status != AutoInvoiceStatus.PENDING:
        await message.answer(
            "⚠️ هذه الفاتورة تمت معالجتها مسبقاً."
        )
        await state.clear()
        return

    if datetime.utcnow() > invoice.expires_at:
        invoice.status = AutoInvoiceStatus.EXPIRED
        await session.commit()
        await message.answer(
            "⌛ انتهت صلاحية الفاتورة. أنشئ فاتورة جديدة.",
            reply_markup=back_to_main_kb(),
        )
        await state.clear()
        return

    await message.answer("⏳ جاري التحقق من الدفع...")

    try:
        result = await sam_api_client.verify_invoice(
            invoice_id=invoice.external_invoice_id,
            transaction_ref=tx_ref,
        )
    except SamApiExpiredError:
        invoice.status = AutoInvoiceStatus.EXPIRED
        await session.commit()
        await message.answer(
            "⌛ انتهت صلاحية الفاتورة.",
            reply_markup=back_to_main_kb(),
        )
        await state.clear()
        return
    except SamApiError as e:
        logger.error(f"فشل التحقق من فاتورة Sam API: {e}")
        await message.answer(
            f"❌ فشل التحقق:\n<code>{e}</code>\n\n"
            "تأكد من رقم العملية وحاول مجدداً.",
        )
        return

    if result.get("verified"):
        invoice.status = AutoInvoiceStatus.PAID
        invoice.transaction_ref = tx_ref
        invoice.paid_at = datetime.utcnow()
        await session.commit()

        await BalanceService.add_balance(
            session,
            db_user.id,
            invoice.amount_usd,
            TransactionType.DEPOSIT,
            description=(
                f"شحن شام كاش تلقائي - "
                f"فاتورة #{invoice.id}"
            ),
            related_table="auto_invoices",
            related_id=invoice.id,
        )

        notifier = NotificationService(bot)
        await notifier.notify_admin(
            f"💳 <b>شحن شام كاش تلقائي</b>\n\n"
            f"👤 المستخدم: {db_user.telegram_id} "
            f"(@{db_user.username or '-'})\n"
            f"💵 المبلغ: <b>{invoice.amount_usd}$</b>\n"
            f"💰 الأصلي: {invoice.amount_original} "
            f"{invoice.currency}\n"
            f"🔢 رقم العملية: <code>{tx_ref}</code>"
        )

        await message.answer(
            f"✅ <b>تم شحن رصيدك بنجاح!</b>\n\n"
            f"💰 تمت إضافة <b>{invoice.amount_usd}$</b> "
            f"إلى رصيدك.\n"
            f"يمكنك الآن استخدام رصيدك.",
            reply_markup=back_to_main_kb(),
        )
        await state.clear()
    else:
        msg = result.get(
            "message",
            "لم يتم العثور على رقم العملية"
        )
        await message.answer(
            f"❌ فشل التحقق:\n<b>{msg}</b>\n\n"
            "تأكد من:\n"
            "• صحة رقم العملية\n"
            "• أن التحويل تم بنجاح\n"
            "• أن المبلغ صحيح\n\n"
            "أرسل رقم العملية مجدداً أو ألغِ الفاتورة."
        )


@router.callback_query(F.data.startswith("sc_verify:"))
async def shamcash_auto_verify_button(
    callback: CallbackQuery, state: FSMContext
):
    invoice_id = int(callback.data.split(":")[1])
    await state.update_data(invoice_id=invoice_id)
    await state.set_state(
        ShamCashAutoStates.waiting_transaction_ref
    )
    await callback.answer()
    await callback.message.answer(
        "🔢 أرسل رقم العملية للتحقق:"
    )


@router.callback_query(F.data.startswith("sc_cancel:"))
async def shamcash_auto_cancel(
    callback: CallbackQuery, session, state: FSMContext
):
    invoice_id = int(callback.data.split(":")[1])
    invoice = await session.get(AutoInvoice, invoice_id)

    if invoice and invoice.status == AutoInvoiceStatus.PENDING:
        invoice.status = AutoInvoiceStatus.CANCELLED
        await session.commit()

    await callback.answer("❌ تم إلغاء الفاتورة.")
    await state.clear()
    try:
        await callback.message.edit_text(
            "❌ تم إلغاء الفاتورة.",
            reply_markup=back_to_main_kb(),
        )
    except Exception:
        await callback.message.answer(
            "❌ تم إلغاء الفاتورة.",
            reply_markup=back_to_main_kb(),
        )


# ══════════════════════════════════════════
# ══════════════ 4) USDT تلقائي (Plisio) ══════════════
# ══════════════════════════════════════════

@router.callback_query(F.data == "deposit:usdt_auto")
async def usdt_auto_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.answer()
    await state.clear()
    description = await SettingsService.get(
        "payment_usdt_auto_description",
        "₮ الشحن الفوري عبر USDT"
    )
    await callback.message.edit_text(
        description,
        reply_markup=start_deposit_kb("usdt_auto"),
    )


@router.callback_query(F.data == "deposit_start:usdt_auto")
async def usdt_auto_amount_ask(
    callback: CallbackQuery, state: FSMContext
):
    await callback.answer()
    min_deposit = await SettingsService.get_decimal(
        "min_deposit_usdt_usd", Decimal("2")
    )
    await callback.message.edit_text(
        f"₮ <b>USDT تلقائي (TRC20)</b>\n\n"
        f"الحد الأدنى: <b>{min_deposit}$</b>\n\n"
        "أرسل المبلغ بالدولار (مثال: 10):",
        reply_markup=cancel_deposit_kb(),
    )
    await state.set_state(UsdtAutoStates.waiting_amount)


@router.message(UsdtAutoStates.waiting_amount)
async def usdt_auto_amount_received(
    message: Message,
    state: FSMContext,
    session,
    db_user: User,
    bot,
):
    try:
        amount = Decimal(message.text.strip())
    except (InvalidOperation, AttributeError):
        await message.answer("⚠️ أرسل رقماً صحيحاً.")
        return

    min_deposit = await SettingsService.get_decimal(
        "min_deposit_usdt_usd", Decimal("2")
    )
    if amount < min_deposit:
        await message.answer(
            f"⚠️ الحد الأدنى هو {min_deposit}$"
        )
        return

    fee_percent = await SettingsService.get_decimal(
        "plisio_fee_percent", Decimal("3.0")
    )
    amount_with_fee = (
        amount * (Decimal("1") + fee_percent / Decimal("100"))
    ).quantize(Decimal("0.01"))

    await message.answer("⏳ جاري إنشاء الفاتورة...")

    order_id = (
        f"user_{db_user.id}_"
        f"{int(datetime.utcnow().timestamp())}"
    )

    try:
        payment_data = await plisio_client.create_payment(
            amount=amount_with_fee,
            order_id=order_id,
            currency="USDT_TRX",
            order_name=f"Deposit for user {db_user.id}",
        )
    except PlisioError as e:
        logger.error(f"فشل إنشاء فاتورة Plisio: {e}")
        await message.answer(
            f"❌ فشل إنشاء الفاتورة:\n<code>{e}</code>\n\n"
            "حاول مجدداً لاحقاً أو استخدم طريقة دفع أخرى.",
            reply_markup=back_to_main_kb(),
        )
        await state.clear()
        return

    external_id = payment_data.get("uuid")
    address = payment_data.get("address")
    payment_url = payment_data.get("url")
    payer_amount = payment_data.get(
        "payer_amount", str(amount_with_fee)
    )
    expired_at_ts = payment_data.get("expired_at")

    if not external_id or not address:
        await message.answer(
            "❌ خطأ في استجابة الخادم.",
            reply_markup=back_to_main_kb(),
        )
        await state.clear()
        return

    if expired_at_ts:
        try:
            expires_at = datetime.utcfromtimestamp(
                int(expired_at_ts)
            )
        except (ValueError, TypeError):
            expires_at = datetime.utcnow() + timedelta(
                minutes=30
            )
    else:
        expires_at = datetime.utcnow() + timedelta(
            minutes=30
        )

    invoice = AutoInvoice(
        user_id=db_user.id,
        method=AutoInvoiceMethod.USDT_AUTO,
        external_invoice_id=external_id,
        amount_usd=amount,
        amount_original=Decimal(str(payer_amount)),
        currency="USDT",
        network="TRC20",
        payment_address=address,
        payment_url=payment_url,
        status=AutoInvoiceStatus.PENDING,
        expires_at=expires_at,
        raw_data=json.dumps(
            payment_data, ensure_ascii=False,
            default=str
        ),
    )
    session.add(invoice)
    await session.commit()
    await session.refresh(invoice)

    remaining = expires_at - datetime.utcnow()
    minutes = int(remaining.total_seconds() // 60)

    text = (
        "₮ <b>فاتورة USDT (TRC20)</b>\n\n"
        f"⏱ الوقت المتبقي: <b>{minutes} دقيقة</b>\n"
        f"💰 المبلغ المطلوب: <b>{payer_amount} USDT</b>\n"
        f"💵 يعادل: <b>{amount}$</b>\n"
        f"💸 يشمل رسوم: <b>{fee_percent}%</b>\n\n"
        f"📬 عنوان المحفظة:\n"
        f"<code>{address}</code>\n\n"
        "⚠️ <b>مهم جداً:</b>\n"
        "• حوّل عبر شبكة <b>TRC20</b> فقط\n"
        "• أرسل المبلغ المحدد بالضبط\n"
        "• سيتم فحص الدفع كل 30 ثانية\n"
        "• عند وصول التحويل يُضاف الرصيد تلقائياً\n\n"
        "✨ لا حاجة لإدخال رقم العملية!"
    )

    status_msg = await message.answer(
        text,
        reply_markup=usdt_auto_invoice_kb(
            invoice.id, payment_url
        ),
    )
    invoice.status_chat_id = status_msg.chat.id
    invoice.status_message_id = status_msg.message_id
    await session.commit()
    await state.clear()


@router.callback_query(F.data.startswith("usdt_check:"))
async def usdt_auto_check_button(
    callback: CallbackQuery, session, bot
):
    invoice_id = int(callback.data.split(":")[1])
    invoice = await session.get(AutoInvoice, invoice_id)

    if not invoice:
        await callback.answer(
            "⚠️ الفاتورة غير موجودة.", show_alert=True
        )
        return

    if invoice.status == AutoInvoiceStatus.PAID:
        await callback.answer(
            "✅ الفاتورة مدفوعة بالفعل.", show_alert=True
        )
        return

    if invoice.status != AutoInvoiceStatus.PENDING:
        await callback.answer(
            "⚠️ هذه الفاتورة تمت معالجتها.", show_alert=True
        )
        return

    await callback.answer("⏳ جاري الفحص...")

    try:
        info = await plisio_client.get_payment_info(
            uuid=invoice.external_invoice_id
        )
    except PlisioError as e:
        logger.error(f"فشل فحص فاتورة Plisio: {e}")
        await callback.message.answer(
            f"⚠️ خطأ في الفحص: {e}"
        )
        return

    status = info.get("status", "process")

    if plisio_client.is_paid_status(status):
        from tasks.invoice_monitor import (
            _process_paid_usdt_invoice
        )
        await _process_paid_usdt_invoice(
            session, invoice, info, bot
        )
        await callback.message.answer(
            "✅ تم الدفع! أُضيف الرصيد لحسابك."
        )
    elif plisio_client.is_failed_status(status):
        invoice.status = AutoInvoiceStatus.FAILED
        await session.commit()
        await callback.message.answer(
            "❌ فشلت الفاتورة."
        )
    else:
        await callback.message.answer(
            f"⏳ الفاتورة قيد المعالجة (الحالة: {status})\n"
            "سيتم إشعارك تلقائياً عند اكتمال الدفع."
        )


@router.callback_query(F.data.startswith("usdt_cancel:"))
async def usdt_auto_cancel(
    callback: CallbackQuery, session
):
    invoice_id = int(callback.data.split(":")[1])
    invoice = await session.get(AutoInvoice, invoice_id)

    if invoice and invoice.status == AutoInvoiceStatus.PENDING:
        invoice.status = AutoInvoiceStatus.CANCELLED
        await session.commit()

    await callback.answer("❌ تم إلغاء الفاتورة.")
    try:
        await callback.message.edit_text(
            "❌ تم إلغاء الفاتورة.",
            reply_markup=back_to_main_kb(),
        )
    except Exception:
        await callback.message.answer(
            "❌ تم إلغاء الفاتورة.",
            reply_markup=back_to_main_kb(),
        )
```

### `handlers/games.py`

```python
"""
هاندلر موحد لشراء المنتجات (ألعاب + تطبيقات + SMM).
كل الأقسام تعمل بنفس المنطق:
1) المستخدم يختار القسم الرئيسي → القسم الفرعي → المنتج
2) يدخل البيانات المطلوبة (Player ID أو رابط أو كمية)
3) يتم التحقق من الرصيد
4) يُرسل الطلب للمزود تلقائياً
5) يُتابع الطلب من order_monitor
"""
import logging
from decimal import Decimal

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.orm import selectinload

from database.models import (
    User, UnifiedOrder, UnifiedOrderStatus,
    TransactionType, Product, ProductStatus,
    CategoryType,
)
from services.dynamic_service import DynamicService
from services.balance_service import BalanceService, InsufficientBalanceError
from services.notification_service import NotificationService
from services.settings_service import SettingsService
from services.coupon_service import CouponService, CouponError
from services.cashback_service import CashbackService
from providers.games_provider import GamesProviderClient, GamesProviderError
from providers.smm_provider import SMMProviderClient, SMMProviderError
from states.states import GamesOrderStates, AppsOrderStates, SMMOrderStates
from keyboards.games import (
    sub_categories_kb, products_kb,
    product_confirm_kb, product_confirm_with_coupon_kb,
)
from keyboards.main_menu import (
    insufficient_balance_kb, confirm_large_order_kb,
    back_to_main_kb,
)

logger = logging.getLogger(__name__)

router = Router(name="games")


# ══════════════ اختيار القسم الرئيسي ══════════════

@router.callback_query(F.data.startswith("cat:"))
async def category_selected(
    callback: CallbackQuery, session
):
    category_id = int(callback.data.split(":")[1])
    category = await DynamicService.get_category(
        session, category_id
    )
    if not category or not category.is_active:
        await callback.answer(
            "⚠️ هذا القسم غير متاح حالياً.",
            show_alert=True,
        )
        return

    await callback.answer()
    sub_cats = await DynamicService.get_active_sub_categories(
        session, category_id
    )

    if not sub_cats:
        await callback.message.edit_text(
            f"{category.emoji} <b>{category.name_ar}</b>\n\n"
            "⚠️ لا توجد أقسام فرعية متاحة حالياً.",
            reply_markup=back_to_main_kb(),
        )
        return

    await callback.message.edit_text(
        f"{category.emoji} <b>{category.name_ar}</b>\n\n"
        "اختر القسم الفرعي:",
        reply_markup=sub_categories_kb(category_id, sub_cats),
    )


# ══════════════ اختيار القسم الفرعي ══════════════

@router.callback_query(F.data.startswith("subcat:"))
async def sub_category_selected(
    callback: CallbackQuery, session
):
    sub_cat_id = int(callback.data.split(":")[1])
    sub_cat = await DynamicService.get_sub_category(
        session, sub_cat_id
    )
    if not sub_cat or not sub_cat.is_active:
        await callback.answer(
            "⚠️ هذا القسم غير متاح.",
            show_alert=True,
        )
        return

    await callback.answer()
    products = await DynamicService.get_active_products(
        session, sub_cat_id
    )

    if not products:
        await callback.message.edit_text(
            f"{sub_cat.emoji} <b>{sub_cat.name_ar}</b>\n\n"
            "⚠️ لا توجد منتجات متاحة حالياً.",
            reply_markup=back_to_main_kb(),
        )
        return

    await callback.message.edit_text(
        f"{sub_cat.emoji} <b>{sub_cat.name_ar}</b>\n\n"
        "اختر المنتج:",
        reply_markup=products_kb(
            sub_cat_id, products, sub_cat.category_id
        ),
    )


# ══════════════ اختيار المنتج ══════════════

@router.callback_query(F.data.startswith("prod:"))
async def product_selected(
    callback: CallbackQuery,
    session,
    db_user: User,
    state: FSMContext,
):
    product_id = int(callback.data.split(":")[1])
    product = await DynamicService.get_product(
        session, product_id
    )

    if not product or product.status != ProductStatus.ACTIVE:
        await callback.answer(
            "⚠️ هذا المنتج غير متاح.",
            show_alert=True,
        )
        return

    await callback.answer()

    # ── فحص الرصيد ──
    if db_user.balance < product.price_usd:
        notifier = NotificationService(callback.bot)
        await notifier.notify_insufficient_balance(
            user_telegram_id=db_user.telegram_id,
            required_usd=str(product.price_usd),
            current_balance_usd=f"{db_user.balance:.2f}",
            reply_markup=insufficient_balance_kb(),
        )
        return

    sub_cat = product.sub_category

    # ── تحديد نوع الإدخال المطلوب ──
    if product.requires_player_id:
        await callback.message.edit_text(
            f"🎮 <b>{product.name_ar}</b>\n"
            f"💰 السعر: <b>{product.price_usd}$</b>\n\n"
            "أرسل <b>آيدي اللاعب</b> (Player ID):",
        )
        await state.update_data(product_id=product_id)
        await state.set_state(GamesOrderStates.waiting_player_id)

    elif product.requires_link:
        if product.requires_quantity:
            await callback.message.edit_text(
                f"📈 <b>{product.name_ar}</b>\n"
                f"💰 السعر: <b>{product.price_usd}$</b> "
                f"/ {product.min_quantity}\n"
                f"📊 الحد الأدنى: {product.min_quantity} | "
                f"الحد الأقصى: {product.max_quantity}\n\n"
                "أرسل <b>الرابط</b>:",
            )
            await state.update_data(product_id=product_id)
            await state.set_state(SMMOrderStates.waiting_link)
        else:
            await callback.message.edit_text(
                f"📈 <b>{product.name_ar}</b>\n"
                f"💰 السعر: <b>{product.price_usd}$</b>\n\n"
                "أرسل <b>الرابط</b>:",
            )
            await state.update_data(
                product_id=product_id,
                quantity=1,
            )
            await state.set_state(SMMOrderStates.waiting_link)

    else:
        await callback.message.edit_text(
            f"📦 <b>{product.name_ar}</b>\n"
            f"💰 السعر: <b>{product.price_usd}$</b>\n\n"
            "هل تريد تأكيد الشراء؟",
            reply_markup=product_confirm_kb(
                product_id,
                sub_cat.id if sub_cat else 0,
            ),
        )


# ══════════════ إدخال Player ID ══════════════

@router.message(GamesOrderStates.waiting_player_id)
async def player_id_received(
    message: Message,
    state: FSMContext,
    session,
    db_user: User,
):
    player_id = message.text.strip()
    if not player_id:
        await message.answer("⚠️ أرسل آيدي اللاعب بشكل صحيح.")
        return

    data = await state.get_data()
    product_id = data["product_id"]
    product = await DynamicService.get_product(
        session, product_id
    )

    if not product:
        await message.answer("⚠️ المنتج غير موجود.")
        await state.clear()
        return

    await state.update_data(
        target=player_id,
        quantity=1,
    )

    sub_cat = product.sub_category
    await message.answer(
        f"🎮 <b>{product.name_ar}</b>\n"
        f"🎯 آيدي اللاعب: <code>{player_id}</code>\n"
        f"💰 السعر: <b>{product.price_usd}$</b>\n\n"
        "هل تريد تأكيد الشراء؟",
        reply_markup=product_confirm_kb(
            product_id,
            sub_cat.id if sub_cat else 0,
        ),
    )
    await state.clear()


# ══════════════ إدخال الرابط (SMM) ══════════════

@router.message(SMMOrderStates.waiting_link)
async def smm_link_received(
    message: Message, state: FSMContext, session
):
    link = message.text.strip()
    if not link.startswith("http"):
        await message.answer(
            "⚠️ أرسل رابطاً صحيحاً يبدأ بـ http"
        )
        return

    data = await state.get_data()
    product_id = data["product_id"]
    product = await DynamicService.get_product(
        session, product_id
    )

    if not product:
        await message.answer("⚠️ المنتج غير موجود.")
        await state.clear()
        return

    await state.update_data(target=link)

    if product.requires_quantity:
        await message.answer(
            f"📊 أرسل <b>الكمية</b> المطلوبة:\n"
            f"الحد الأدنى: {product.min_quantity}\n"
            f"الحد الأقصى: {product.max_quantity}"
        )
        await state.set_state(SMMOrderStates.waiting_quantity)
    else:
        await state.update_data(quantity=1)
        sub_cat = product.sub_category
        await message.answer(
            f"📈 <b>{product.name_ar}</b>\n"
            f"🔗 الرابط: {link}\n"
            f"💰 السعر: <b>{product.price_usd}$</b>\n\n"
            "هل تريد تأكيد الشراء؟",
            reply_markup=product_confirm_kb(
                product_id,
                sub_cat.id if sub_cat else 0,
            ),
        )
        await state.clear()


# ══════════════ إدخال الكمية (SMM) ══════════════

@router.message(SMMOrderStates.waiting_quantity)
async def smm_quantity_received(
    message: Message, state: FSMContext, session
):
    try:
        quantity = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ أرسل رقماً صحيحاً.")
        return

    data = await state.get_data()
    product_id = data["product_id"]
    product = await DynamicService.get_product(
        session, product_id
    )

    if not product:
        await message.answer("⚠️ المنتج غير موجود.")
        await state.clear()
        return

    if quantity < product.min_quantity:
        await message.answer(
            f"⚠️ الحد الأدنى هو {product.min_quantity}"
        )
        return
    if quantity > product.max_quantity:
        await message.answer(
            f"⚠️ الحد الأقصى هو {product.max_quantity}"
        )
        return

    total_price = (
        product.price_usd * Decimal(str(quantity))
        / Decimal(str(product.min_quantity))
    ).quantize(Decimal("0.0001"))

    await state.update_data(
        quantity=quantity,
        total_price=str(total_price),
    )

    sub_cat = product.sub_category
    link = data.get("target", "—")

    await message.answer(
        f"📈 <b>{product.name_ar}</b>\n"
        f"🔗 الرابط: {link}\n"
        f"📊 الكمية: {quantity}\n"
        f"💰 السعر الإجمالي: <b>{total_price}$</b>\n\n"
        "هل تريد تأكيد الشراء؟",
        reply_markup=product_confirm_kb(
            product_id,
            sub_cat.id if sub_cat else 0,
        ),
    )
    await state.clear()


# ══════════════ كوبون الخصم ══════════════

@router.callback_query(F.data.startswith("prod_coupon:"))
async def product_coupon_start(
    callback: CallbackQuery, state: FSMContext
):
    product_id = int(callback.data.split(":")[1])
    await state.update_data(coupon_product_id=product_id)
    await callback.message.answer("🎟 أرسل كود الكوبون:")
    await state.set_state(GamesOrderStates.waiting_coupon)
    await callback.answer()


@router.message(GamesOrderStates.waiting_coupon)
async def product_coupon_received(
    message: Message,
    state: FSMContext,
    session,
    db_user: User,
):
    data = await state.get_data()
    product_id = data.get("coupon_product_id")
    product = await DynamicService.get_product(
        session, product_id
    )

    if not product:
        await message.answer("⚠️ المنتج غير موجود.")
        await state.clear()
        return

    code = message.text.strip()
    try:
        coupon = await CouponService.validate_coupon(
            session, code, db_user.id, product.price_usd
        )
    except CouponError as e:
        await message.answer(str(e))
        await state.clear()
        return

    discount = CouponService.calculate_discount(
        coupon, product.price_usd
    )
    sub_cat = product.sub_category

    await message.answer(
        f"🎟 <b>كوبون: {coupon.code}</b>\n"
        f"💰 السعر الأصلي: {product.price_usd}$\n"
        f"🎁 الخصم: {discount}$\n"
        f"💵 السعر بعد الخصم: "
        f"<b>{product.price_usd - discount}$</b>",
        reply_markup=product_confirm_with_coupon_kb(
            product_id,
            sub_cat.id if sub_cat else 0,
            coupon.code,
            str(discount),
        ),
    )
    await state.clear()


# ══════════════ تأكيد الشراء ══════════════

@router.callback_query(F.data.startswith("prod_confirm:"))
async def product_confirm(
    callback: CallbackQuery,
    session,
    db_user: User,
    bot,
    state: FSMContext,
):
    product_id = int(callback.data.split(":")[1])
    await _execute_purchase(
        callback, session, db_user, bot, state,
        product_id, coupon_code=None,
    )


@router.callback_query(
    F.data.startswith("prod_confirm_coupon:")
)
async def product_confirm_with_coupon(
    callback: CallbackQuery,
    session,
    db_user: User,
    bot,
    state: FSMContext,
):
    parts = callback.data.split(":")
    product_id = int(parts[1])
    coupon_code = parts[2]
    await _execute_purchase(
        callback, session, db_user, bot, state,
        product_id, coupon_code=coupon_code,
    )


async def _execute_purchase(
    callback: CallbackQuery,
    session,
    db_user: User,
    bot,
    state: FSMContext,
    product_id: int,
    coupon_code: str | None,
):
    product = await DynamicService.get_product(
        session, product_id
    )
    if not product or product.status != ProductStatus.ACTIVE:
        await callback.answer(
            "⚠️ المنتج غير متاح.", show_alert=True
        )
        return

    await callback.answer("⏳ جاري تنفيذ الطلب...")

    fsm_data = await state.get_data()
    target = fsm_data.get("target", "")
    quantity = fsm_data.get("quantity", 1)

    # ── حساب السعر ──
    if product.requires_quantity and quantity > 1:
        total_price = (
            product.price_usd * Decimal(str(quantity))
            / Decimal(str(product.min_quantity))
        ).quantize(Decimal("0.0001"))
    else:
        total_price = product.price_usd

    # ── تطبيق الكوبون ──
    discount = Decimal("0")
    coupon = None
    if coupon_code:
        try:
            coupon = await CouponService.validate_coupon(
                session, coupon_code, db_user.id, total_price
            )
            discount = CouponService.calculate_discount(
                coupon, total_price
            )
        except CouponError:
            discount = Decimal("0")
            coupon = None

    final_price = total_price - discount

    # ── تأكيد الطلبات الكبيرة ──
    large_confirm = await SettingsService.get_decimal(
        "large_order_confirm_usd", Decimal("20")
    )
    if final_price >= large_confirm:
        await callback.message.answer(
            f"⚠️ <b>تأكيد الطلب الكبير</b>\n\n"
            f"المنتج: {product.name_ar}\n"
            f"المبلغ: <b>{final_price}$</b>\n\n"
            "هل أنت متأكد؟",
            reply_markup=confirm_large_order_kb(
                f"prod_final:{product_id}:{coupon_code or 'none'}:{target}:{quantity}"
            ),
        )
        return

    await _finalize_purchase(
        callback, session, db_user, bot,
        product, target, quantity,
        final_price, discount, coupon,
    )


@router.callback_query(F.data.startswith("prod_final:"))
async def product_final_confirm(
    callback: CallbackQuery,
    session,
    db_user: User,
    bot,
    state: FSMContext,
):
    parts = callback.data.split(":")
    product_id = int(parts[1])
    coupon_code = parts[2] if parts[2] != "none" else None
    target = parts[3] if len(parts) > 3 else ""
    quantity = int(parts[4]) if len(parts) > 4 else 1

    product = await DynamicService.get_product(
        session, product_id
    )
    if not product:
        await callback.answer("⚠️ المنتج غير متاح.", show_alert=True)
        return

    await callback.answer("⏳ جاري تنفيذ الطلب...")

    if product.requires_quantity and quantity > 1:
        total_price = (
            product.price_usd * Decimal(str(quantity))
            / Decimal(str(product.min_quantity))
        ).quantize(Decimal("0.0001"))
    else:
        total_price = product.price_usd

    discount = Decimal("0")
    coupon = None
    if coupon_code:
        try:
            coupon = await CouponService.validate_coupon(
                session, coupon_code, db_user.id, total_price
            )
            discount = CouponService.calculate_discount(
                coupon, total_price
            )
        except CouponError:
            pass

    final_price = total_price - discount

    await _finalize_purchase(
        callback, session, db_user, bot,
        product, target, quantity,
        final_price, discount, coupon,
    )


async def _finalize_purchase(
    callback,
    session,
    db_user,
    bot,
    product,
    target,
    quantity,
    final_price,
    discount,
    coupon,
):
    notifier = NotificationService(bot)

    # ── فحص الرصيد ──
    if db_user.balance < final_price:
        await notifier.notify_insufficient_balance(
            user_telegram_id=db_user.telegram_id,
            required_usd=str(final_price),
            current_balance_usd=f"{db_user.balance:.2f}",
            reply_markup=insufficient_balance_kb(),
        )
        return

    # ── خصم الرصيد ──
    try:
        await BalanceService.deduct_balance(
            session, db_user.id, final_price,
            TransactionType.PURCHASE,
            description=f"شراء {product.name_ar}",
            is_purchase=True,
        )
    except InsufficientBalanceError:
        await callback.message.answer("⚠️ رصيدك غير كافٍ.")
        return

    # ── تسجيل استخدام الكوبون ──
    if coupon and discount > 0:
        await CouponService.apply_coupon(
            session, coupon, db_user.id, discount
        )

    # ── إرسال الطلب للمزود ──
    external_order_id = None
    order_status = UnifiedOrderStatus.PENDING
    status_message = "بانتظار التنفيذ"

    if product.api_provider_id and product.provider_service_id:
        provider = product.api_provider
        if provider and provider.is_active:
            try:
                if provider.type.value == "smm":
                    client = SMMProviderClient(provider)
                    result = await client.place_order(
                        service_id=product.provider_service_id,
                        link=target,
                        quantity=quantity,
                    )
                else:
                    client = GamesProviderClient(provider)
                    result = await client.place_order(
                        service_id=product.provider_service_id,
                        target=target,
                        quantity=quantity,
                    )
                external_order_id = result.get("order_id")
                order_status = UnifiedOrderStatus.PROCESSING
                status_message = "تم إرسال الطلب للمزود"
            except (GamesProviderError, SMMProviderError) as e:
                logger.error(
                    f"فشل إرسال الطلب للمزود: {e}"
                )
                await BalanceService.add_balance(
                    session, db_user.id, final_price,
                    TransactionType.REFUND,
                    description="استرجاع - فشل الإرسال للمزود",
                )
                await callback.message.answer(
                    "❌ فشل إرسال الطلب للمزود. "
                    "تم استرجاع رصيدك بالكامل."
                )
                return

    # ── حفظ الطلب ──
    order = UnifiedOrder(
        user_id=db_user.id,
        product_id=product.id,
        api_provider_id=product.api_provider_id,
        external_order_id=external_order_id,
        target=target,
        quantity=quantity,
        price_usd=final_price,
        cost_price_usd=product.cost_price_usd,
        status=order_status,
        status_message=status_message,
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)

    # ── تحديث عداد المبيعات ──
    await DynamicService.increment_product_sold(
        session, product.id, quantity
    )

    # ── كاشباك ──
    cashback = await CashbackService.apply_cashback(
        session, db_user.id,
        order.id, "unified_orders",
        final_price,
    )

    # ── رسالة النجاح ──
    result_text = (
        f"✅ <b>تم إرسال طلبك بنجاح!</b>\n\n"
        f"🆔 رقم الطلب: #{order.id}\n"
        f"📦 المنتج: {product.name_ar}\n"
        f"💰 المبلغ: {final_price}$\n"
    )
    if discount > 0:
        result_text += f"🎟 الخصم: {discount}$\n"
    if cashback > 0:
        result_text += f"🎁 كاشباك: {cashback}$\n"
    if target:
        result_text += f"🎯 الهدف: <code>{target}</code>\n"
    if quantity > 1:
        result_text += f"📊 الكمية: {quantity}\n"
    result_text += (
        f"\n📊 الحالة: {status_message}\n"
        "ستصلك إشعارات بتحديث حالة طلبك."
    )

    await callback.message.answer(result_text)

    # ── إشعار الأدمن ──
    await notifier.notify_admin(
        f"🛒 <b>طلب شراء جديد</b>\n\n"
        f"👤 المستخدم: {db_user.telegram_id} "
        f"(@{db_user.username or '-'})\n"
        f"📦 المنتج: {product.name_ar}\n"
        f"💰 المبلغ: {final_price}$\n"
        f"🎯 الهدف: {target or '—'}\n"
        f"📊 الكمية: {quantity}\n"
        f"🆔 طلب #{order.id}"
    )

    # ── إشعار القناة العامة ──
    await notifier.notify_successful_unified_order(
        username=db_user.username,
        full_name=db_user.full_name,
        product_name=product.name_ar,
        price_usd=str(final_price),
    )
```

### `handlers/numbers.py`

```python
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
```

### `handlers/referral.py`

```python
"""
نظام الإحالة.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func

from config import settings
from database.models import User
from services.settings_service import SettingsService
from keyboards.main_menu import back_to_main_kb

router = Router(name="referral")


@router.message(F.text == "💎 دعوة أصدقاء")
async def referral_handler(
    message: Message, session, db_user: User
):
    await _send_referral_info(message, session, db_user)


@router.callback_query(F.data == "menu:referral")
async def referral_handler_cb(
    callback: CallbackQuery, session, db_user: User
):
    await callback.answer()
    await _send_referral_info(
        callback.message, session, db_user
    )


async def _send_referral_info(
    message: Message, session, db_user: User
):
    link = (
        f"https://t.me/{settings.BOT_USERNAME}"
        f"?start=ref_{db_user.telegram_id}"
    )

    result = await session.execute(
        select(func.count(User.id)).where(
            User.referrer_id == db_user.id
        )
    )
    referrals_count = result.scalar_one()

    bonus_usd = await SettingsService.get_decimal(
        "referral_bonus_usd"
    )
    referral_percent = await SettingsService.get_decimal(
        "referral_percent"
    )

    await message.answer(
        "💎 <b>نظام الإحالة</b>\n\n"
        "شارك الرابط التالي مع أصدقائك وستحصل على "
        "مكافآت عن كل شخص ينضم ويُفعّل حسابه:\n\n"
        f"🔗 <code>{link}</code>\n\n"
        f"💰 مكافأة الإحالة: <b>{bonus_usd}$</b> "
        f"عن كل مستخدم جديد\n"
        f"📈 نسبة من مشتريات المُحالين: "
        f"<b>{referral_percent}%</b>\n\n"
        f"👥 عدد إحالاتك: <b>{referrals_count}</b>",
        reply_markup=back_to_main_kb(),
    )
```

### `handlers/start.py`

```python
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
```

### `handlers/support.py`

```python
"""
الدعم الفني.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from services.settings_service import SettingsService
from keyboards.main_menu import back_to_main_kb

router = Router(name="support")


@router.message(F.text == "🛠 الدعم الفني")
async def support_handler(message: Message):
    await _send_support(message)


@router.callback_query(F.data == "menu:support")
async def support_handler_cb(callback: CallbackQuery):
    await callback.answer()
    await _send_support(callback.message)


async def _send_support(message: Message):
    support_username = await SettingsService.get(
        "support_username", "@support"
    )
    await message.answer(
        f"🛠 <b>الدعم الفني</b>\n\n"
        f"للتواصل مع فريق الدعم اضغط: "
        f"{support_username}\n\n"
        "⏰ أوقات الاستجابة: خلال 24 ساعة",
        reply_markup=back_to_main_kb(),
    )
```

### `handlers/transfer.py`

```python
"""
تحويل الرصيد بين المستخدمين.
"""
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from database.models import User, TransactionType, Transfer
from services.balance_service import (
    BalanceService, InsufficientBalanceError
)
from services.notification_service import NotificationService
from services.settings_service import SettingsService
from states.states import TransferStates
from keyboards.main_menu import back_to_main_kb

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
    except InvalidOperation:
        await message.answer("⚠️ الرجاء إرسال رقم صحيح.")
        return

    if amount <= 0:
        await message.answer(
            "⚠️ المبلغ يجب أن يكون أكبر من صفر."
        )
        return

    data = await state.get_data()
    recipient_id = data["recipient_id"]
    recipient_tg_id = data["recipient_tg_id"]

    try:
        await BalanceService.deduct_balance(
            session, db_user.id, amount,
            TransactionType.TRANSFER_OUT,
            description=f"تحويل إلى {recipient_tg_id}",
        )
    except InsufficientBalanceError:
        await message.answer(
            "⚠️ رصيدك غير كافٍ لإتمام هذا التحويل."
        )
        await state.clear()
        return

    try:
        await BalanceService.add_balance(
            session, recipient_id, amount,
            TransactionType.TRANSFER_IN,
            description=f"تحويل من {db_user.telegram_id}",
        )
    except Exception:
        await BalanceService.add_balance(
            session, db_user.id, amount,
            TransactionType.REFUND,
            description=(
                f"استرجاع - فشل التحويل إلى "
                f"{recipient_tg_id}"
            ),
        )
        await session.commit()
        await message.answer(
            "⚠️ تعذّر إتمام التحويل بسبب خطأ تقني. "
            "تم استرجاع المبلغ لرصيدك بالكامل."
        )
        await state.clear()
        return

    session.add(Transfer(
        from_user_id=db_user.id,
        to_user_id=recipient_id,
        amount=amount,
    ))
    await session.commit()

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
```

### `handlers/admin/__init__.py`

```python

```

### `handlers/admin/api_providers.py`

```python
"""
إدارة المزودين V2 - محسّنة بالكامل.

يدعم:
- Wizard كامل لإضافة مزود (بروتوكول → نوع → اسم → URL → API Key → عملة → اختبار)
- سحب الخدمات في الخلفية مع إشعار عند الاكتمال
- عرض قائمة المزودين مع الحالة وعدد الخدمات
- البحث في خدمات المزود
- عرض الخدمات مع Pagination
- تعديل كامل لبيانات المزود
- حذف مع تأكيد
"""
import asyncio
import json
import logging
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from config import settings as cfg
from database.models import (
    ApiProvider,
    ApiProviderType,
    ApiProtocolType,
    ProviderService,
    ProviderServiceStatus,
)
from services.dynamic_service import DynamicService
from services.provider_sync_service import (
    ProviderSyncService,
)
from services.currency_service import CurrencyService
from states.states import (
    AdminApiProviderStates,
    AdminProviderServicesStates,
)
from keyboards.admin_providers_v2 import (
    providers_list_kb,
    select_protocol_kb,
    select_provider_type_kb,
    select_currency_kb,
    test_connection_kb,
    ask_sync_now_kb,
    provider_detail_kb,
    confirm_delete_provider_kb,
    provider_services_kb,
    provider_service_detail_kb,
    cancel_search_kb,
    sync_in_progress_kb,
    SERVICES_PER_PAGE,
)
from keyboards.admin import admin_back_kb
from filters.admin_filter import IsAdmin

logger = logging.getLogger(__name__)

router = Router(name="admin_api_providers")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# ══════════════════════════════════════════════
# ══════════════ قائمة المزودين ══════════════
# ══════════════════════════════════════════════

@router.callback_query(F.data == "admin:api_providers")
async def providers_list(callback: CallbackQuery, session):
    providers = await DynamicService.get_all_providers(session)

    if not providers:
        text = (
            "🔌 <b>إدارة المزودين</b>\n\n"
            "لا يوجد مزودين مسجلين حتى الآن.\n"
            "اضغط الزر أدناه لإضافة مزود جديد."
        )
    else:
        text = (
            "🔌 <b>إدارة المزودين</b>\n\n"
            f"عدد المزودين: <b>{len(providers)}</b>\n\n"
            "🟢 = مفعّل | 🔴 = معطّل\n"
            "اضغط على أي مزود لعرض التفاصيل."
        )

    await callback.message.edit_text(
        text,
        reply_markup=providers_list_kb(providers),
    )


# ══════════════════════════════════════════════
# ══════════════ إضافة مزود - الخطوة 1 ══════════════
# ══════════════════════════════════════════════

@router.callback_query(F.data == "admin:aprov_add")
async def aprov_add_start(
    callback: CallbackQuery, state: FSMContext
):
    await state.clear()
    await callback.message.edit_text(
        "🔌 <b>إضافة مزود جديد</b>\n\n"
        "الخطوة 1️⃣ من 6️⃣\n\n"
        "اختر نوع البروتوكول:\n\n"
        "📈 <b>SMM V2</b>: بروتوكول قياسي لمواقع "
        "رشق السوشيال (JumboSMM, SMMGold, PeakSMM, إلخ)\n\n"
        "🎮 <b>Games</b>: لمواقع شحن الألعاب "
        "<i>(قريباً)</i>\n\n"
        "🛠 <b>Custom</b>: لأي موقع مخصص "
        "<i>(قريباً)</i>",
        reply_markup=select_protocol_kb(),
    )
    await state.set_state(
        AdminApiProviderStates.waiting_protocol_type
    )


@router.callback_query(F.data.startswith("admin:aprov_proto:"))
async def aprov_protocol_selected(
    callback: CallbackQuery, state: FSMContext
):
    protocol_key = callback.data.split(":")[2]

    if protocol_key not in ("smm_v2",):
        await callback.answer(
            "⏳ هذا البروتوكول قيد التطوير. "
            "استخدم SMM V2 حالياً.",
            show_alert=True,
        )
        return

    try:
        protocol_type = ApiProtocolType(protocol_key)
    except ValueError:
        await callback.answer(
            "❌ بروتوكول غير صالح", show_alert=True
        )
        return

    await state.update_data(
        protocol_type=protocol_type.value
    )
    await callback.answer()

    await callback.message.edit_text(
        f"✅ البروتوكول: <b>{protocol_type.value.upper()}</b>\n\n"
        "الخطوة 2️⃣ من 6️⃣\n\n"
        "اختر نوع المزود:",
        reply_markup=select_provider_type_kb(),
    )
    await state.set_state(
        AdminApiProviderStates.waiting_type
    )


@router.callback_query(F.data.startswith("admin:aprov_ptype:"))
async def aprov_type_selected(
    callback: CallbackQuery, state: FSMContext
):
    type_key = callback.data.split(":")[2]

    try:
        provider_type = ApiProviderType(type_key)
    except ValueError:
        await callback.answer(
            "❌ نوع غير صالح", show_alert=True
        )
        return

    await state.update_data(provider_type=provider_type.value)
    await callback.answer()

    await callback.message.edit_text(
        f"✅ النوع: <b>{provider_type.value}</b>\n\n"
        "الخطوة 3️⃣ من 6️⃣\n\n"
        "📝 أرسل اسم المزود:\n"
        "(مثال: <code>JumboSMM</code> أو "
        "<code>SMMGold</code>)",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(
        AdminApiProviderStates.waiting_name
    )


@router.message(AdminApiProviderStates.waiting_name)
async def aprov_name_received(
    message: Message, state: FSMContext
):
    name = message.text.strip()

    if len(name) < 2:
        await message.answer("⚠️ الاسم قصير جداً.")
        return

    if len(name) > 64:
        await message.answer(
            "⚠️ الاسم طويل جداً (الحد الأقصى 64 حرف)."
        )
        return

    await state.update_data(name=name)

    await message.answer(
        f"✅ الاسم: <b>{name}</b>\n\n"
        "الخطوة 4️⃣ من 6️⃣\n\n"
        "🔗 أرسل رابط API الخاص بالمزود:\n"
        "(مثال: <code>https://jumbosmm.com/api/v2</code>)"
    )
    await state.set_state(
        AdminApiProviderStates.waiting_api_url
    )


@router.message(AdminApiProviderStates.waiting_api_url)
async def aprov_url_received(
    message: Message, state: FSMContext
):
    url = message.text.strip()

    if not url.startswith(("http://", "https://")):
        await message.answer(
            "⚠️ يجب أن يبدأ الرابط بـ http:// أو https://"
        )
        return

    if len(url) > 500:
        await message.answer(
            "⚠️ الرابط طويل جداً."
        )
        return

    await state.update_data(api_url=url)

    await message.answer(
        f"✅ الرابط محفوظ\n\n"
        "الخطوة 5️⃣ من 6️⃣\n\n"
        "🔑 أرسل مفتاح API (API Key):"
    )
    await state.set_state(
        AdminApiProviderStates.waiting_api_key
    )


@router.message(AdminApiProviderStates.waiting_api_key)
async def aprov_key_received(
    message: Message, state: FSMContext
):
    api_key = message.text.strip()

    if len(api_key) < 5:
        await message.answer(
            "⚠️ المفتاح قصير جداً. تأكد من إدخاله كاملاً."
        )
        return

    await state.update_data(api_key=api_key)

    try:
        await message.delete()
    except Exception:
        pass

    await message.answer(
        "✅ المفتاح محفوظ\n\n"
        "الخطوة 6️⃣ من 6️⃣\n\n"
        "💱 اختر عملة المزود:\n"
        "(عملة الأسعار في لوحة المزود)",
        reply_markup=select_currency_kb(),
    )
    await state.set_state(
        AdminApiProviderStates.waiting_currency
    )


@router.callback_query(F.data.startswith("admin:aprov_curr:"))
async def aprov_currency_selected(
    callback: CallbackQuery, state: FSMContext, session
):
    currency_code = callback.data.split(":")[2]

    if currency_code == "custom":
        await callback.message.edit_text(
            "✏️ أرسل رمز العملة (3 أحرف):\n"
            "(مثال: <code>USD</code> أو <code>UAH</code>)"
        )
        await state.set_state(
            AdminApiProviderStates.waiting_currency
        )
        await state.update_data(waiting_custom_currency=True)
        await callback.answer()
        return

    await state.update_data(currency=currency_code)

    rate = await CurrencyService.get_rate_to_usd(
        currency_code, session
    )
    await state.update_data(rate_to_usd=str(rate))

    await callback.answer()
    await _show_summary_and_test(callback.message, state)


@router.message(AdminApiProviderStates.waiting_currency)
async def aprov_custom_currency_received(
    message: Message, state: FSMContext, session
):
    data = await state.get_data()
    if not data.get("waiting_custom_currency"):
        return

    currency = message.text.strip().upper()

    if len(currency) != 3 or not currency.isalpha():
        await message.answer(
            "⚠️ العملة يجب أن تكون 3 أحرف فقط (مثل USD)"
        )
        return

    await state.update_data(currency=currency)
    await state.update_data(waiting_custom_currency=False)

    rate = await CurrencyService.get_rate_to_usd(
        currency, session
    )
    await state.update_data(rate_to_usd=str(rate))

    await _show_summary_and_test(message, state)


async def _show_summary_and_test(
    message: Message, state: FSMContext
):
    """يعرض ملخص البيانات وزر اختبار الاتصال."""
    data = await state.get_data()

    text = (
        "📋 <b>ملخص بيانات المزود</b>\n\n"
        f"🔌 البروتوكول: <b>{data['protocol_type'].upper()}</b>\n"
        f"📁 النوع: <b>{data['provider_type']}</b>\n"
        f"📝 الاسم: <b>{data['name']}</b>\n"
        f"🔗 URL: <code>{data['api_url'][:50]}...</code>\n"
        f"💱 العملة: <b>{data['currency']}</b>\n"
        f"💵 سعر الصرف: 1 {data['currency']} = "
        f"{data['rate_to_usd']} USD\n\n"
        "اضغط الزر أدناه لاختبار الاتصال وحفظ المزود:"
    )

    await message.answer(
        text,
        reply_markup=test_connection_kb(),
    )
    # ══════════════════════════════════════════════
# ══════════════ اختبار الاتصال + الحفظ ══════════════
# ══════════════════════════════════════════════

@router.callback_query(F.data == "admin:aprov_test")
async def aprov_test_and_save(
    callback: CallbackQuery, state: FSMContext, session
):
    data = await state.get_data()

    required_fields = [
        "protocol_type", "provider_type", "name",
        "api_url", "api_key", "currency",
    ]
    for field in required_fields:
        if field not in data:
            await callback.answer(
                f"⚠️ حقل ناقص: {field}", show_alert=True
            )
            return

    await callback.answer("⏳ جاري اختبار الاتصال...")

    test_msg = await callback.message.edit_text(
        "⏳ <b>جاري اختبار الاتصال...</b>\n\n"
        f"مزود: {data['name']}\n"
        f"URL: <code>{data['api_url'][:50]}...</code>"
    )

    try:
        temp_provider = ApiProvider(
            name=data["name"],
            type=ApiProviderType(data["provider_type"]),
            protocol_type=ApiProtocolType(
                data["protocol_type"]
            ),
            api_url=data["api_url"],
            api_key=data["api_key"],
            currency=data["currency"],
            rate_to_usd=Decimal(data["rate_to_usd"]),
        )
    except Exception as e:
        await test_msg.edit_text(
            f"❌ خطأ في البيانات: {e}",
            reply_markup=admin_back_kb(),
        )
        await state.clear()
        return

    success, message_text, balance, currency = (
        await ProviderSyncService.test_provider_connection(
            temp_provider
        )
    )

    if not success:
        await test_msg.edit_text(
            f"❌ <b>فشل الاتصال بالمزود!</b>\n\n"
            f"السبب: <code>{message_text}</code>\n\n"
            "تأكد من:\n"
            "• صحة الـ API URL\n"
            "• صحة الـ API Key\n"
            "• اتصال الإنترنت\n"
            "• أن المزود يدعم البروتوكول المحدد",
            reply_markup=admin_back_kb(),
        )
        await state.clear()
        return

    provider = ApiProvider(
        name=data["name"],
        type=ApiProviderType(data["provider_type"]),
        protocol_type=ApiProtocolType(
            data["protocol_type"]
        ),
        api_url=data["api_url"],
        api_key=data["api_key"],
        currency=currency or data["currency"],
        rate_to_usd=Decimal(data["rate_to_usd"]),
        balance=balance,
        is_active=True,
        priority=1,
        low_balance_threshold=Decimal("10"),
    )
    session.add(provider)
    await session.commit()
    await session.refresh(provider)

    logger.info(
        f"تم إضافة مزود جديد: "
        f"#{provider.id} - {provider.name}"
    )

    balance_display = (
        f"{balance} {currency}" if balance else "غير معروف"
    )
    balance_usd = None
    if balance and currency:
        balance_usd = (
            balance * Decimal(data["rate_to_usd"])
        ).quantize(Decimal("0.01"))

    text = (
        "✅ <b>تم إضافة المزود بنجاح!</b>\n\n"
        f"📝 الاسم: <b>{provider.name}</b>\n"
        f"🔌 البروتوكول: {provider.protocol_type.value.upper()}\n"
        f"💰 الرصيد: <b>{balance_display}</b>"
    )
    if balance_usd:
        text += f"\n💵 يعادل: <b>{balance_usd}$</b>"
    text += (
        "\n\n<b>هل تريد سحب خدمات المزود الآن؟</b>\n"
        "قد يستغرق وقتاً إذا كانت الخدمات كثيرة."
    )

    await test_msg.edit_text(
        text,
        reply_markup=ask_sync_now_kb(provider.id),
    )
    await state.clear()


# ══════════════════════════════════════════════
# ══════════════ تفاصيل المزود ══════════════
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:aprov_view:"))
async def aprov_view(callback: CallbackQuery, session):
    provider_id = int(callback.data.split(":")[2])
    provider = await session.get(ApiProvider, provider_id)

    if not provider:
        await callback.answer(
            "⚠️ المزود غير موجود.", show_alert=True
        )
        return

    await _show_provider_details(
        callback.message, provider, edit=True
    )


async def _show_provider_details(
    message, provider: ApiProvider, edit: bool = True
):
    """يعرض تفاصيل مزود."""
    status = (
        "🟢 مفعّل" if provider.is_active else "🔴 معطّل"
    )
    type_label = {
        "smm": "📈 رشق SMM",
        "games": "🎮 ألعاب",
        "numbers": "📞 أرقام",
    }.get(provider.type.value, provider.type.value)

    balance_text = (
        f"{provider.balance} {provider.currency}"
        if provider.balance is not None
        else "غير معروف"
    )

    balance_usd = None
    if provider.balance is not None:
        balance_usd = (
            provider.balance * provider.rate_to_usd
        ).quantize(Decimal("0.01"))

    last_check = (
        provider.last_checked_at.strftime("%Y-%m-%d %H:%M")
        if provider.last_checked_at
        else "—"
    )
    last_sync = (
        provider.last_sync_at.strftime("%Y-%m-%d %H:%M")
        if provider.last_sync_at
        else "لم يتم بعد"
    )

    api_url_display = (
        provider.api_url[:40] + "..."
        if len(provider.api_url) > 40
        else provider.api_url
    )
    api_key_display = (
        provider.api_key[:8] + "***"
        if len(provider.api_key) > 8
        else "***"
    )

    text = (
        f"🔌 <b>{provider.name}</b>\n\n"
        f"📁 النوع: {type_label}\n"
        f"🔧 البروتوكول: "
        f"{provider.protocol_type.value.upper()}\n"
        f"📊 الحالة: {status}\n"
        f"🎯 الأولوية: {provider.priority}\n\n"
        f"💰 الرصيد: <b>{balance_text}</b>\n"
    )
    if balance_usd:
        text += f"💵 يعادل: <b>{balance_usd}$</b>\n"
    text += (
        f"💱 العملة: {provider.currency}\n"
        f"📈 سعر الصرف: 1 {provider.currency} = "
        f"{provider.rate_to_usd}$\n\n"
        f"🔗 URL: <code>{api_url_display}</code>\n"
        f"🔑 API Key: <code>{api_key_display}</code>\n\n"
        f"📦 عدد الخدمات: <b>"
        f"{provider.total_services or 0}</b>\n"
        f"🕐 آخر فحص: {last_check}\n"
        f"🔄 آخر مزامنة: {last_sync}\n"
    )

    if provider.last_error:
        text += (
            f"\n⚠️ آخر خطأ: "
            f"<code>{provider.last_error[:150]}</code>"
        )

    kb = provider_detail_kb(provider)

    if edit:
        try:
            await message.edit_text(text, reply_markup=kb)
        except Exception:
            await message.answer(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


# ══════════════════════════════════════════════
# ══════════════ تفعيل / تعطيل ══════════════
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:aprov_toggle:"))
async def aprov_toggle(callback: CallbackQuery, session):
    provider_id = int(callback.data.split(":")[2])
    provider = await session.get(ApiProvider, provider_id)

    if not provider:
        await callback.answer(
            "⚠️ غير موجود", show_alert=True
        )
        return

    provider.is_active = not provider.is_active
    await session.commit()

    status_text = (
        "✅ تم تفعيل" if provider.is_active
        else "❌ تم تعطيل"
    )
    await callback.answer(f"{status_text} المزود.")

    await session.refresh(provider)
    await _show_provider_details(
        callback.message, provider, edit=True
    )


# ══════════════════════════════════════════════
# ══════════════ تحديث الرصيد ══════════════
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:aprov_balance:"))
async def aprov_check_balance(
    callback: CallbackQuery, session
):
    provider_id = int(callback.data.split(":")[2])
    provider = await session.get(ApiProvider, provider_id)

    if not provider:
        await callback.answer(
            "⚠️ غير موجود", show_alert=True
        )
        return

    await callback.answer("⏳ جاري فحص الرصيد...")

    success, msg = await (
        ProviderSyncService.update_provider_balance(
            provider_id
        )
    )

    await session.refresh(provider)

    if success:
        await callback.message.answer(
            f"✅ <b>{provider.name}</b>\n{msg}"
        )
    else:
        await callback.message.answer(
            f"❌ فشل تحديث الرصيد:\n<code>{msg}</code>"
        )

    await _show_provider_details(
        callback.message, provider, edit=False
    )


# ══════════════════════════════════════════════
# ══════════════ مزامنة الخدمات ══════════════
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:aprov_sync:"))
async def aprov_sync_services(
    callback: CallbackQuery, session, bot
):
    provider_id = int(callback.data.split(":")[2])
    provider = await session.get(ApiProvider, provider_id)

    if not provider:
        await callback.answer(
            "⚠️ غير موجود", show_alert=True
        )
        return

    await callback.answer("⏳ جاري بدء المزامنة...")

    progress_msg = await callback.message.edit_text(
        f"🔄 <b>جاري مزامنة خدمات {provider.name}...</b>\n\n"
        "⏱ قد تستغرق العملية عدة دقائق حسب عدد الخدمات.\n"
        "سيصلك إشعار عند الاكتمال.",
        reply_markup=sync_in_progress_kb(provider_id),
    )

    admin_chat_id = callback.from_user.id

    asyncio.create_task(
        _sync_in_background(
            bot=bot,
            provider_id=provider_id,
            admin_chat_id=admin_chat_id,
            progress_message_id=progress_msg.message_id,
        )
    )


async def _sync_in_background(
    bot,
    provider_id: int,
    admin_chat_id: int,
    progress_message_id: int,
):
    """ينفذ المزامنة في الخلفية."""
    try:
        result = await (
            ProviderSyncService.sync_provider_services(
                provider_id
            )
        )

        try:
            await bot.edit_message_text(
                chat_id=admin_chat_id,
                message_id=progress_message_id,
                text=result.summary(),
                reply_markup=sync_in_progress_kb(
                    provider_id
                ),
            )
        except Exception:
            await bot.send_message(
                chat_id=admin_chat_id,
                text=result.summary(),
                reply_markup=sync_in_progress_kb(
                    provider_id
                ),
            )
    except Exception as e:
        logger.error(f"خطأ في مزامنة خلفية: {e}")
        try:
            await bot.send_message(
                chat_id=admin_chat_id,
                text=(
                    f"❌ فشل المزامنة:\n"
                    f"<code>{str(e)[:200]}</code>"
                ),
            )
        except Exception:
            pass


# ══════════════════════════════════════════════
# ══════════════ عرض خدمات المزود ══════════════
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:aprov_services:"))
async def aprov_services_list(
    callback: CallbackQuery, session, state: FSMContext
):
    parts = callback.data.split(":")
    provider_id = int(parts[2])
    page = int(parts[3]) if len(parts) > 3 else 0

    provider = await session.get(ApiProvider, provider_id)
    if not provider:
        await callback.answer(
            "⚠️ غير موجود", show_alert=True
        )
        return

    await state.clear()

    total_count = (
        await ProviderSyncService.get_provider_services_count(
            provider_id, active_only=True
        )
    )

    if total_count == 0:
        await callback.message.edit_text(
            f"📦 <b>خدمات {provider.name}</b>\n\n"
            "⚠️ لا توجد خدمات مسحوبة.\n"
            "اضغط 'مزامنة الخدمات' لسحبها.",
            reply_markup=sync_in_progress_kb(provider_id),
        )
        return

    services = await (
        ProviderSyncService.get_provider_services(
            provider_id=provider_id,
            limit=SERVICES_PER_PAGE,
            offset=page * SERVICES_PER_PAGE,
            active_only=True,
        )
    )

    total_pages = max(
        1,
        (total_count + SERVICES_PER_PAGE - 1)
        // SERVICES_PER_PAGE,
    )

    text = (
        f"📦 <b>خدمات {provider.name}</b>\n\n"
        f"📊 المجموع: <b>{total_count}</b> خدمة\n"
        f"📄 الصفحة: <b>{page + 1}/{total_pages}</b>\n\n"
        "اضغط على أي خدمة لعرض التفاصيل:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=provider_services_kb(
            provider_id=provider_id,
            services=services,
            current_page=page,
            total_count=total_count,
        ),
    )
    await callback.answer()


# ══════════════════════════════════════════════
# ══════════════ البحث في الخدمات ══════════════
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:aprov_search:"))
async def aprov_search_start(
    callback: CallbackQuery, state: FSMContext
):
    provider_id = int(callback.data.split(":")[2])
    await state.update_data(search_provider_id=provider_id)

    await callback.message.edit_text(
        "🔍 <b>البحث في خدمات المزود</b>\n\n"
        "أرسل كلمة أو جملة للبحث:\n"
        "(البحث في: الاسم، التصنيف، الآيدي)",
        reply_markup=cancel_search_kb(provider_id),
    )
    await state.set_state(
        AdminProviderServicesStates.waiting_search_query
    )
    await callback.answer()


@router.message(
    AdminProviderServicesStates.waiting_search_query
)
async def aprov_search_query_received(
    message: Message, state: FSMContext, session
):
    query = message.text.strip()

    if len(query) < 1:
        await message.answer("⚠️ أرسل كلمة بحث صالحة.")
        return

    data = await state.get_data()
    provider_id = data.get("search_provider_id")

    if not provider_id:
        await message.answer("⚠️ جلسة منتهية.")
        await state.clear()
        return

    provider = await session.get(ApiProvider, provider_id)
    if not provider:
        await message.answer("⚠️ المزود غير موجود.")
        await state.clear()
        return

    await state.update_data(search_query=query)

    services = await (
        ProviderSyncService.get_provider_services(
            provider_id=provider_id,
            limit=SERVICES_PER_PAGE,
            offset=0,
            active_only=True,
            search=query,
        )
    )

    if not services:
        await message.answer(
            f"🔍 <b>البحث عن:</b> {query}\n\n"
            "❌ لا توجد نتائج.",
            reply_markup=cancel_search_kb(provider_id),
        )
        return

    total_search = len(services)

    text = (
        f"🔍 <b>نتائج البحث</b>\n\n"
        f"🔎 الكلمة: <code>{query}</code>\n"
        f"📊 النتائج: <b>{total_search}+</b>\n\n"
        "اضغط على أي خدمة للتفاصيل:"
    )

    await message.answer(
        text,
        reply_markup=provider_services_kb(
            provider_id=provider_id,
            services=services,
            current_page=0,
            total_count=total_search,
            search_query=query,
        ),
    )
    await state.set_state(None)


# ══════════════════════════════════════════════
# ══════════════ تفاصيل خدمة ══════════════
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:aprov_svc:"))
async def aprov_service_view(
    callback: CallbackQuery, session
):
    service_id = int(callback.data.split(":")[2])
    service = await session.get(ProviderService, service_id)

    if not service:
        await callback.answer(
            "⚠️ الخدمة غير موجودة.", show_alert=True
        )
        return

    provider = await session.get(
        ApiProvider, service.api_provider_id
    )
    if not provider:
        await callback.answer(
            "⚠️ المزود غير موجود.", show_alert=True
        )
        return

    from sqlalchemy import select, func
    from database.models import Product

    products_count_result = await session.execute(
        select(func.count(Product.id)).where(
            Product.provider_service_ref_id == service.id
        )
    )
    products_count = products_count_result.scalar_one()

    text = (
        f"📦 <b>تفاصيل الخدمة</b>\n\n"
        f"🔌 المزود: {provider.name}\n"
        f"🆔 الآيدي: <code>{service.external_service_id}</code>\n"
        f"📝 الاسم: <b>{service.name}</b>\n"
    )

    if service.category:
        text += f"📁 التصنيف: {service.category}\n"
    if service.service_type:
        text += f"🏷 النوع: {service.service_type}\n"

    text += (
        f"\n💰 <b>السعر عند المزود:</b>\n"
        f"• {service.rate} {provider.currency} / 1000\n"
        f"• {service.rate_usd}$ / 1000\n\n"
        f"📊 <b>الكمية:</b>\n"
        f"• الحد الأدنى: {service.min_quantity:,}\n"
        f"• الحد الأقصى: {service.max_quantity:,}\n\n"
        f"⚙️ <b>المتطلبات:</b>\n"
    )
    if service.requires_link:
        text += "• ✅ رابط\n"
    if service.requires_player_id:
        text += "• ✅ Player ID\n"
    if service.requires_quantity:
        text += "• ✅ الكمية\n"

    text += (
        f"\n🔧 <b>الميزات:</b>\n"
        f"• Refill: "
        f"{'✅' if service.supports_refill else '❌'}\n"
        f"• Cancel: "
        f"{'✅' if service.supports_cancel else '❌'}\n\n"
        f"📦 المنتجات المرتبطة: <b>{products_count}</b>"
    )

    if service.description:
        desc = service.description[:200]
        text += f"\n\n📄 <b>الوصف:</b>\n<i>{desc}</i>"

    await callback.message.edit_text(
        text,
        reply_markup=provider_service_detail_kb(service),
    )
    await callback.answer()


# ══════════════════════════════════════════════
# ══════════════ تعديل بيانات المزود ══════════════
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:aprov_edit_name:"))
async def aprov_edit_name_start(
    callback: CallbackQuery, state: FSMContext
):
    provider_id = int(callback.data.split(":")[2])
    await state.update_data(
        edit_provider_id=provider_id,
        edit_field="name",
    )
    await callback.message.edit_text(
        "📝 أرسل الاسم الجديد للمزود:",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(
        AdminApiProviderStates.waiting_edit_value
    )


@router.callback_query(F.data.startswith("admin:aprov_edit_key:"))
async def aprov_edit_key_start(
    callback: CallbackQuery, state: FSMContext
):
    provider_id = int(callback.data.split(":")[2])
    await state.update_data(
        edit_provider_id=provider_id,
        edit_field="api_key",
    )
    await callback.message.edit_text(
        "🔑 أرسل مفتاح API الجديد:",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(
        AdminApiProviderStates.waiting_edit_value
    )


@router.callback_query(F.data.startswith("admin:aprov_edit_url:"))
async def aprov_edit_url_start(
    callback: CallbackQuery, state: FSMContext
):
    provider_id = int(callback.data.split(":")[2])
    await state.update_data(
        edit_provider_id=provider_id,
        edit_field="api_url",
    )
    await callback.message.edit_text(
        "🔗 أرسل رابط API الجديد:",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(
        AdminApiProviderStates.waiting_edit_value
    )


@router.callback_query(F.data.startswith("admin:aprov_edit_rate:"))
async def aprov_edit_rate_start(
    callback: CallbackQuery, state: FSMContext
):
    provider_id = int(callback.data.split(":")[2])
    await state.update_data(
        edit_provider_id=provider_id,
        edit_field="rate_to_usd",
    )
    await callback.message.edit_text(
        "💱 أرسل سعر الصرف الجديد (1 عملة = X دولار):\n"
        "(مثال: <code>0.011</code> للروبل)",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(
        AdminApiProviderStates.waiting_edit_value
    )


@router.message(AdminApiProviderStates.waiting_edit_value)
async def aprov_edit_value_received(
    message: Message, state: FSMContext, session
):
    data = await state.get_data()
    provider_id = data.get("edit_provider_id")
    field = data.get("edit_field")

    if not provider_id or not field:
        await message.answer("⚠️ جلسة منتهية.")
        await state.clear()
        return

    provider = await session.get(ApiProvider, provider_id)
    if not provider:
        await message.answer("⚠️ المزود غير موجود.")
        await state.clear()
        return

    value = message.text.strip()

    if field == "name":
        if len(value) < 2 or len(value) > 64:
            await message.answer(
                "⚠️ الاسم يجب أن يكون بين 2 و 64 حرف."
            )
            return
        provider.name = value

    elif field == "api_key":
        if len(value) < 5:
            await message.answer(
                "⚠️ المفتاح قصير جداً."
            )
            return
        provider.api_key = value
        try:
            await message.delete()
        except Exception:
            pass

    elif field == "api_url":
        if not value.startswith(("http://", "https://")):
            await message.answer(
                "⚠️ يجب أن يبدأ بـ http:// أو https://"
            )
            return
        provider.api_url = value

    elif field == "rate_to_usd":
        try:
            rate = Decimal(value)
            if rate <= 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            await message.answer(
                "⚠️ أرسل رقماً صحيحاً أكبر من صفر."
            )
            return
        provider.rate_to_usd = rate

    await session.commit()
    await message.answer(f"✅ تم تحديث {field} بنجاح.")
    await state.clear()

    await session.refresh(provider)
    await _show_provider_details(
        message, provider, edit=False
    )


# ══════════════════════════════════════════════
# ══════════════ حذف المزود ══════════════
# ══════════════════════════════════════════════

@router.callback_query(
    F.data.startswith("admin:aprov_delete_confirm:")
)
async def aprov_delete_confirm(
    callback: CallbackQuery, session
):
    provider_id = int(callback.data.split(":")[2])
    provider = await session.get(ApiProvider, provider_id)

    if not provider:
        await callback.answer(
            "⚠️ غير موجود", show_alert=True
        )
        return

    services_count = (
        await ProviderSyncService.get_provider_services_count(
            provider_id, active_only=False
        )
    )

    from sqlalchemy import select, func
    from database.models import Product
    products_result = await session.execute(
        select(func.count(Product.id)).where(
            Product.api_provider_id == provider_id
        )
    )
    products_count = products_result.scalar_one()

    text = (
        f"⚠️ <b>تأكيد حذف المزود</b>\n\n"
        f"سيتم حذف:\n"
        f"• المزود: <b>{provider.name}</b>\n"
        f"• {services_count} خدمة مسحوبة\n"
    )
    if products_count > 0:
        text += (
            f"\n⚠️ يوجد <b>{products_count}</b> منتج "
            f"مرتبط بهذا المزود!\n"
            f"سيتم فك ارتباطها (لن تُحذف).\n"
        )
    text += "\n<b>هل أنت متأكد؟</b>"

    await callback.message.edit_text(
        text,
        reply_markup=confirm_delete_provider_kb(provider_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:aprov_delete:"))
async def aprov_delete(
    callback: CallbackQuery, session
):
    provider_id = int(callback.data.split(":")[2])
    provider = await session.get(ApiProvider, provider_id)

    if not provider:
        await callback.answer(
            "⚠️ غير موجود", show_alert=True
        )
        return

    provider_name = provider.name

    from sqlalchemy import update
    from database.models import Product
    await session.execute(
        update(Product)
        .where(Product.api_provider_id == provider_id)
        .values(
            api_provider_id=None,
            provider_service_ref_id=None,
        )
    )

    await session.delete(provider)
    await session.commit()

    await callback.answer(
        f"🗑 تم حذف المزود: {provider_name}"
    )

    logger.info(
        f"تم حذف المزود: #{provider_id} - {provider_name}"
    )

    await providers_list(callback, session)


# ══════════════════════════════════════════════
# ══════════════ noop (زر بدون فعل) ══════════════
# ══════════════════════════════════════════════

@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    await callback.answer()
```

### `handlers/admin/broadcast.py`

```python
"""
الإذاعة الجماعية.
"""
import asyncio

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from database.models import User, BroadcastLog
from states.states import AdminBroadcastStates
from keyboards.admin import admin_back_kb
from filters.admin_filter import IsAdmin

router = Router(name="admin_broadcast")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "admin:broadcast")
async def broadcast_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.message.edit_text(
        "📢 <b>إذاعة جماعية</b>\n\n"
        "أرسل الرسالة (نص أو صورة مع كابشن) "
        "التي تريد إذاعتها لكل المستخدمين:\n\n"
        "⚠️ سيتم إرسالها لكل المستخدمين غير المحظورين.",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(AdminBroadcastStates.waiting_content)


@router.message(AdminBroadcastStates.waiting_content)
async def broadcast_content_received(
    message: Message,
    state: FSMContext,
    session,
    db_user: User,
    bot,
):
    result = await session.execute(
        select(User).where(User.is_banned == False)
    )
    users = result.scalars().all()

    progress_msg = await message.answer(
        f"📢 جاري الإرسال لـ {len(users)} مستخدم...\n"
        "⏳ يرجى الانتظار."
    )

    sent, failed = 0, 0
    for user in users:
        try:
            if message.photo:
                await bot.send_photo(
                    user.telegram_id,
                    message.photo[-1].file_id,
                    caption=message.caption,
                )
            elif message.video:
                await bot.send_video(
                    user.telegram_id,
                    message.video.file_id,
                    caption=message.caption,
                )
            elif message.document:
                await bot.send_document(
                    user.telegram_id,
                    message.document.file_id,
                    caption=message.caption,
                )
            else:
                await bot.send_message(
                    user.telegram_id,
                    message.text or message.caption or "",
                )
            sent += 1
        except Exception:
            failed += 1

        if (sent + failed) % 30 == 0:
            await asyncio.sleep(1)

    session.add(BroadcastLog(
        admin_id=db_user.id,
        total_sent=sent,
        total_failed=failed,
    ))
    await session.commit()

    try:
        await progress_msg.edit_text(
            f"✅ تم الإرسال.\n\n"
            f"📤 نجح: {sent}\n"
            f"❌ فشل: {failed}\n"
            f"📊 الإجمالي: {len(users)}"
        )
    except Exception:
        await message.answer(
            f"✅ تم الإرسال.\n"
            f"📤 نجح: {sent} | ❌ فشل: {failed}"
        )

    await state.clear()
```

### `handlers/admin/categories.py`

```python
"""
إدارة الأقسام الرئيسية والفرعية.

يشمل:
- عرض قائمة الأقسام
- Wizard إضافة قسم رئيسي (نوع → اسم → إيموجي)
- Wizard إضافة قسم فرعي (اسم → إيموجي → صورة)
- تفعيل/تعطيل
- تعديل الحقول (اسم، إيموجي، وصف، صورة، ترتيب)
- حذف مع تأكيد
- تسجيل Audit Log
"""
import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.models import (
    Category,
    SubCategory,
    CategoryType,
    AuditAction,
)
from services.audit_service import AuditService
from services.dynamic_service import DynamicService
from states.states import (
    AdminCategoryStates,
    AdminSubCategoryStates,
)
from keyboards.admin_categories_v2 import (
    categories_list_kb,
    select_category_type_kb,
    select_emoji_kb,
    category_detail_kb,
    confirm_delete_category_kb,
    sub_categories_list_kb,
    sub_category_detail_kb,
    confirm_delete_sub_category_kb,
    image_options_kb,
    cancel_add_kb,
)
from keyboards.admin import admin_back_kb
from filters.admin_filter import IsAdmin

logger = logging.getLogger(__name__)

router = Router(name="admin_categories")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# ══════════════════════════════════════════════
# ══════════════ قائمة الأقسام ══════════════
# ══════════════════════════════════════════════

@router.callback_query(F.data == "admin:categories")
async def categories_list(callback: CallbackQuery, session):
    """يعرض قائمة كل الأقسام الرئيسية."""
    categories = await DynamicService.get_all_categories(session)

    if not categories:
        text = (
            "📂 <b>إدارة الأقسام</b>\n\n"
            "لا توجد أقسام مسجلة حتى الآن.\n"
            "اضغط الزر أدناه لإضافة قسم جديد."
        )
    else:
        text = (
            "📂 <b>إدارة الأقسام</b>\n\n"
            f"عدد الأقسام: <b>{len(categories)}</b>\n\n"
            "🟢 = مفعّل | 🔴 = معطّل\n"
            "الرقم بين قوسين = عدد الأقسام الفرعية\n\n"
            "اضغط على أي قسم لعرض التفاصيل."
        )

    await callback.message.edit_text(
        text,
        reply_markup=categories_list_kb(categories),
    )


# ══════════════════════════════════════════════
# ══════════════ إضافة قسم رئيسي - الخطوة 1 ══════════════
# ══════════════════════════════════════════════

@router.callback_query(F.data == "admin:cat_add")
async def cat_add_start(
    callback: CallbackQuery, state: FSMContext
):
    """يبدأ Wizard إضافة قسم رئيسي."""
    await state.clear()
    await callback.message.edit_text(
        "📂 <b>إضافة قسم رئيسي جديد</b>\n\n"
        "الخطوة 1️⃣ من 3️⃣\n\n"
        "اختر نوع القسم:\n\n"
        "📈 <b>رشق سوشيال</b>: منتجات رشق للمنصات "
        "(متابعين، لايكات، مشاهدات)\n\n"
        "🎮 <b>شحن ألعاب</b>: منتجات شحن الألعاب "
        "(UC ببجي، جواهر فري فاير، إلخ)\n\n"
        "📱 <b>تطبيقات دردشة</b>: منتجات تطبيقات مثل "
        "بيجو لايف، لايكي، تيك توك",
        reply_markup=select_category_type_kb(),
    )
    await state.set_state(AdminCategoryStates.waiting_type)


@router.callback_query(F.data.startswith("admin:cat_type:"))
async def cat_type_selected(
    callback: CallbackQuery, state: FSMContext
):
    """اختيار نوع القسم."""
    type_key = callback.data.split(":")[2]

    try:
        cat_type = CategoryType(type_key)
    except ValueError:
        await callback.answer(
            "❌ نوع غير صالح", show_alert=True
        )
        return

    await state.update_data(category_type=cat_type.value)
    await callback.answer()

    type_names = {
        "smm": "📈 رشق سوشيال ميديا",
        "games": "🎮 شحن ألعاب",
        "apps": "📱 تطبيقات دردشة",
    }
    type_display = type_names.get(
        cat_type.value, cat_type.value
    )

    await callback.message.edit_text(
        f"✅ النوع: <b>{type_display}</b>\n\n"
        "الخطوة 2️⃣ من 3️⃣\n\n"
        "📝 أرسل اسم القسم بالعربية:\n"
        "(مثال: <code>رشق سوشيال ميديا</code> أو "
        "<code>شحن ألعاب</code>)",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(AdminCategoryStates.waiting_name)


@router.message(AdminCategoryStates.waiting_name)
async def cat_name_received(
    message: Message, state: FSMContext
):
    """استقبال اسم القسم."""
    name = message.text.strip()

    if len(name) < 2:
        await message.answer("⚠️ الاسم قصير جداً.")
        return

    if len(name) > 64:
        await message.answer(
            "⚠️ الاسم طويل جداً (الحد الأقصى 64 حرف)."
        )
        return

    await state.update_data(name=name)

    data = await state.get_data()
    cat_type = data.get("category_type", "smm")

    await message.answer(
        f"✅ الاسم: <b>{name}</b>\n\n"
        "الخطوة 3️⃣ من 3️⃣\n\n"
        "🎨 اختر إيموجي للقسم:",
        reply_markup=select_emoji_kb(cat_type),
    )
    await state.set_state(
        AdminCategoryStates.waiting_emoji
    )


@router.callback_query(
    AdminCategoryStates.waiting_emoji,
    F.data.startswith("admin:cat_emoji:"),
)
async def cat_emoji_selected(
    callback: CallbackQuery,
    state: FSMContext,
    session,
    db_user,
):
    """استقبال الإيموجي وإنشاء القسم."""
    emoji_choice = callback.data.split(":", 2)[2]
    data = await state.get_data()

    if emoji_choice == "custom":
        await callback.message.edit_text(
            "✏️ أرسل إيموجي مخصص:\n"
            "(إيموجي واحد فقط)"
        )
        return

    if emoji_choice == "default":
        emoji_defaults = {
            "smm": "📈",
            "games": "🎮",
            "apps": "📱",
        }
        emoji = emoji_defaults.get(
            data.get("category_type", "smm"), "📦"
        )
    else:
        emoji = emoji_choice

    try:
        category = await DynamicService.create_category(
            session=session,
            name_ar=data["name"],
            emoji=emoji,
            category_type=CategoryType(
                data["category_type"]
            ),
        )
    except Exception as e:
        logger.error(f"فشل إنشاء قسم: {e}")
        await callback.answer(
            f"❌ فشل الإنشاء: {e}", show_alert=True
        )
        await state.clear()
        return

    await AuditService.log_create(
        admin_id=db_user.id,
        entity_type="category",
        entity_id=category.id,
        entity_name=category.name_ar,
        new_value={
            "name": category.name_ar,
            "emoji": category.emoji,
            "type": category.type.value,
        },
        session=session,
    )

    await callback.answer("✅ تم إنشاء القسم بنجاح")
    await callback.message.edit_text(
        f"✅ <b>تم إنشاء القسم بنجاح!</b>\n\n"
        f"{emoji} <b>{category.name_ar}</b>\n\n"
        "يمكنك الآن إضافة أقسام فرعية له."
    )
    await state.clear()

    await categories_list(callback, session)


@router.message(AdminCategoryStates.waiting_emoji)
async def cat_custom_emoji_received(
    message: Message,
    state: FSMContext,
    session,
    db_user,
):
    """استقبال إيموجي مخصص."""
    emoji = message.text.strip()

    if len(emoji) > 8:
        await message.answer(
            "⚠️ إيموجي واحد فقط من فضلك."
        )
        return

    data = await state.get_data()

    try:
        category = await DynamicService.create_category(
            session=session,
            name_ar=data["name"],
            emoji=emoji,
            category_type=CategoryType(
                data["category_type"]
            ),
        )
    except Exception as e:
        logger.error(f"فشل إنشاء قسم: {e}")
        await message.answer(f"❌ فشل الإنشاء: {e}")
        await state.clear()
        return

    await AuditService.log_create(
        admin_id=db_user.id,
        entity_type="category",
        entity_id=category.id,
        entity_name=category.name_ar,
        new_value={
            "name": category.name_ar,
            "emoji": category.emoji,
            "type": category.type.value,
        },
        session=session,
    )

    await message.answer(
        f"✅ <b>تم إنشاء القسم بنجاح!</b>\n\n"
        f"{emoji} <b>{category.name_ar}</b>"
    )
    await state.clear()


# ══════════════════════════════════════════════
# ══════════════ تفاصيل القسم ══════════════
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:cat_view:"))
async def cat_view(callback: CallbackQuery, session):
    """يعرض تفاصيل قسم رئيسي."""
    cat_id = int(callback.data.split(":")[2])
    category = await DynamicService.get_category(
        session, cat_id
    )

    if not category:
        await callback.answer(
            "⚠️ القسم غير موجود", show_alert=True
        )
        return

    await _show_category_details(
        callback.message, category, edit=True
    )


async def _show_category_details(
    message,
    category: Category,
    edit: bool = True,
):
    """يعرض تفاصيل قسم."""
    status = (
        "🟢 مفعّل" if category.is_active else "🔴 معطّل"
    )
    type_labels = {
        "smm": "📈 رشق سوشيال",
        "games": "🎮 شحن ألعاب",
        "apps": "📱 تطبيقات",
        "numbers": "📞 أرقام",
    }
    type_label = type_labels.get(
        category.type.value, category.type.value
    )

    subs_count = (
        len(category.sub_categories)
        if category.sub_categories
        else 0
    )

    active_subs = 0
    if category.sub_categories:
        active_subs = sum(
            1 for s in category.sub_categories
            if s.is_active
        )

    text = (
        f"{category.emoji} <b>{category.name_ar}</b>\n\n"
        f"📁 النوع: {type_label}\n"
        f"📊 الحالة: {status}\n"
        f"🔢 الترتيب: {category.sort_order}\n\n"
        f"📂 عدد الأقسام الفرعية: <b>{subs_count}</b>\n"
        f"🟢 نشطة منها: <b>{active_subs}</b>\n\n"
        f"📅 تاريخ الإنشاء: "
        f"{category.created_at.strftime('%Y-%m-%d')}"
    )

    kb = category_detail_kb(category)

    if edit:
        try:
            await message.edit_text(text, reply_markup=kb)
        except Exception:
            await message.answer(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


# ══════════════════════════════════════════════
# ══════════════ تفعيل / تعطيل ══════════════
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:cat_toggle:"))
async def cat_toggle(
    callback: CallbackQuery, session, db_user
):
    """يبدل حالة قسم رئيسي."""
    cat_id = int(callback.data.split(":")[2])
    category = await session.get(Category, cat_id)

    if not category:
        await callback.answer(
            "⚠️ غير موجود", show_alert=True
        )
        return

    category.is_active = not category.is_active
    await session.commit()

    await AuditService.log_toggle(
        admin_id=db_user.id,
        entity_type="category",
        entity_id=category.id,
        entity_name=category.name_ar,
        new_status=category.is_active,
        session=session,
    )

    status_text = (
        "✅ تم تفعيل"
        if category.is_active
        else "❌ تم تعطيل"
    )
    await callback.answer(f"{status_text} القسم")

    await session.refresh(category)
    await _show_category_details(
        callback.message, category, edit=True
    )


# ══════════════════════════════════════════════
# ══════════════ تعديل القسم ══════════════
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:cat_edit:"))
async def cat_edit_start(
    callback: CallbackQuery, state: FSMContext
):
    """يبدأ تعديل حقل في القسم."""
    parts = callback.data.split(":")
    field = parts[2]
    cat_id = int(parts[3])

    await state.update_data(
        edit_category_id=cat_id,
        edit_field=field,
    )

    field_prompts = {
        "name": "📝 أرسل الاسم الجديد للقسم:",
        "emoji": "🎨 أرسل الإيموجي الجديد:",
        "sort": (
            "🔢 أرسل رقم الترتيب الجديد "
            "(الأصغر يظهر أولاً):"
        ),
    }

    prompt = field_prompts.get(
        field, "أرسل القيمة الجديدة:"
    )

    await callback.message.edit_text(
        prompt,
        reply_markup=cancel_add_kb(
            f"admin:cat_view:{cat_id}"
        ),
    )
    await state.set_state(
        AdminCategoryStates.waiting_edit_value
    )


@router.message(AdminCategoryStates.waiting_edit_value)
async def cat_edit_value_received(
    message: Message,
    state: FSMContext,
    session,
    db_user,
):
    """يستقبل القيمة الجديدة ويحدث القسم."""
    data = await state.get_data()
    cat_id = data.get("edit_category_id")
    field = data.get("edit_field")

    if not cat_id or not field:
        await message.answer("⚠️ جلسة منتهية.")
        await state.clear()
        return

    category = await session.get(Category, cat_id)
    if not category:
        await message.answer("⚠️ القسم غير موجود.")
        await state.clear()
        return

    value = message.text.strip()
    old_value = None

    if field == "name":
        if len(value) < 2 or len(value) > 64:
            await message.answer(
                "⚠️ الاسم يجب أن يكون بين 2 و 64 حرف."
            )
            return
        old_value = category.name_ar
        category.name_ar = value

    elif field == "emoji":
        if len(value) > 8:
            await message.answer(
                "⚠️ إيموجي واحد فقط."
            )
            return
        old_value = category.emoji
        category.emoji = value

    elif field == "sort":
        try:
            sort_val = int(value)
        except ValueError:
            await message.answer("⚠️ أرسل رقماً صحيحاً.")
            return
        old_value = category.sort_order
        category.sort_order = sort_val

    await session.commit()

    await AuditService.log_update(
        admin_id=db_user.id,
        entity_type="category",
        entity_id=category.id,
        entity_name=category.name_ar,
        field=field,
        old_value=old_value,
        new_value=value,
        session=session,
    )

    await message.answer(f"✅ تم تحديث {field}.")
    await state.clear()

    await session.refresh(category)
    await _show_category_details(
        message, category, edit=False
    )


# ══════════════════════════════════════════════
# ══════════════ حذف قسم رئيسي ══════════════
# ══════════════════════════════════════════════

@router.callback_query(
    F.data.startswith("admin:cat_delete_confirm:")
)
async def cat_delete_confirm(
    callback: CallbackQuery, session
):
    """تأكيد حذف قسم رئيسي."""
    cat_id = int(callback.data.split(":")[2])
    category = await DynamicService.get_category(
        session, cat_id
    )

    if not category:
        await callback.answer(
            "⚠️ غير موجود", show_alert=True
        )
        return

    subs_count = (
        len(category.sub_categories)
        if category.sub_categories
        else 0
    )

    text = (
        f"⚠️ <b>تأكيد حذف القسم</b>\n\n"
        f"سيتم حذف:\n"
        f"• القسم: {category.emoji} {category.name_ar}\n"
    )
    if subs_count > 0:
        text += (
            f"• <b>{subs_count}</b> قسم فرعي\n"
            f"• كل المنتجات داخل الأقسام الفرعية\n"
        )
    text += "\n<b>هل أنت متأكد؟ هذا الإجراء لا يمكن التراجع عنه!</b>"

    await callback.message.edit_text(
        text,
        reply_markup=confirm_delete_category_kb(
            category.id, subs_count
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:cat_delete:"))
async def cat_delete(
    callback: CallbackQuery, session, db_user
):
    """يحذف قسم رئيسي."""
    cat_id = int(callback.data.split(":")[2])
    category = await session.get(Category, cat_id)

    if not category:
        await callback.answer(
            "⚠️ غير موجود", show_alert=True
        )
        return

    cat_name = category.name_ar

    await AuditService.log_delete(
        admin_id=db_user.id,
        entity_type="category",
        entity_id=category.id,
        entity_name=cat_name,
        session=session,
    )

    await session.delete(category)
    await session.commit()

    await callback.answer(f"🗑 تم حذف: {cat_name}")
    logger.info(
        f"الأدمن {db_user.telegram_id} حذف "
        f"القسم #{cat_id} - {cat_name}"
    )

    await categories_list(callback, session)
    # ══════════════════════════════════════════════
# ══════════════ الأقسام الفرعية ══════════════
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:subcat_list:"))
async def subcat_list(callback: CallbackQuery, session):
    """يعرض قائمة الأقسام الفرعية لقسم رئيسي."""
    cat_id = int(callback.data.split(":")[2])
    category = await DynamicService.get_category(
        session, cat_id
    )

    if not category:
        await callback.answer(
            "⚠️ غير موجود", show_alert=True
        )
        return

    subs = await DynamicService.get_all_sub_categories(
        session, cat_id
    )

    if not subs:
        text = (
            f"📂 <b>{category.emoji} "
            f"{category.name_ar}</b>\n\n"
            "لا توجد أقسام فرعية.\n"
            "اضغط الزر أدناه لإضافة قسم فرعي."
        )
    else:
        text = (
            f"📂 <b>{category.emoji} "
            f"{category.name_ar}</b>\n\n"
            f"عدد الأقسام الفرعية: <b>{len(subs)}</b>\n\n"
            "🟢 = مفعّل | 🔴 = معطّل\n"
            "الرقم بين قوسين = عدد المنتجات"
        )

    await callback.message.edit_text(
        text,
        reply_markup=sub_categories_list_kb(cat_id, subs),
    )


# ══════════════ إضافة قسم فرعي ══════════════

@router.callback_query(F.data.startswith("admin:subcat_add:"))
async def subcat_add_start(
    callback: CallbackQuery, state: FSMContext
):
    """يبدأ Wizard إضافة قسم فرعي."""
    cat_id = int(callback.data.split(":")[2])
    await state.update_data(parent_category_id=cat_id)

    await callback.message.edit_text(
        "📂 <b>إضافة قسم فرعي جديد</b>\n\n"
        "الخطوة 1️⃣ من 4️⃣\n\n"
        "📝 أرسل اسم القسم الفرعي:\n"
        "(مثال: <code>إنستقرام</code> أو "
        "<code>ببجي موبايل</code>)",
        reply_markup=cancel_add_kb(
            f"admin:subcat_list:{cat_id}"
        ),
    )
    await state.set_state(
        AdminSubCategoryStates.waiting_name
    )


@router.message(AdminSubCategoryStates.waiting_name)
async def subcat_name_received(
    message: Message, state: FSMContext
):
    """استقبال اسم القسم الفرعي."""
    name = message.text.strip()

    if len(name) < 2:
        await message.answer("⚠️ الاسم قصير جداً.")
        return

    if len(name) > 64:
        await message.answer(
            "⚠️ الاسم طويل جداً (الحد الأقصى 64)."
        )
        return

    await state.update_data(name=name)

    data = await state.get_data()
    cat_id = data.get("parent_category_id")

    await message.answer(
        f"✅ الاسم: <b>{name}</b>\n\n"
        "الخطوة 2️⃣ من 4️⃣\n\n"
        "🎨 اختر إيموجي للقسم الفرعي:",
        reply_markup=select_emoji_kb("smm"),
    )
    await state.set_state(
        AdminSubCategoryStates.waiting_emoji
    )


@router.callback_query(
    AdminSubCategoryStates.waiting_emoji,
    F.data.startswith("admin:cat_emoji:"),
)
async def subcat_emoji_selected(
    callback: CallbackQuery, state: FSMContext
):
    """استقبال الإيموجي."""
    emoji_choice = callback.data.split(":", 2)[2]

    if emoji_choice == "custom":
        await callback.message.edit_text(
            "✏️ أرسل إيموجي مخصص:"
        )
        return

    if emoji_choice == "default":
        emoji = "📱"
    else:
        emoji = emoji_choice

    await state.update_data(emoji=emoji)

    await callback.message.edit_text(
        f"✅ الإيموجي: {emoji}\n\n"
        "الخطوة 3️⃣ من 4️⃣\n\n"
        "📝 أرسل وصف القسم (اختياري):\n"
        "أو اضغط ⏭ للتخطي",
        reply_markup=cancel_add_kb(
            "admin:categories"
        ),
    )
    await state.set_state(
        AdminSubCategoryStates.waiting_description
    )


@router.message(AdminSubCategoryStates.waiting_emoji)
async def subcat_custom_emoji_received(
    message: Message, state: FSMContext
):
    """استقبال إيموجي مخصص."""
    emoji = message.text.strip()

    if len(emoji) > 8:
        await message.answer("⚠️ إيموجي واحد فقط.")
        return

    await state.update_data(emoji=emoji)

    await message.answer(
        f"✅ الإيموجي: {emoji}\n\n"
        "الخطوة 3️⃣ من 4️⃣\n\n"
        "📝 أرسل وصف القسم (اختياري):\n"
        "أرسل نصاً أو - للتخطي"
    )
    await state.set_state(
        AdminSubCategoryStates.waiting_description
    )


@router.message(AdminSubCategoryStates.waiting_description)
async def subcat_description_received(
    message: Message, state: FSMContext
):
    """استقبال الوصف."""
    desc = message.text.strip()
    if desc == "-" or desc == "تخطي":
        desc = None
    elif len(desc) > 255:
        await message.answer("⚠️ الوصف طويل جداً (255).")
        return

    await state.update_data(description=desc)

    data = await state.get_data()
    cat_id = data.get("parent_category_id")

    await message.answer(
        "الخطوة 4️⃣ من 4️⃣\n\n"
        "🖼 هل تريد إضافة صورة للقسم؟",
        reply_markup=image_options_kb(
            context="subcat_wizard",
            entity_id=cat_id,
        ),
    )
    await state.set_state(
        AdminSubCategoryStates.waiting_image
    )


@router.callback_query(
    AdminSubCategoryStates.waiting_image,
    F.data.startswith("admin:subcat_wizard_img:"),
)
async def subcat_image_option(
    callback: CallbackQuery,
    state: FSMContext,
    session,
    db_user,
):
    """اختيار خيار الصورة."""
    parts = callback.data.split(":")
    option = parts[2]

    if option == "skip":
        await _create_sub_category(
            callback.message, state, session, db_user
        )
        return

    if option == "upload":
        await callback.message.edit_text(
            "📤 أرسل الصورة الآن:"
        )
        return

    if option == "url":
        await callback.message.edit_text(
            "🔗 أرسل رابط الصورة:"
        )
        return


@router.message(
    AdminSubCategoryStates.waiting_image,
    F.photo,
)
async def subcat_image_uploaded(
    message: Message,
    state: FSMContext,
    session,
    db_user,
):
    """استقبال صورة مرفوعة."""
    file_id = message.photo[-1].file_id
    await state.update_data(image_file_id=file_id)
    await _create_sub_category(
        message, state, session, db_user
    )


@router.message(AdminSubCategoryStates.waiting_image)
async def subcat_image_url_received(
    message: Message,
    state: FSMContext,
    session,
    db_user,
):
    """استقبال رابط صورة."""
    url = message.text.strip()

    if url.lower() in ("-", "تخطي", "skip"):
        await _create_sub_category(
            message, state, session, db_user
        )
        return

    if not url.startswith(("http://", "https://")):
        await message.answer(
            "⚠️ أرسل رابط صورة صحيح أو - للتخطي."
        )
        return

    if len(url) > 500:
        await message.answer("⚠️ الرابط طويل جداً.")
        return

    await state.update_data(image_url=url)
    await _create_sub_category(
        message, state, session, db_user
    )


async def _create_sub_category(
    message,
    state: FSMContext,
    session,
    db_user,
):
    """ينشئ القسم الفرعي في قاعدة البيانات."""
    data = await state.get_data()

    try:
        sub_category = SubCategory(
            category_id=data["parent_category_id"],
            name_ar=data["name"],
            emoji=data.get("emoji", "📱"),
            description=data.get("description"),
            image_file_id=data.get("image_file_id"),
            image_url=data.get("image_url"),
            is_active=True,
        )
        session.add(sub_category)
        await session.commit()
        await session.refresh(sub_category)
    except Exception as e:
        logger.error(f"فشل إنشاء قسم فرعي: {e}")
        if hasattr(message, "answer"):
            await message.answer(f"❌ فشل الإنشاء: {e}")
        await state.clear()
        return

    await AuditService.log_create(
        admin_id=db_user.id,
        entity_type="sub_category",
        entity_id=sub_category.id,
        entity_name=sub_category.name_ar,
        new_value={
            "name": sub_category.name_ar,
            "emoji": sub_category.emoji,
        },
        session=session,
    )

    success_text = (
        f"✅ <b>تم إنشاء القسم الفرعي بنجاح!</b>\n\n"
        f"{sub_category.emoji} <b>{sub_category.name_ar}</b>\n\n"
        "يمكنك الآن إضافة منتجات له."
    )

    if hasattr(message, "answer"):
        await message.answer(success_text)
    else:
        try:
            await message.edit_text(success_text)
        except Exception:
            pass

    await state.clear()


# ══════════════ تفاصيل قسم فرعي ══════════════

@router.callback_query(F.data.startswith("admin:subcat_view:"))
async def subcat_view(callback: CallbackQuery, session):
    """يعرض تفاصيل قسم فرعي."""
    sub_id = int(callback.data.split(":")[2])
    sub = await DynamicService.get_sub_category(
        session, sub_id
    )

    if not sub:
        await callback.answer(
            "⚠️ غير موجود", show_alert=True
        )
        return

    await _show_sub_category_details(
        callback.message, sub, edit=True
    )


async def _show_sub_category_details(
    message,
    sub: SubCategory,
    edit: bool = True,
):
    """يعرض تفاصيل قسم فرعي."""
    status = "🟢 مفعّل" if sub.is_active else "🔴 معطّل"

    products_count = (
        len(sub.products) if sub.products else 0
    )
    active_products = 0
    if sub.products:
        from database.models import ProductStatus
        active_products = sum(
            1 for p in sub.products
            if p.status == ProductStatus.ACTIVE
        )

    text = (
        f"{sub.emoji} <b>{sub.name_ar}</b>\n\n"
        f"📊 الحالة: {status}\n"
        f"🔢 الترتيب: {sub.sort_order}\n\n"
    )

    if sub.description:
        text += f"📝 الوصف: <i>{sub.description}</i>\n\n"

    text += (
        f"📦 عدد المنتجات: <b>{products_count}</b>\n"
        f"🟢 نشطة منها: <b>{active_products}</b>\n\n"
    )

    if sub.image_file_id or sub.image_url:
        text += "🖼 يحتوي صورة ✅\n\n"

    text += (
        f"📅 تاريخ الإنشاء: "
        f"{sub.created_at.strftime('%Y-%m-%d')}"
    )

    kb = sub_category_detail_kb(sub)

    if edit:
        try:
            await message.edit_text(text, reply_markup=kb)
        except Exception:
            await message.answer(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


# ══════════════ تفعيل/تعطيل قسم فرعي ══════════════

@router.callback_query(F.data.startswith("admin:subcat_toggle:"))
async def subcat_toggle(
    callback: CallbackQuery, session, db_user
):
    """يبدل حالة قسم فرعي."""
    sub_id = int(callback.data.split(":")[2])
    sub = await session.get(SubCategory, sub_id)

    if not sub:
        await callback.answer(
            "⚠️ غير موجود", show_alert=True
        )
        return

    sub.is_active = not sub.is_active
    await session.commit()

    await AuditService.log_toggle(
        admin_id=db_user.id,
        entity_type="sub_category",
        entity_id=sub.id,
        entity_name=sub.name_ar,
        new_status=sub.is_active,
        session=session,
    )

    status_text = (
        "✅ تم تفعيل" if sub.is_active else "❌ تم تعطيل"
    )
    await callback.answer(f"{status_text} القسم الفرعي")

    await session.refresh(sub)
    await _show_sub_category_details(
        callback.message, sub, edit=True
    )


# ══════════════ تعديل قسم فرعي ══════════════

@router.callback_query(F.data.startswith("admin:subcat_edit:"))
async def subcat_edit_start(
    callback: CallbackQuery, state: FSMContext
):
    """يبدأ تعديل حقل في قسم فرعي."""
    parts = callback.data.split(":")
    field = parts[2]
    sub_id = int(parts[3])

    await state.update_data(
        edit_sub_id=sub_id,
        edit_field=field,
    )

    field_prompts = {
        "name": "📝 أرسل الاسم الجديد:",
        "emoji": "🎨 أرسل الإيموجي الجديد:",
        "desc": "📝 أرسل الوصف الجديد (أو - لحذفه):",
        "image": "🖼 أرسل الصورة الجديدة (صورة أو رابط أو - لحذفها):",
        "sort": "🔢 أرسل رقم الترتيب الجديد:",
    }

    prompt = field_prompts.get(
        field, "أرسل القيمة الجديدة:"
    )

    await callback.message.edit_text(
        prompt,
        reply_markup=cancel_add_kb(
            f"admin:subcat_view:{sub_id}"
        ),
    )
    await state.set_state(
        AdminSubCategoryStates.waiting_edit_value
    )


@router.message(
    AdminSubCategoryStates.waiting_edit_value,
    F.photo,
)
async def subcat_edit_image_photo(
    message: Message,
    state: FSMContext,
    session,
    db_user,
):
    """يستقبل صورة للتعديل."""
    data = await state.get_data()
    sub_id = data.get("edit_sub_id")
    field = data.get("edit_field")

    if field != "image":
        return

    sub = await session.get(SubCategory, sub_id)
    if not sub:
        await message.answer("⚠️ القسم غير موجود.")
        await state.clear()
        return

    old_value = "لديه صورة" if sub.image_file_id else "بدون"
    sub.image_file_id = message.photo[-1].file_id
    sub.image_url = None
    await session.commit()

    await AuditService.log_update(
        admin_id=db_user.id,
        entity_type="sub_category",
        entity_id=sub.id,
        entity_name=sub.name_ar,
        field="image",
        old_value=old_value,
        new_value="لديه صورة",
        session=session,
    )

    await message.answer("✅ تم تحديث الصورة.")
    await state.clear()

    await session.refresh(sub)
    await _show_sub_category_details(
        message, sub, edit=False
    )


@router.message(AdminSubCategoryStates.waiting_edit_value)
async def subcat_edit_value_received(
    message: Message,
    state: FSMContext,
    session,
    db_user,
):
    """يستقبل القيمة الجديدة."""
    data = await state.get_data()
    sub_id = data.get("edit_sub_id")
    field = data.get("edit_field")

    if not sub_id or not field:
        await message.answer("⚠️ جلسة منتهية.")
        await state.clear()
        return

    sub = await session.get(SubCategory, sub_id)
    if not sub:
        await message.answer("⚠️ القسم غير موجود.")
        await state.clear()
        return

    value = message.text.strip()
    old_value = None

    if field == "name":
        if len(value) < 2 or len(value) > 64:
            await message.answer(
                "⚠️ الاسم يجب أن يكون بين 2 و 64."
            )
            return
        old_value = sub.name_ar
        sub.name_ar = value

    elif field == "emoji":
        if len(value) > 8:
            await message.answer("⚠️ إيموجي واحد فقط.")
            return
        old_value = sub.emoji
        sub.emoji = value

    elif field == "desc":
        if value == "-":
            old_value = sub.description
            sub.description = None
        else:
            if len(value) > 255:
                await message.answer("⚠️ الوصف طويل.")
                return
            old_value = sub.description
            sub.description = value

    elif field == "image":
        if value == "-":
            old_value = "لديه صورة" if sub.image_file_id or sub.image_url else "بدون"
            sub.image_file_id = None
            sub.image_url = None
        elif value.startswith(("http://", "https://")):
            if len(value) > 500:
                await message.answer("⚠️ الرابط طويل.")
                return
            old_value = "قديمة"
            sub.image_url = value
            sub.image_file_id = None
        else:
            await message.answer(
                "⚠️ أرسل رابط أو صورة أو - للحذف."
            )
            return

    elif field == "sort":
        try:
            sort_val = int(value)
        except ValueError:
            await message.answer("⚠️ أرسل رقماً.")
            return
        old_value = sub.sort_order
        sub.sort_order = sort_val

    await session.commit()

    await AuditService.log_update(
        admin_id=db_user.id,
        entity_type="sub_category",
        entity_id=sub.id,
        entity_name=sub.name_ar,
        field=field,
        old_value=old_value,
        new_value=value,
        session=session,
    )

    await message.answer(f"✅ تم تحديث {field}.")
    await state.clear()

    await session.refresh(sub)
    await _show_sub_category_details(
        message, sub, edit=False
    )


# ══════════════ حذف قسم فرعي ══════════════

@router.callback_query(
    F.data.startswith("admin:subcat_delete_confirm:")
)
async def subcat_delete_confirm(
    callback: CallbackQuery, session
):
    """تأكيد حذف قسم فرعي."""
    sub_id = int(callback.data.split(":")[2])
    sub = await DynamicService.get_sub_category(
        session, sub_id
    )

    if not sub:
        await callback.answer(
            "⚠️ غير موجود", show_alert=True
        )
        return

    products_count = (
        len(sub.products) if sub.products else 0
    )

    text = (
        f"⚠️ <b>تأكيد حذف القسم الفرعي</b>\n\n"
        f"سيتم حذف:\n"
        f"• القسم: {sub.emoji} {sub.name_ar}\n"
    )
    if products_count > 0:
        text += f"• <b>{products_count}</b> منتج\n"
    text += "\n<b>هل أنت متأكد؟ لا يمكن التراجع!</b>"

    await callback.message.edit_text(
        text,
        reply_markup=confirm_delete_sub_category_kb(
            sub.id, sub.category_id, products_count
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:subcat_delete:"))
async def subcat_delete(
    callback: CallbackQuery, session, db_user
):
    """يحذف قسم فرعي."""
    sub_id = int(callback.data.split(":")[2])
    sub = await session.get(SubCategory, sub_id)

    if not sub:
        await callback.answer(
            "⚠️ غير موجود", show_alert=True
        )
        return

    sub_name = sub.name_ar
    parent_id = sub.category_id

    await AuditService.log_delete(
        admin_id=db_user.id,
        entity_type="sub_category",
        entity_id=sub.id,
        entity_name=sub_name,
        session=session,
    )

    await session.delete(sub)
    await session.commit()

    await callback.answer(f"🗑 تم حذف: {sub_name}")
    logger.info(
        f"الأدمن {db_user.telegram_id} حذف "
        f"القسم الفرعي #{sub_id}"
    )

    from types import SimpleNamespace
    fake_callback = SimpleNamespace(
        data=f"admin:subcat_list:{parent_id}",
        message=callback.message,
        answer=callback.answer,
        from_user=callback.from_user,
    )
    await subcat_list(fake_callback, session)
```

### `handlers/admin/channels.py`

```python
"""
إدارة قنوات الاشتراك الإجباري.
"""
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from database.models import MandatoryChannel
from states.states import AdminChannelStates
from keyboards.admin import admin_channels_kb, admin_back_kb
from filters.admin_filter import IsAdmin

router = Router(name="admin_channels")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "admin:channels")
async def channels_list(callback: CallbackQuery, session):
    result = await session.execute(
        select(MandatoryChannel).where(
            MandatoryChannel.is_active == True
        )
    )
    channels = result.scalars().all()
    text = "📌 <b>قنوات الاشتراك الإجباري:</b>\n\n"
    if channels:
        text += "\n".join([
            f"• {c.title or c.chat_id}"
            for c in channels
        ])
    else:
        text += "لا يوجد قنوات مضافة."

    await callback.message.edit_text(
        text,
        reply_markup=admin_channels_kb(channels),
    )


@router.callback_query(F.data == "admin:channel_add")
async def channel_add_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.message.edit_text(
        "➕ أرسل آيدي القناة أو يوزرها:\n"
        "(مثال: -1001234567890 أو @mychannel)\n\n"
        "⚠️ يجب أن يكون البوت أدمن بالقناة أولاً.",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(AdminChannelStates.waiting_channel_id)


@router.message(AdminChannelStates.waiting_channel_id)
async def channel_add_received(
    message: Message,
    state: FSMContext,
    session,
    bot,
):
    raw = message.text.strip()
    try:
        chat = await bot.get_chat(raw)
    except Exception:
        await message.answer(
            "⚠️ تعذر العثور على القناة.\n"
            "تأكد أن البوت أدمن فيها وأن المعرف صحيح."
        )
        return

    existing = await session.execute(
        select(MandatoryChannel).where(
            MandatoryChannel.chat_id == chat.id
        )
    )
    if existing.scalar_one_or_none():
        await message.answer("⚠️ هذه القناة مضافة مسبقاً.")
        await state.clear()
        return

    channel = MandatoryChannel(
        chat_id=chat.id,
        username_or_link=(
            f"https://t.me/{chat.username}"
            if chat.username
            else None
        ),
        title=chat.title,
    )
    session.add(channel)
    await session.commit()

    await message.answer(
        f"✅ تمت إضافة القناة: {chat.title}"
    )
    await state.clear()


@router.callback_query(F.data.startswith("admin:channel_del:"))
async def channel_delete(
    callback: CallbackQuery, session
):
    channel_id = int(callback.data.split(":")[2])
    channel = await session.get(MandatoryChannel, channel_id)
    if channel:
        channel.is_active = False
        await session.commit()
        await callback.answer("✅ تم إلغاء تفعيل القناة.")
    else:
        await callback.answer(
            "⚠️ غير موجود.", show_alert=True
        )
    await channels_list(callback, session)
```

### `handlers/admin/countries.py`

```python
"""
إدارة الدول من لوحة الأدمن.
يدعم 4 مزودين الآن بدل 2.
"""
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from database.models import Country
from providers.countries import get_all_countries
from providers.fivesim import FiveSimProvider
from states.states import AdminCountryStates
from keyboards.admin import (
    admin_countries_kb, admin_country_detail_kb,
    admin_back_kb,
)
from filters.admin_filter import IsAdmin

router = Router(name="admin_countries")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "admin:countries")
async def countries_list(callback: CallbackQuery, session):
    countries = await get_all_countries(session)
    text = (
        "🌍 <b>إدارة الدول</b>\n\n"
        "🟢 = مفعّلة | ⚪ = معطّلة\n\n"
    )
    if countries:
        text += "اضغط على أي دولة لتعديلها."
    else:
        text += "لا توجد أي دولة مضافة بعد."
    await callback.message.edit_text(
        text, reply_markup=admin_countries_kb(countries)
    )


@router.callback_query(F.data == "admin:country_add")
async def country_add_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.message.edit_text(
        "➕ <b>إضافة دولة جديدة</b>\n\n"
        "أرسل معرّفاً داخلياً بالإنجليزية:\n"
        "(مثال: <code>egypt</code>)",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(AdminCountryStates.waiting_code)


@router.message(AdminCountryStates.waiting_code)
async def country_code_received(
    message: Message, state: FSMContext, session
):
    code = message.text.strip().lower().replace(" ", "_")
    existing = await session.execute(
        select(Country).where(Country.code == code)
    )
    if existing.scalar_one_or_none():
        await message.answer(
            "⚠️ يوجد دولة بهذا المعرّف. أرسل معرّفاً آخر."
        )
        return
    await state.update_data(code=code)
    await message.answer("✏️ أرسل اسم الدولة بالعربي:")
    await state.set_state(AdminCountryStates.waiting_name_ar)


@router.message(AdminCountryStates.waiting_name_ar)
async def country_name_received(
    message: Message, state: FSMContext
):
    await state.update_data(name_ar=message.text.strip())
    await message.answer(
        "🚩 أرسل علم الدولة (إيموجي):\n"
        "(أو أرسل - للتخطي)"
    )
    await state.set_state(AdminCountryStates.waiting_flag)


@router.message(AdminCountryStates.waiting_flag)
async def country_flag_received(
    message: Message, state: FSMContext
):
    flag = message.text.strip()
    await state.update_data(flag=None if flag == "-" else flag)
    await message.answer(
        "🔢 أرسل كود الدولة لدى <b>5sim</b>:\n"
        "(أو أرسل - للتخطي)"
    )
    await state.set_state(AdminCountryStates.waiting_fivesim_code)


@router.message(AdminCountryStates.waiting_fivesim_code)
async def country_fivesim_received(
    message: Message, state: FSMContext
):
    val = message.text.strip()
    await state.update_data(
        fivesim_code=None if val == "-" else val
    )
    await message.answer(
        "🔢 أرسل كود الدولة لدى <b>HeroSMS</b>:\n"
        "(أو أرسل - للتخطي)"
    )
    await state.set_state(AdminCountryStates.waiting_herosms_code)


@router.message(AdminCountryStates.waiting_herosms_code)
async def country_herosms_received(
    message: Message, state: FSMContext
):
    val = message.text.strip()
    await state.update_data(
        herosms_code=None if val == "-" else val
    )
    await message.answer(
        "🔢 أرسل كود الدولة لدى <b>SMS-Activate</b>:\n"
        "(أو أرسل - للتخطي)"
    )
    await state.set_state(
        AdminCountryStates.waiting_sms_activate_code
    )


@router.message(AdminCountryStates.waiting_sms_activate_code)
async def country_sms_activate_received(
    message: Message, state: FSMContext
):
    val = message.text.strip()
    await state.update_data(
        sms_activate_code=None if val == "-" else val
    )
    await message.answer(
        "🔢 أرسل كود الدولة لدى <b>SMSHub</b>:\n"
        "(أو أرسل - للتخطي)"
    )
    await state.set_state(AdminCountryStates.waiting_smshub_code)


@router.message(AdminCountryStates.waiting_smshub_code)
async def country_smshub_received(
    message: Message,
    state: FSMContext,
    session,
    db_user,
):
    val = message.text.strip()
    data = await state.get_data()

    fivesim_code = data.get("fivesim_code")
    herosms_code = data.get("herosms_code")
    sms_activate_code = data.get("sms_activate_code")
    smshub_code = None if val == "-" else val

    if not any([
        fivesim_code, herosms_code,
        sms_activate_code, smshub_code
    ]):
        await message.answer(
            "⚠️ يجب تحديد كود لمزود واحد على الأقل."
        )
        await state.clear()
        return

    country = Country(
        code=data["code"],
        name_ar=data["name_ar"],
        flag=data.get("flag") or "🌍",
        fivesim_code=fivesim_code,
        herosms_code=herosms_code,
        sms_activate_code=sms_activate_code,
        smshub_code=smshub_code,
        is_active=False,
        added_by_admin_id=db_user.id,
    )
    session.add(country)
    await session.commit()

    await message.answer(
        f"✅ تمت إضافة الدولة {country.flag} "
        f"{country.name_ar} (معطّلة حالياً).\n"
        "فعّلها من قائمة الدول عندما تكون جاهزاً."
    )
    await state.clear()


@router.callback_query(F.data.startswith("admin:country_view:"))
async def country_view(callback: CallbackQuery, session):
    country_id = int(callback.data.split(":")[2])
    country = await session.get(Country, country_id)
    if not country:
        await callback.answer("⚠️ غير موجود.", show_alert=True)
        return

    status = (
        "🟢 مفعّلة" if country.is_active else "⚪ معطّلة"
    )
    await callback.message.edit_text(
        f"{country.flag} <b>{country.name_ar}</b>\n\n"
        f"المعرّف: <code>{country.code}</code>\n"
        f"الحالة: {status}\n"
        f"5sim: <code>{country.fivesim_code or '—'}</code>\n"
        f"HeroSMS: <code>{country.herosms_code or '—'}</code>\n"
        f"SMS-Activate: <code>{country.sms_activate_code or '—'}</code>\n"
        f"SMSHub: <code>{country.smshub_code or '—'}</code>\n"
        f"الترتيب: {country.sort_order}",
        reply_markup=admin_country_detail_kb(country),
    )


@router.callback_query(F.data.startswith("admin:country_toggle:"))
async def country_toggle(callback: CallbackQuery, session):
    country_id = int(callback.data.split(":")[2])
    country = await session.get(Country, country_id)
    if not country:
        await callback.answer("⚠️ غير موجود.", show_alert=True)
        return
    country.is_active = not country.is_active
    await session.commit()
    await callback.answer("✅ تم التحديث.")
    await country_view(callback, session)


@router.callback_query(F.data.startswith("admin:country_delete:"))
async def country_delete(callback: CallbackQuery, session):
    country_id = int(callback.data.split(":")[2])
    country = await session.get(Country, country_id)
    if not country:
        await callback.answer("⚠️ غير موجود.", show_alert=True)
        return
    await session.delete(country)
    await session.commit()
    await callback.answer("🗑 تم الحذف.")
    await countries_list(callback, session)


@router.callback_query(F.data == "admin:country_reference_list")
async def country_reference_list(callback: CallbackQuery):
    await callback.answer("⏳ جاري الجلب...")
    try:
        provider = FiveSimProvider()
        countries = await provider.list_countries()
        text = (
            "🌍 <b>أكواد دول 5sim:</b>\n\n"
            + "\n".join(countries[:40])
        )
    except Exception as e:
        text = f"⚠️ تعذّر الجلب: {e}"
    await callback.message.answer(text)
```

### `handlers/admin/coupons.py`

```python
"""
إدارة كوبونات الخصم من لوحة الأدمن.
"""
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import User
from services.coupon_service import CouponService
from states.states import AdminCouponStates
from keyboards.admin import (
    admin_coupons_kb, admin_coupon_detail_kb,
    admin_back_kb,
)
from filters.admin_filter import IsAdmin

router = Router(name="admin_coupons")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# ══════════════ قائمة الكوبونات ══════════════

@router.callback_query(F.data == "admin:coupons")
async def coupons_list(callback: CallbackQuery, session):
    coupons = await CouponService.get_all_coupons(session)
    await callback.message.edit_text(
        "🎟 <b>إدارة الكوبونات</b>\n\n"
        "🟢 = مفعّل | ⚪ = معطّل",
        reply_markup=admin_coupons_kb(coupons),
    )


# ══════════════ إنشاء كوبون ══════════════

@router.callback_query(F.data == "admin:coupon_add")
async def coupon_add_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.message.edit_text(
        "🎟 <b>إنشاء كوبون جديد</b>\n\n"
        "أرسل كود الكوبون:\n"
        "(مثال: SAVE10)",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(AdminCouponStates.waiting_code)


@router.message(AdminCouponStates.waiting_code)
async def coupon_code_received(
    message: Message, state: FSMContext, session
):
    code = message.text.strip().upper()
    existing = await CouponService.get_coupon_by_code(
        session, code
    )
    if existing:
        await message.answer(
            "⚠️ يوجد كوبون بهذا الكود مسبقاً. أرسل كوداً آخر."
        )
        return

    await state.update_data(coupon_code=code)

    b = InlineKeyboardBuilder()
    b.button(
        text="📊 نسبة مئوية (%)",
        callback_data="admin:coupon_dtype:percent",
    )
    b.button(
        text="💵 مبلغ ثابت ($)",
        callback_data="admin:coupon_dtype:fixed",
    )
    b.adjust(1)
    await message.answer(
        "اختر نوع الخصم:",
        reply_markup=b.as_markup(),
    )


@router.callback_query(F.data.startswith("admin:coupon_dtype:"))
async def coupon_dtype_selected(
    callback: CallbackQuery, state: FSMContext
):
    dtype = callback.data.split(":")[2]
    await state.update_data(coupon_dtype=dtype)

    label = "النسبة (%)" if dtype == "percent" else "المبلغ ($)"
    await callback.message.edit_text(
        f"🔢 أرسل قيمة الخصم ({label}):\n"
        "(مثال: 10)"
    )
    await state.set_state(AdminCouponStates.waiting_discount_value)
    await callback.answer()


@router.message(AdminCouponStates.waiting_discount_value)
async def coupon_value_received(
    message: Message, state: FSMContext
):
    try:
        value = Decimal(message.text.strip())
        if value <= 0:
            raise InvalidOperation
    except InvalidOperation:
        await message.answer("⚠️ أرسل رقماً صحيحاً أكبر من صفر.")
        return

    await state.update_data(coupon_value=str(value))
    await message.answer(
        "🔢 أرسل الحد الأقصى لعدد الاستخدامات:\n"
        "(مثال: 100)"
    )
    await state.set_state(AdminCouponStates.waiting_max_uses)


@router.message(AdminCouponStates.waiting_max_uses)
async def coupon_max_uses_received(
    message: Message, state: FSMContext
):
    try:
        max_uses = int(message.text.strip())
        if max_uses <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ أرسل رقماً صحيحاً أكبر من صفر.")
        return

    await state.update_data(coupon_max_uses=max_uses)
    await message.answer(
        "💰 أرسل الحد الأدنى لقيمة الطلب بالدولار:\n"
        "(أو أرسل 0 لبدون حد أدنى)"
    )
    await state.set_state(AdminCouponStates.waiting_min_order)


@router.message(AdminCouponStates.waiting_min_order)
async def coupon_min_order_received(
    message: Message, state: FSMContext
):
    try:
        min_order = Decimal(message.text.strip())
    except InvalidOperation:
        await message.answer("⚠️ أرسل رقماً صحيحاً.")
        return

    await state.update_data(coupon_min_order=str(min_order))
    await message.answer(
        "📅 أرسل عدد أيام صلاحية الكوبون:\n"
        "(أو أرسل 0 لبدون تاريخ انتهاء)"
    )
    await state.set_state(AdminCouponStates.waiting_expires_days)


@router.message(AdminCouponStates.waiting_expires_days)
async def coupon_expires_received(
    message: Message,
    state: FSMContext,
    session,
    db_user: User,
):
    try:
        days = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ أرسل رقماً صحيحاً.")
        return

    data = await state.get_data()

    expires_at = None
    if days > 0:
        expires_at = datetime.utcnow() + timedelta(days=days)

    coupon = await CouponService.create_coupon(
        session=session,
        code=data["coupon_code"],
        discount_type=data["coupon_dtype"],
        discount_value=Decimal(data["coupon_value"]),
        max_uses=data["coupon_max_uses"],
        min_order_usd=Decimal(data.get("coupon_min_order", "0")),
        expires_at=expires_at,
        created_by=db_user.id,
    )

    dtype_label = (
        f"{coupon.discount_value}%"
        if coupon.discount_type == "percent"
        else f"{coupon.discount_value}$"
    )
    expires_label = (
        expires_at.strftime("%Y-%m-%d")
        if expires_at
        else "بدون انتهاء"
    )

    await message.answer(
        f"✅ تم إنشاء الكوبون بنجاح!\n\n"
        f"🎟 الكود: <code>{coupon.code}</code>\n"
        f"💰 الخصم: {dtype_label}\n"
        f"🔢 الاستخدامات: {coupon.max_uses}\n"
        f"💵 حد أدنى للطلب: {coupon.min_order_usd}$\n"
        f"📅 الانتهاء: {expires_label}"
    )
    await state.clear()


# ══════════════ تفاصيل الكوبون ══════════════

@router.callback_query(F.data.startswith("admin:coupon_view:"))
async def coupon_view(callback: CallbackQuery, session):
    coupon_id = int(callback.data.split(":")[2])
    coupon = await session.get(
        __import__("database.models", fromlist=["Coupon"]).Coupon,
        coupon_id,
    )
    if not coupon:
        await callback.answer("⚠️ غير موجود.", show_alert=True)
        return

    status = "🟢 مفعّل" if coupon.is_active else "⚪ معطّل"
    dtype_label = (
        f"{coupon.discount_value}%"
        if coupon.discount_type == "percent"
        else f"{coupon.discount_value}$"
    )
    expires_label = (
        coupon.expires_at.strftime("%Y-%m-%d")
        if coupon.expires_at
        else "بدون انتهاء"
    )

    await callback.message.edit_text(
        f"🎟 <b>كوبون: {coupon.code}</b>\n\n"
        f"الحالة: {status}\n"
        f"💰 الخصم: {dtype_label}\n"
        f"🔢 الاستخدامات: {coupon.used_count}/{coupon.max_uses}\n"
        f"💵 حد أدنى: {coupon.min_order_usd}$\n"
        f"📅 الانتهاء: {expires_label}\n"
        f"📅 تاريخ الإنشاء: "
        f"{coupon.created_at.strftime('%Y-%m-%d')}",
        reply_markup=admin_coupon_detail_kb(coupon),
    )


# ══════════════ تفعيل/تعطيل ══════════════

@router.callback_query(F.data.startswith("admin:coupon_toggle:"))
async def coupon_toggle(callback: CallbackQuery, session):
    coupon_id = int(callback.data.split(":")[2])
    coupon = await CouponService.toggle_coupon(session, coupon_id)
    if coupon:
        await callback.answer("✅ تم التحديث.")
        await coupon_view(callback, session)
    else:
        await callback.answer("⚠️ غير موجود.", show_alert=True)


# ══════════════ حذف ══════════════

@router.callback_query(F.data.startswith("admin:coupon_delete:"))
async def coupon_delete(callback: CallbackQuery, session):
    coupon_id = int(callback.data.split(":")[2])
    success = await CouponService.delete_coupon(session, coupon_id)
    if success:
        await callback.answer("🗑 تم حذف الكوبون.")
    else:
        await callback.answer("⚠️ غير موجود.", show_alert=True)
    await coupons_list(callback, session)
```

### `handlers/admin/multi_admin.py`

```python
"""
إدارة الأدمنية المتعددة من لوحة الأدمن.
الأدمن الرئيسي (من ADMIN_IDS في .env) محمي ولا يمكن إزالته.
"""
import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from config import settings
from database.models import User
from states.states import AdminMultiAdminStates
from keyboards.admin import (
    admin_multi_admin_kb, admin_madmin_detail_kb,
    admin_back_kb,
)
from filters.admin_filter import IsAdmin

logger = logging.getLogger(__name__)

router = Router(name="admin_multi_admin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# ══════════════ قائمة الأدمنية ══════════════

@router.callback_query(F.data == "admin:multi_admin")
async def multi_admin_list(
    callback: CallbackQuery, session
):
    result = await session.execute(
        select(User).where(User.is_admin == True)
    )
    admins = result.scalars().all()

    await callback.message.edit_text(
        "👨‍💼 <b>إدارة الأدمنية</b>\n\n"
        f"عدد الأدمنية الحاليين: {len(admins)}\n"
        "⭐ = أدمن رئيسي (محمي من الحذف)",
        reply_markup=admin_multi_admin_kb(admins),
    )


# ══════════════ تفاصيل أدمن ══════════════

@router.callback_query(F.data.startswith("admin:madmin_view:"))
async def madmin_view(callback: CallbackQuery, session):
    user_id = int(callback.data.split(":")[2])
    user = await session.get(User, user_id)
    if not user:
        await callback.answer("⚠️ المستخدم غير موجود.", show_alert=True)
        return

    is_primary = user.telegram_id in settings.admin_ids_list
    primary_label = "⭐ أدمن رئيسي (محمي)" if is_primary else "👤 أدمن عادي"

    await callback.message.edit_text(
        f"👨‍💼 <b>تفاصيل الأدمن</b>\n\n"
        f"🆔 آيدي: {user.telegram_id}\n"
        f"👤 يوزر: @{user.username or '-'}\n"
        f"📛 الاسم: {user.full_name or '-'}\n"
        f"💰 الرصيد: {user.balance:.2f}$\n"
        f"🏅 النوع: {primary_label}\n"
        f"📅 الانضمام: {user.joined_at.strftime('%Y-%m-%d')}",
        reply_markup=admin_madmin_detail_kb(user, is_primary),
    )


# ══════════════ إضافة أدمن ══════════════

@router.callback_query(F.data == "admin:madmin_add")
async def madmin_add_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.message.edit_text(
        "➕ <b>إضافة أدمن جديد</b>\n\n"
        "أرسل آيدي المستخدم (Telegram ID) "
        "الذي تريد منحه صلاحيات الأدمن:\n\n"
        "⚠️ تأكد أن المستخدم قد تفاعل مع البوت مسبقاً.",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(AdminMultiAdminStates.waiting_admin_id)


@router.message(AdminMultiAdminStates.waiting_admin_id)
async def madmin_add_received(
    message: Message, state: FSMContext, session, db_user: User
):
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ أرسل آيدي صحيح (أرقام فقط).")
        return

    if tg_id == db_user.telegram_id:
        await message.answer("⚠️ أنت أدمن بالفعل!")
        await state.clear()
        return

    result = await session.execute(
        select(User).where(User.telegram_id == tg_id)
    )
    target_user = result.scalar_one_or_none()

    if target_user is None:
        await message.answer(
            "⚠️ لا يوجد مستخدم بهذا الآيدي في البوت.\n"
            "يجب أن يكون المستخدم قد تفاعل مع البوت أولاً."
        )
        await state.clear()
        return

    if target_user.is_admin:
        await message.answer(
            f"⚠️ المستخدم {tg_id} هو أدمن بالفعل."
        )
        await state.clear()
        return

    target_user.is_admin = True
    await session.commit()

    logger.info(
        f"الأدمن {db_user.telegram_id} منح صلاحيات أدمن "
        f"للمستخدم {tg_id}"
    )

    await message.answer(
        f"✅ تم منح صلاحيات الأدمن للمستخدم "
        f"{target_user.full_name or tg_id} "
        f"(@{target_user.username or '-'}) بنجاح.\n\n"
        "يمكنه الآن الوصول للوحة التحكم عبر /admin"
    )
    await state.clear()


# ══════════════ إزالة أدمن ══════════════

@router.callback_query(F.data.startswith("admin:madmin_remove:"))
async def madmin_remove(
    callback: CallbackQuery, session, db_user: User
):
    user_id = int(callback.data.split(":")[2])
    target_user = await session.get(User, user_id)

    if not target_user:
        await callback.answer("⚠️ المستخدم غير موجود.", show_alert=True)
        return

    if target_user.telegram_id in settings.admin_ids_list:
        await callback.answer(
            "⛔ لا يمكن إزالة الأدمن الرئيسي.",
            show_alert=True,
        )
        return

    if target_user.id == db_user.id:
        await callback.answer(
            "⛔ لا يمكنك إزالة نفسك.",
            show_alert=True,
        )
        return

    target_user.is_admin = False
    await session.commit()

    logger.info(
        f"الأدمن {db_user.telegram_id} أزال صلاحيات أدمن "
        f"من المستخدم {target_user.telegram_id}"
    )

    await callback.answer(
        f"✅ تم إزالة صلاحيات الأدمن من "
        f"{target_user.telegram_id}."
    )
    await multi_admin_list(callback, session)
```

### `handlers/admin/number_services.py`

```python
"""
إدارة خدمات الأرقام الديناميكية من لوحة الأدمن.
بدل SERVICE_MAP الثابت، كل خدمة تُدار من هنا.
"""
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from services.dynamic_service import DynamicService
from states.states import AdminNumberServiceStates
from keyboards.admin import (
    admin_number_services_kb, admin_nsvc_detail_kb,
    admin_back_kb,
)
from filters.admin_filter import IsAdmin

router = Router(name="admin_number_services")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# ══════════════ قائمة الخدمات ══════════════

@router.callback_query(F.data == "admin:number_services")
async def number_services_list(
    callback: CallbackQuery, session
):
    services = await DynamicService.get_all_number_services(session)
    await callback.message.edit_text(
        "📞 <b>إدارة خدمات الأرقام</b>\n\n"
        "🟢 = مفعّلة | ⚪ = معطّلة\n\n"
        "هذه الخدمات تظهر في القائمة الرئيسية للمستخدمين.",
        reply_markup=admin_number_services_kb(services),
    )


# ══════════════ إضافة خدمة ══════════════

@router.callback_query(F.data == "admin:nsvc_add")
async def nsvc_add_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.message.edit_text(
        "➕ <b>إضافة خدمة أرقام جديدة</b>\n\n"
        "أرسل كود الخدمة بالإنجليزية (بدون مسافات):\n"
        "(مثال: instagram أو snapchat)",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(AdminNumberServiceStates.waiting_code)


@router.message(AdminNumberServiceStates.waiting_code)
async def nsvc_code_received(
    message: Message, state: FSMContext, session
):
    code = message.text.strip().lower().replace(" ", "_")

    existing = await DynamicService.get_number_service_by_code(
        session, code
    )
    if existing:
        await message.answer(
            "⚠️ توجد خدمة بهذا الكود مسبقاً. أرسل كوداً آخر."
        )
        return

    await state.update_data(nsvc_code=code)
    await message.answer(
        "📝 أرسل اسم الخدمة بالعربي:\n"
        "(مثال: إنستقرام)"
    )
    await state.set_state(AdminNumberServiceStates.waiting_name)


@router.message(AdminNumberServiceStates.waiting_name)
async def nsvc_name_received(
    message: Message, state: FSMContext
):
    await state.update_data(nsvc_name=message.text.strip())
    await message.answer(
        "أرسل إيموجي للخدمة:\n"
        "(أو أرسل - لاستخدام 📱)"
    )
    await state.set_state(AdminNumberServiceStates.waiting_emoji)


@router.message(AdminNumberServiceStates.waiting_emoji)
async def nsvc_emoji_received(
    message: Message, state: FSMContext
):
    emoji = message.text.strip()
    if emoji == "-":
        emoji = "📱"
    await state.update_data(nsvc_emoji=emoji)
    await message.answer(
        "🔢 أرسل كود الخدمة لدى <b>5sim</b>:\n"
        "(أو أرسل - للتخطي)"
    )
    await state.set_state(
        AdminNumberServiceStates.waiting_fivesim_code
    )


@router.message(AdminNumberServiceStates.waiting_fivesim_code)
async def nsvc_fivesim_received(
    message: Message, state: FSMContext
):
    val = message.text.strip()
    await state.update_data(
        nsvc_fivesim=None if val == "-" else val
    )
    await message.answer(
        "🔢 أرسل كود الخدمة لدى <b>HeroSMS</b>:\n"
        "(أو أرسل - للتخطي)"
    )
    await state.set_state(
        AdminNumberServiceStates.waiting_herosms_code
    )


@router.message(AdminNumberServiceStates.waiting_herosms_code)
async def nsvc_herosms_received(
    message: Message, state: FSMContext
):
    val = message.text.strip()
    await state.update_data(
        nsvc_herosms=None if val == "-" else val
    )
    await message.answer(
        "🔢 أرسل كود الخدمة لدى <b>SMS-Activate</b>:\n"
        "(أو أرسل - للتخطي)"
    )
    await state.set_state(
        AdminNumberServiceStates.waiting_sms_activate_code
    )


@router.message(AdminNumberServiceStates.waiting_sms_activate_code)
async def nsvc_sms_activate_received(
    message: Message, state: FSMContext
):
    val = message.text.strip()
    await state.update_data(
        nsvc_sms_activate=None if val == "-" else val
    )
    await message.answer(
        "🔢 أرسل كود الخدمة لدى <b>SMSHub</b>:\n"
        "(أو أرسل - للتخطي)"
    )
    await state.set_state(
        AdminNumberServiceStates.waiting_smshub_code
    )


@router.message(AdminNumberServiceStates.waiting_smshub_code)
async def nsvc_smshub_received(
    message: Message, state: FSMContext, session
):
    val = message.text.strip()
    data = await state.get_data()

    fivesim = data.get("nsvc_fivesim")
    herosms = data.get("nsvc_herosms")
    sms_activate = data.get("nsvc_sms_activate")
    smshub = None if val == "-" else val

    if not any([fivesim, herosms, sms_activate, smshub]):
        await message.answer(
            "⚠️ يجب تحديد كود لدى مزود واحد على الأقل."
        )
        await state.clear()
        return

    service = await DynamicService.create_number_service(
        session=session,
        code=data["nsvc_code"],
        name_ar=data["nsvc_name"],
        emoji=data["nsvc_emoji"],
        fivesim_code=fivesim,
        herosms_code=herosms,
        sms_activate_code=sms_activate,
        smshub_code=smshub,
    )

    await message.answer(
        f"✅ تم إضافة خدمة الأرقام:\n"
        f"{service.emoji} <b>{service.name_ar}</b>\n\n"
        "ستظهر الآن في القائمة الرئيسية للمستخدمين."
    )
    await state.clear()


# ══════════════ تفاصيل خدمة ══════════════

@router.callback_query(F.data.startswith("admin:nsvc_view:"))
async def nsvc_view(callback: CallbackQuery, session):
    svc_id = int(callback.data.split(":")[2])
    svc = await session.get(
        __import__(
            "database.models", fromlist=["NumberService"]
        ).NumberService,
        svc_id,
    )
    if not svc:
        await callback.answer("⚠️ غير موجود.", show_alert=True)
        return

    status = "🟢 مفعّلة" if svc.is_active else "⚪ معطّلة"
    await callback.message.edit_text(
        f"{svc.emoji} <b>{svc.name_ar}</b>\n\n"
        f"الكود: <code>{svc.code}</code>\n"
        f"الحالة: {status}\n"
        f"5sim: <code>{svc.fivesim_code or '—'}</code>\n"
        f"HeroSMS: <code>{svc.herosms_code or '—'}</code>\n"
        f"SMS-Activate: <code>{svc.sms_activate_code or '—'}</code>\n"
        f"SMSHub: <code>{svc.smshub_code or '—'}</code>\n"
        f"الترتيب: {svc.sort_order}",
        reply_markup=admin_nsvc_detail_kb(svc),
    )


# ══════════════ تفعيل/تعطيل ══════════════

@router.callback_query(F.data.startswith("admin:nsvc_toggle:"))
async def nsvc_toggle(callback: CallbackQuery, session):
    svc_id = int(callback.data.split(":")[2])
    svc = await DynamicService.update_number_service(
        session, svc_id,
        is_active=not (
            await session.get(
                __import__(
                    "database.models",
                    fromlist=["NumberService"]
                ).NumberService,
                svc_id,
            )
        ).is_active,
    )
    await callback.answer("✅ تم التحديث.")
    await nsvc_view(callback, session)


# ══════════════ تعديل الاسم ══════════════

@router.callback_query(F.data.startswith("admin:nsvc_edit_name:"))
async def nsvc_edit_name_start(
    callback: CallbackQuery, state: FSMContext
):
    svc_id = int(callback.data.split(":")[2])
    await state.update_data(edit_nsvc_id=svc_id)
    await callback.message.edit_text(
        "📝 أرسل الاسم الجديد بالعربي:",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(
        AdminNumberServiceStates.waiting_edit_value
    )


@router.message(AdminNumberServiceStates.waiting_edit_value)
async def nsvc_edit_received(
    message: Message, state: FSMContext, session
):
    data = await state.get_data()
    svc_id = data.get("edit_nsvc_id")
    await DynamicService.update_number_service(
        session, svc_id, name_ar=message.text.strip()
    )
    await message.answer("✅ تم تحديث الاسم.")
    await state.clear()


# ══════════════ حذف خدمة ══════════════

@router.callback_query(F.data.startswith("admin:nsvc_delete:"))
async def nsvc_delete(callback: CallbackQuery, session):
    svc_id = int(callback.data.split(":")[2])
    success = await DynamicService.delete_number_service(
        session, svc_id
    )
    if success:
        await callback.answer("🗑 تم حذف الخدمة.")
    else:
        await callback.answer("⚠️ غير موجود.", show_alert=True)
    await number_services_list(callback, session)
```

### `handlers/admin/panel.py`

```python
"""
لوحة تحكم الأدمن الرئيسية.
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards.admin import admin_main_kb, admin_maintenance_kb
from services.settings_service import SettingsService
from states.states import AdminMaintenanceStates
from filters.admin_filter import IsAdmin

router = Router(name="admin_panel")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(Command("admin"))
async def admin_entry(message: Message):
    await message.answer(
        "🛠 <b>لوحة تحكم الأدمن</b>",
        reply_markup=admin_main_kb(),
    )


@router.callback_query(F.data == "admin:main")
async def admin_main_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛠 <b>لوحة تحكم الأدمن</b>",
        reply_markup=admin_main_kb(),
    )


# ══════════════ وضع الصيانة ══════════════

@router.callback_query(F.data == "admin:maintenance")
async def maintenance_menu(callback: CallbackQuery):
    is_active = await SettingsService.get_bool(
        "maintenance_mode", False
    )
    current_msg = await SettingsService.get(
        "maintenance_message",
        "⚙️ البوت تحت الصيانة حالياً..."
    )
    status = "🔴 مفعّل" if is_active else "🟢 غير مفعّل"
    await callback.message.edit_text(
        f"🔧 <b>وضع الصيانة</b>\n\n"
        f"الحالة: {status}\n\n"
        f"📝 رسالة الصيانة الحالية:\n"
        f"<i>{current_msg}</i>",
        reply_markup=admin_maintenance_kb(is_active),
    )


@router.callback_query(F.data == "admin:maintenance_on")
async def maintenance_on(
    callback: CallbackQuery, session
):
    await SettingsService.set(
        session, "maintenance_mode", "true"
    )
    await callback.answer("✅ تم تفعيل وضع الصيانة.")
    await maintenance_menu(callback)


@router.callback_query(F.data == "admin:maintenance_off")
async def maintenance_off(
    callback: CallbackQuery, session
):
    await SettingsService.set(
        session, "maintenance_mode", "false"
    )
    await callback.answer("✅ تم إيقاف وضع الصيانة.")
    await maintenance_menu(callback)


@router.callback_query(F.data == "admin:maintenance_msg")
async def maintenance_msg_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.message.edit_text(
        "📝 أرسل رسالة الصيانة الجديدة:"
    )
    await state.set_state(
        AdminMaintenanceStates.waiting_message
    )


@router.message(AdminMaintenanceStates.waiting_message)
async def maintenance_msg_received(
    message: Message, state: FSMContext, session
):
    await SettingsService.set(
        session,
        "maintenance_message",
        message.text.strip(),
    )
    await message.answer(
        "✅ تم تحديث رسالة الصيانة.",
        reply_markup=admin_main_kb(),
    )
    await state.clear()
```

### `handlers/admin/pricing.py`

```python
"""
إعدادات الأسعار ونسبة الربح.
"""
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from services.settings_service import SettingsService
from states.states import AdminPricingStates
from keyboards.admin import admin_pricing_kb, admin_back_kb
from filters.admin_filter import IsAdmin

router = Router(name="admin_pricing")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "admin:pricing")
async def pricing_menu(callback: CallbackQuery):
    margin = await SettingsService.get_decimal(
        "default_profit_margin_percent"
    )
    await callback.message.edit_text(
        "💵 <b>إدارة الأسعار</b>\n\n"
        f"📈 نسبة الربح العامة الحالية: <b>{margin}%</b>\n\n"
        "هذه النسبة تُطبَّق على كل خدمة/دولة لا تملك "
        "نسبة مخصصة.\n"
        "يمكنك تعيين نسب مخصصة من صفحة تفاصيل كل خدمة.",
        reply_markup=admin_pricing_kb(),
    )


@router.callback_query(F.data == "admin:set_margin")
async def set_margin_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.message.edit_text(
        "📈 أرسل نسبة الربح العامة الجديدة (%):",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(
        AdminPricingStates.waiting_margin_value
    )


@router.message(AdminPricingStates.waiting_margin_value)
async def set_margin_received(
    message: Message, state: FSMContext, session
):
    try:
        margin = Decimal(message.text.strip())
        if margin < 0:
            raise InvalidOperation
    except InvalidOperation:
        await message.answer("⚠️ أرسل رقماً صحيحاً.")
        return

    await SettingsService.set(
        session,
        "default_profit_margin_percent",
        str(margin),
    )
    await message.answer(
        f"✅ تم تحديث نسبة الربح العامة إلى {margin}%"
    )
    await state.clear()
```

### `handlers/admin/products.py`

```python
"""
إدارة المنتجات من لوحة الأدمن.
"""
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import ProductStatus, ApiProviderType
from services.dynamic_service import DynamicService
from states.states import AdminProductStates
from keyboards.admin import (
    admin_products_list_kb, admin_product_detail_kb,
    admin_back_kb,
)
from filters.admin_filter import IsAdmin

router = Router(name="admin_products")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# ══════════════ قائمة المنتجات (عبر القسم الفرعي) ══════════════

@router.callback_query(F.data == "admin:products_menu")
async def products_menu(callback: CallbackQuery, session):
    categories = await DynamicService.get_all_categories(session)
    if not categories:
        await callback.message.edit_text(
            "⚠️ لا توجد أقسام. أنشئ قسماً أولاً.",
            reply_markup=admin_back_kb(),
        )
        return

    b = InlineKeyboardBuilder()
    for cat in categories:
        b.button(
            text=f"{cat.emoji} {cat.name_ar}",
            callback_data=f"admin:prods_cat:{cat.id}",
        )
    b.button(text="🔙 رجوع", callback_data="admin:main")
    b.adjust(2)
    await callback.message.edit_text(
        "📦 <b>إدارة المنتجات</b>\n\n"
        "اختر القسم الرئيسي:",
        reply_markup=b.as_markup(),
    )


@router.callback_query(F.data.startswith("admin:prods_cat:"))
async def products_cat_selected(
    callback: CallbackQuery, session
):
    cat_id = int(callback.data.split(":")[2])
    sub_cats = await DynamicService.get_all_sub_categories(
        session, cat_id
    )
    if not sub_cats:
        await callback.message.edit_text(
            "⚠️ لا توجد أقسام فرعية. أنشئ قسماً فرعياً أولاً.",
            reply_markup=admin_back_kb(),
        )
        return

    b = InlineKeyboardBuilder()
    for sub in sub_cats:
        b.button(
            text=f"{sub.emoji} {sub.name_ar}",
            callback_data=f"admin:prods:{sub.id}",
        )
    b.button(text="🔙 رجوع", callback_data="admin:products_menu")
    b.adjust(2)
    await callback.message.edit_text(
        "📦 اختر القسم الفرعي:",
        reply_markup=b.as_markup(),
    )


@router.callback_query(F.data.startswith("admin:prods:"))
async def products_list(callback: CallbackQuery, session):
    sub_id = int(callback.data.split(":")[2])
    sub = await DynamicService.get_sub_category(session, sub_id)
    if not sub:
        await callback.answer("⚠️ غير موجود.", show_alert=True)
        return

    products = await DynamicService.get_all_products(session, sub_id)
    await callback.message.edit_text(
        f"📦 <b>منتجات {sub.emoji} {sub.name_ar}</b>\n\n"
        "🟢 = مفعّل | ⚪ = معطّل",
        reply_markup=admin_products_list_kb(sub_id, products),
    )


# ══════════════ إضافة منتج ══════════════

@router.callback_query(F.data.startswith("admin:prod_add:"))
async def prod_add_start(
    callback: CallbackQuery, state: FSMContext
):
    sub_id = int(callback.data.split(":")[2])
    await state.update_data(prod_sub_id=sub_id)
    await callback.message.edit_text(
        "📝 أرسل اسم المنتج بالعربي:\n"
        "(مثال: 60 UC ببجي / 1000 متابع إنستا)",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(AdminProductStates.waiting_name)


@router.message(AdminProductStates.waiting_name)
async def prod_name_received(
    message: Message, state: FSMContext
):
    await state.update_data(prod_name=message.text.strip())
    await message.answer(
        "💰 أرسل سعر البيع بالدولار:\n"
        "(مثال: 1.50)"
    )
    await state.set_state(AdminProductStates.waiting_price)


@router.message(AdminProductStates.waiting_price)
async def prod_price_received(
    message: Message, state: FSMContext
):
    try:
        price = Decimal(message.text.strip())
        if price <= 0:
            raise InvalidOperation
    except InvalidOperation:
        await message.answer("⚠️ أرسل رقماً صحيحاً أكبر من صفر.")
        return

    await state.update_data(prod_price=str(price))
    await message.answer(
        "💵 أرسل سعر التكلفة بالدولار (سعرك عند المزود):\n"
        "(أو أرسل 0 إذا لا ينطبق)"
    )
    await state.set_state(AdminProductStates.waiting_cost_price)


@router.message(AdminProductStates.waiting_cost_price)
async def prod_cost_received(
    message: Message, state: FSMContext, session
):
    try:
        cost = Decimal(message.text.strip())
    except InvalidOperation:
        await message.answer("⚠️ أرسل رقماً صحيحاً.")
        return

    await state.update_data(prod_cost=str(cost))

    providers = await DynamicService.get_all_providers(session)
    if providers:
        b = InlineKeyboardBuilder()
        for p in providers:
            b.button(
                text=f"🔌 {p.name} ({p.type.value})",
                callback_data=f"admin:prod_provider:{p.id}",
            )
        b.button(
            text="⏭ بدون مزود (يدوي)",
            callback_data="admin:prod_provider:0",
        )
        b.adjust(1)
        await message.answer(
            "🔌 اختر المزود لهذا المنتج:",
            reply_markup=b.as_markup(),
        )
    else:
        await state.update_data(
            prod_provider_id=None,
            prod_provider_svc_id=None,
        )
        await _ask_product_type(message, state)


@router.callback_query(F.data.startswith("admin:prod_provider:"))
async def prod_provider_selected(
    callback: CallbackQuery, state: FSMContext
):
    provider_id = int(callback.data.split(":")[2])
    if provider_id == 0:
        await state.update_data(
            prod_provider_id=None,
            prod_provider_svc_id=None,
        )
        await _ask_product_type(callback.message, state)
        await callback.answer()
        return

    await state.update_data(prod_provider_id=provider_id)
    await callback.message.edit_text(
        "🔢 أرسل آيدي الخدمة عند المزود:\n"
        "(الرقم الذي يعرّف هذه الخدمة في لوحة المزود)"
    )
    await state.set_state(
        AdminProductStates.waiting_provider_service_id
    )
    await callback.answer()


@router.message(AdminProductStates.waiting_provider_service_id)
async def prod_svc_id_received(
    message: Message, state: FSMContext
):
    await state.update_data(
        prod_provider_svc_id=message.text.strip()
    )
    await _ask_product_type(message, state)


async def _ask_product_type(message: Message, state: FSMContext):
    b = InlineKeyboardBuilder()
    b.button(
        text="🎮 يحتاج Player ID",
        callback_data="admin:prod_req:player_id",
    )
    b.button(
        text="🔗 يحتاج رابط",
        callback_data="admin:prod_req:link",
    )
    b.button(
        text="🔗📊 يحتاج رابط + كمية",
        callback_data="admin:prod_req:link_qty",
    )
    b.button(
        text="📦 لا يحتاج إدخال",
        callback_data="admin:prod_req:none",
    )
    b.adjust(1)
    await message.answer(
        "ما الذي يحتاجه المستخدم لشراء هذا المنتج؟",
        reply_markup=b.as_markup(),
    )


@router.callback_query(F.data.startswith("admin:prod_req:"))
async def prod_requirements_selected(
    callback: CallbackQuery, state: FSMContext
):
    req = callback.data.split(":")[2]

    requires_player_id = req == "player_id"
    requires_link = req in ("link", "link_qty")
    requires_quantity = req == "link_qty"

    await state.update_data(
        requires_player_id=requires_player_id,
        requires_link=requires_link,
        requires_quantity=requires_quantity,
    )

    if requires_quantity:
        await callback.message.edit_text(
            "📊 أرسل الحد الأدنى للكمية:\n"
            "(مثال: 100)"
        )
        await state.set_state(
            AdminProductStates.waiting_min_quantity
        )
    else:
        await _save_product(callback.message, state, callback)

    await callback.answer()


@router.message(AdminProductStates.waiting_min_quantity)
async def prod_min_qty_received(
    message: Message, state: FSMContext
):
    try:
        min_qty = int(message.text.strip())
        if min_qty <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ أرسل رقماً صحيحاً أكبر من صفر.")
        return

    await state.update_data(min_quantity=min_qty)
    await message.answer(
        "📊 أرسل الحد الأقصى للكمية:\n"
        "(مثال: 10000)"
    )
    await state.set_state(
        AdminProductStates.waiting_max_quantity
    )


@router.message(AdminProductStates.waiting_max_quantity)
async def prod_max_qty_received(
    message: Message, state: FSMContext
):
    try:
        max_qty = int(message.text.strip())
        if max_qty <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ أرسل رقماً صحيحاً أكبر من صفر.")
        return

    await state.update_data(max_quantity=max_qty)
    await _save_product(message, state)


async def _save_product(
    message, state, callback=None
):
    from database.engine import async_session_maker
    data = await state.get_data()

    async with async_session_maker() as session:
        product = await DynamicService.create_product(
            session=session,
            sub_category_id=data["prod_sub_id"],
            name_ar=data["prod_name"],
            price_usd=Decimal(data["prod_price"]),
            cost_price_usd=Decimal(data.get("prod_cost", "0")),
            api_provider_id=data.get("prod_provider_id"),
            provider_service_id=data.get("prod_provider_svc_id"),
            requires_player_id=data.get("requires_player_id", False),
            requires_link=data.get("requires_link", False),
            requires_quantity=data.get("requires_quantity", False),
            min_quantity=data.get("min_quantity", 1),
            max_quantity=data.get("max_quantity", 1),
        )

    target = callback.message if callback else message
    await target.answer(
        f"✅ تم إنشاء المنتج: <b>{product.name_ar}</b>\n"
        f"💰 السعر: {product.price_usd}$"
    )
    await state.clear()


# ══════════════ تفاصيل المنتج ══════════════

@router.callback_query(F.data.startswith("admin:prod_view:"))
async def prod_view(callback: CallbackQuery, session):
    prod_id = int(callback.data.split(":")[2])
    product = await DynamicService.get_product(session, prod_id)
    if not product:
        await callback.answer("⚠️ غير موجود.", show_alert=True)
        return

    status = "🟢 مفعّل" if product.status.value == "active" else "⚪ معطّل"
    provider_name = "—"
    if product.api_provider:
        provider_name = product.api_provider.name

    reqs = []
    if product.requires_player_id:
        reqs.append("🎮 Player ID")
    if product.requires_link:
        reqs.append("🔗 رابط")
    if product.requires_quantity:
        reqs.append(
            f"📊 كمية ({product.min_quantity}-{product.max_quantity})"
        )
    req_text = " | ".join(reqs) if reqs else "📦 لا يحتاج إدخال"

    sub_cat = product.sub_category

    await callback.message.edit_text(
        f"📦 <b>{product.name_ar}</b>\n\n"
        f"الحالة: {status}\n"
        f"💰 سعر البيع: {product.price_usd}$\n"
        f"💵 سعر التكلفة: {product.cost_price_usd}$\n"
        f"📈 الربح: {product.price_usd - product.cost_price_usd}$\n"
        f"🔌 المزود: {provider_name}\n"
        f"🔢 آيدي الخدمة: {product.provider_service_id or '—'}\n"
        f"📥 متطلبات: {req_text}\n"
        f"🛒 إجمالي المبيعات: {product.total_sold}\n"
        f"🔢 الترتيب: {product.sort_order}",
        reply_markup=admin_product_detail_kb(
            product,
            sub_cat.id if sub_cat else 0,
        ),
    )


# ══════════════ تفعيل/تعطيل ══════════════

@router.callback_query(F.data.startswith("admin:prod_toggle:"))
async def prod_toggle(callback: CallbackQuery, session):
    prod_id = int(callback.data.split(":")[2])
    product = await DynamicService.get_product(session, prod_id)
    if not product:
        await callback.answer("⚠️ غير موجود.", show_alert=True)
        return

    new_status = (
        ProductStatus.INACTIVE
        if product.status == ProductStatus.ACTIVE
        else ProductStatus.ACTIVE
    )
    await DynamicService.update_product(
        session, prod_id, status=new_status
    )
    await callback.answer("✅ تم التحديث.")
    await prod_view(callback, session)


# ══════════════ تعديل السعر ══════════════

@router.callback_query(F.data.startswith("admin:prod_edit_price:"))
async def prod_edit_price_start(
    callback: CallbackQuery, state: FSMContext
):
    prod_id = int(callback.data.split(":")[2])
    await state.update_data(edit_prod_id=prod_id, edit_field="price")
    await callback.message.edit_text(
        "💰 أرسل السعر الجديد بالدولار:",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(AdminProductStates.waiting_edit_value)


# ══════════════ تعديل الاسم ══════════════

@router.callback_query(F.data.startswith("admin:prod_edit_name:"))
async def prod_edit_name_start(
    callback: CallbackQuery, state: FSMContext
):
    prod_id = int(callback.data.split(":")[2])
    await state.update_data(edit_prod_id=prod_id, edit_field="name")
    await callback.message.edit_text(
        "📝 أرسل الاسم الجديد:",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(AdminProductStates.waiting_edit_value)


# ══════════════ تعديل آيدي المزود ══════════════

@router.callback_query(F.data.startswith("admin:prod_edit_svc_id:"))
async def prod_edit_svc_id_start(
    callback: CallbackQuery, state: FSMContext
):
    prod_id = int(callback.data.split(":")[2])
    await state.update_data(edit_prod_id=prod_id, edit_field="svc_id")
    await callback.message.edit_text(
        "🔢 أرسل آيدي الخدمة الجديد عند المزود:",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(AdminProductStates.waiting_edit_value)


# ══════════════ معالج التعديل الموحد ══════════════

@router.message(AdminProductStates.waiting_edit_value)
async def prod_edit_received(
    message: Message, state: FSMContext, session
):
    data = await state.get_data()
    prod_id = data.get("edit_prod_id")
    field = data.get("edit_field")
    value = message.text.strip()

    if field == "price":
        try:
            price = Decimal(value)
            if price <= 0:
                raise InvalidOperation
        except InvalidOperation:
            await message.answer("⚠️ أرسل رقماً صحيحاً.")
            return
        await DynamicService.update_product(
            session, prod_id, price_usd=price
        )
    elif field == "name":
        await DynamicService.update_product(
            session, prod_id, name_ar=value
        )
    elif field == "svc_id":
        await DynamicService.update_product(
            session, prod_id, provider_service_id=value
        )

    await message.answer("✅ تم التحديث.")
    await state.clear()


# ══════════════ حذف المنتج ══════════════

@router.callback_query(F.data.startswith("admin:prod_delete:"))
async def prod_delete(callback: CallbackQuery, session):
    prod_id = int(callback.data.split(":")[2])
    product = await DynamicService.get_product(session, prod_id)
    if not product:
        await callback.answer("⚠️ غير موجود.", show_alert=True)
        return

    sub_id = product.sub_category_id
    await DynamicService.delete_product(session, prod_id)
    await callback.answer("🗑 تم حذف المنتج.")

    products = await DynamicService.get_all_products(session, sub_id)
    await callback.message.edit_text(
        "📦 <b>المنتجات</b>",
        reply_markup=admin_products_list_kb(sub_id, products),
    )
```

### `handlers/admin/providers.py`

```python
"""
عرض معلومات مزودي الأرقام المبرمجين مسبقاً.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select

from database.models import ProviderStatus
from services.settings_service import SettingsService
from keyboards.admin import admin_back_kb
from filters.admin_filter import IsAdmin

router = Router(name="admin_providers")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "admin:providers")
async def providers_info(callback: CallbackQuery, session):
    result = await session.execute(select(ProviderStatus))
    providers = result.scalars().all()

    threshold = await SettingsService.get_decimal(
        "provider_low_balance_threshold"
    )

    text = "🌐 <b>مزودو الأرقام</b>\n\n"
    for p in providers:
        status_emoji = "🟢" if p.is_online else "🔴"
        balance_text = (
            f"{p.balance}$"
            if p.balance is not None
            else "غير معروف"
        )

        low_warning = ""
        if (
            p.balance is not None
            and p.is_online
            and p.balance < threshold
        ):
            low_warning = " ⚠️ رصيد منخفض!"

        text += (
            f"{status_emoji} <b>{p.provider.value}</b>\n"
            f"💰 الرصيد: {balance_text}{low_warning}\n"
            f"🕐 آخر تحديث: "
            f"{p.last_checked_at.strftime('%Y-%m-%d %H:%M') if p.last_checked_at else '—'}\n"
        )
        if p.last_error:
            text += f"⚠️ آخر خطأ: {p.last_error[:100]}\n"
        text += "\n"

    text += f"🚨 حد التنبيه: {threshold}$"

    await callback.message.edit_text(
        text, reply_markup=admin_back_kb()
    )
```

### `handlers/admin/settings.py`

```python
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
```

### `handlers/admin/stars.py`

```python
"""
إدارة باقات نجوم تليجرام من لوحة الأدمن.
"""
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from services.dynamic_service import DynamicService
from states.states import AdminStarsStates
from keyboards.admin import (
    admin_stars_kb, admin_star_detail_kb,
    admin_back_kb,
)
from filters.admin_filter import IsAdmin

router = Router(name="admin_stars")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# ══════════════ قائمة الباقات ══════════════

@router.callback_query(F.data == "admin:stars")
async def stars_list(callback: CallbackQuery, session):
    packages = await DynamicService.get_all_stars_packages(session)
    await callback.message.edit_text(
        "⭐ <b>إدارة باقات نجوم تليجرام</b>\n\n"
        "🟢 = مفعّلة | ⚪ = معطّلة\n\n"
        "هذه الباقات تظهر للمستخدم عند اختيار شحن بالنجوم.",
        reply_markup=admin_stars_kb(packages),
    )


# ══════════════ إضافة باقة ══════════════

@router.callback_query(F.data == "admin:star_add")
async def star_add_start(
    callback: CallbackQuery, state: FSMContext
):
    await callback.message.edit_text(
        "➕ <b>إضافة باقة نجوم جديدة</b>\n\n"
        "أرسل عدد النجوم:\n"
        "(مثال: 100)",
        reply_markup=admin_back_kb(),
    )
    await state.set_state(AdminStarsStates.waiting_stars_amount)


@router.message(AdminStarsStates.waiting_stars_amount)
async def star_amount_received(
    message: Message, state: FSMContext
):
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "⚠️ أرسل رقماً صحيحاً أكبر من صفر."
        )
        return

    await state.update_data(star_amount=amount)
    await message.answer(
        "💰 أرسل المبلغ بالدولار الذي سيُضاف للرصيد "
        "عند شراء هذه الباقة:\n"
        "(مثال: 1.30)"
    )
    await state.set_state(AdminStarsStates.waiting_usd_amount)


@router.message(AdminStarsStates.waiting_usd_amount)
async def star_usd_received(
    message: Message, state: FSMContext
):
    try:
        usd = Decimal(message.text.strip())
        if usd <= 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        await message.answer(
            "⚠️ أرسل رقماً صحيحاً أكبر من صفر."
        )
        return

    await state.update_data(star_usd=str(usd))
    data = await state.get_data()
    default_label = f"⭐ {data['star_amount']} نجمة"

    await message.answer(
        f"📝 أرسل عنوان الباقة:\n"
        f"(أو أرسل - لاستخدام: {default_label})"
    )
    await state.set_state(AdminStarsStates.waiting_label)


@router.message(AdminStarsStates.waiting_label)
async def star_label_received(
    message: Message, state: FSMContext, session
):
    data = await state.get_data()
    label = message.text.strip()
    if label == "-":
        label = f"⭐ {data['star_amount']} نجمة"

    package = await DynamicService.create_stars_package(
        session=session,
        stars_amount=data["star_amount"],
        usd_amount=Decimal(data["star_usd"]),
        label=label,
    )

    await message.answer(
        f"✅ تم إنشاء الباقة بنجاح!\n\n"
        f"⭐ النجوم: {package.stars_amount}\n"
        f"💰 المبلغ: {package.usd_amount}$\n"
        f"📝 العنوان: {package.label}"
    )
    await state.clear()


# ══════════════ تفاصيل الباقة ══════════════

@router.callback_query(F.data.startswith("admin:star_view:"))
async def star_view(callback: CallbackQuery, session):
    pkg_id = int(callback.data.split(":")[2])
    package = await DynamicService.get_stars_package(
        session, pkg_id
    )
    if not package:
        await callback.answer(
            "⚠️ الباقة غير موجودة.", show_alert=True
        )
        return

    status = "🟢 مفعّلة" if package.is_active else "⚪ معطّلة"
    await callback.message.edit_text(
        f"⭐ <b>{package.label}</b>\n\n"
        f"عدد النجوم: {package.stars_amount}\n"
        f"المبلغ: {package.usd_amount}$\n"
        f"الحالة: {status}\n"
        f"الترتيب: {package.sort_order}\n"
        f"تاريخ الإنشاء: "
        f"{package.created_at.strftime('%Y-%m-%d')}",
        reply_markup=admin_star_detail_kb(package),
    )


# ══════════════ تفعيل/تعطيل ══════════════

@router.callback_query(F.data.startswith("admin:star_toggle:"))
async def star_toggle(callback: CallbackQuery, session):
    pkg_id = int(callback.data.split(":")[2])
    package = await DynamicService.get_stars_package(
        session, pkg_id
    )
    if not package:
        await callback.answer(
            "⚠️ الباقة غير موجودة.", show_alert=True
        )
        return

    await DynamicService.update_stars_package(
        session, pkg_id, is_active=not package.is_active
    )
    await callback.answer("✅ تم التحديث.")
    await star_view(callback, session)


# ══════════════ حذف الباقة ══════════════

@router.callback_query(F.data.startswith("admin:star_delete:"))
async def star_delete(callback: CallbackQuery, session):
    pkg_id = int(callback.data.split(":")[2])
    success = await DynamicService.delete_stars_package(
        session, pkg_id
    )
    if success:
        await callback.answer("🗑 تم حذف الباقة.")
    else:
        await callback.answer(
            "⚠️ الباقة غير موجودة.", show_alert=True
        )
    await stars_list(callback, session)
```

### `handlers/admin/stats.py`

```python
"""
إحصائيات البوت الشاملة.
"""
from datetime import datetime, timedelta
from decimal import Decimal

from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select, func

from database.models import (
    User, DepositRequest, DepositStatus,
    NumberOrder, UnifiedOrder,
    OrderStatus, UnifiedOrderStatus,
    Transaction, TransactionType,
)
from keyboards.admin import admin_back_kb
from filters.admin_filter import IsAdmin

router = Router(name="admin_stats")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "admin:stats")
async def stats_handler(callback: CallbackQuery, session):
    now = datetime.utcnow()
    today_start = now.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    # ── المستخدمون ──
    total_users = (await session.execute(
        select(func.count(User.id))
    )).scalar_one()

    new_users_today = (await session.execute(
        select(func.count(User.id)).where(
            User.joined_at >= today_start
        )
    )).scalar_one()

    new_users_week = (await session.execute(
        select(func.count(User.id)).where(
            User.joined_at >= week_start
        )
    )).scalar_one()

    banned_users = (await session.execute(
        select(func.count(User.id)).where(
            User.is_banned == True
        )
    )).scalar_one()

    # ── الإيداعات ──
    today_deposits = (await session.execute(
        select(
            func.coalesce(
                func.sum(DepositRequest.amount_usd), 0
            )
        ).where(
            DepositRequest.status == DepositStatus.APPROVED,
            DepositRequest.processed_at >= today_start,
        )
    )).scalar_one()
    today_deposits = Decimal(str(today_deposits))

    week_deposits = (await session.execute(
        select(
            func.coalesce(
                func.sum(DepositRequest.amount_usd), 0
            )
        ).where(
            DepositRequest.status == DepositStatus.APPROVED,
            DepositRequest.processed_at >= week_start,
        )
    )).scalar_one()
    week_deposits = Decimal(str(week_deposits))

    month_deposits = (await session.execute(
        select(
            func.coalesce(
                func.sum(DepositRequest.amount_usd), 0
            )
        ).where(
            DepositRequest.status == DepositStatus.APPROVED,
            DepositRequest.processed_at >= month_start,
        )
    )).scalar_one()
    month_deposits = Decimal(str(month_deposits))

    pending_deposits = (await session.execute(
        select(func.count(DepositRequest.id)).where(
            DepositRequest.status == DepositStatus.PENDING
        )
    )).scalar_one()

    # ── طلبات الأرقام ──
    today_num_sales = (await session.execute(
        select(func.count(NumberOrder.id)).where(
            NumberOrder.status == OrderStatus.COMPLETED,
            NumberOrder.purchased_at >= today_start,
        )
    )).scalar_one()

    total_num_sales = (await session.execute(
        select(func.count(NumberOrder.id)).where(
            NumberOrder.status == OrderStatus.COMPLETED
        )
    )).scalar_one()

    num_revenue = (await session.execute(
        select(
            func.coalesce(
                func.sum(NumberOrder.price_sell_usd), 0
            )
        ).where(
            NumberOrder.status == OrderStatus.COMPLETED,
            NumberOrder.purchased_at >= month_start,
        )
    )).scalar_one()
    num_revenue = Decimal(str(num_revenue))

    num_cost = (await session.execute(
        select(
            func.coalesce(
                func.sum(NumberOrder.price_provider_usd), 0
            )
        ).where(
            NumberOrder.status == OrderStatus.COMPLETED,
            NumberOrder.purchased_at >= month_start,
        )
    )).scalar_one()
    num_cost = Decimal(str(num_cost))

    # ── طلبات موحدة (ألعاب/تطبيقات/SMM) ──
    today_uni_sales = (await session.execute(
        select(func.count(UnifiedOrder.id)).where(
            UnifiedOrder.status == UnifiedOrderStatus.COMPLETED,
            UnifiedOrder.created_at >= today_start,
        )
    )).scalar_one()

    total_uni_sales = (await session.execute(
        select(func.count(UnifiedOrder.id)).where(
            UnifiedOrder.status == UnifiedOrderStatus.COMPLETED
        )
    )).scalar_one()

    uni_revenue = (await session.execute(
        select(
            func.coalesce(
                func.sum(UnifiedOrder.price_usd), 0
            )
        ).where(
            UnifiedOrder.status == UnifiedOrderStatus.COMPLETED,
            UnifiedOrder.created_at >= month_start,
        )
    )).scalar_one()
    uni_revenue = Decimal(str(uni_revenue))

    uni_cost = (await session.execute(
        select(
            func.coalesce(
                func.sum(UnifiedOrder.cost_price_usd), 0
            )
        ).where(
            UnifiedOrder.status == UnifiedOrderStatus.COMPLETED,
            UnifiedOrder.created_at >= month_start,
        )
    )).scalar_one()
    uni_cost = Decimal(str(uni_cost))

    # ── الأرباح الصافية ──
    total_revenue = num_revenue + uni_revenue
    total_cost = num_cost + uni_cost
    net_profit = total_revenue - total_cost

    # ── إجمالي أرصدة المستخدمين ──
    total_balances = (await session.execute(
        select(
            func.coalesce(func.sum(User.balance), 0)
        )
    )).scalar_one()
    total_balances = Decimal(str(total_balances))

    await callback.message.edit_text(
        "📊 <b>إحصائيات البوت</b>\n\n"
        "━━━ 👥 المستخدمون ━━━\n"
        f"الإجمالي: {total_users}\n"
        f"جدد اليوم: {new_users_today}\n"
        f"جدد هذا الأسبوع: {new_users_week}\n"
        f"محظورون: {banned_users}\n\n"
        "━━━ 💰 الإيداعات ━━━\n"
        f"اليوم: {today_deposits:.2f}$\n"
        f"الأسبوع: {week_deposits:.2f}$\n"
        f"الشهر: {month_deposits:.2f}$\n"
        f"⏳ معلّقة: {pending_deposits}\n\n"
        "━━━ 📞 طلبات الأرقام ━━━\n"
        f"اليوم: {today_num_sales}\n"
        f"الإجمالي: {total_num_sales}\n\n"
        "━━━ 🛒 طلبات أخرى (ألعاب/SMM) ━━━\n"
        f"اليوم: {today_uni_sales}\n"
        f"الإجمالي: {total_uni_sales}\n\n"
        "━━━ 💵 الأرباح (آخر 30 يوم) ━━━\n"
        f"إجمالي المبيعات: {total_revenue:.2f}$\n"
        f"إجمالي التكاليف: {total_cost:.2f}$\n"
        f"صافي الأرباح: <b>{net_profit:.2f}$</b>\n\n"
        "━━━ 💳 أرصدة المستخدمين ━━━\n"
        f"إجمالي الأرصدة: {total_balances:.2f}$",
        reply_markup=admin_back_kb(),
    )
```

### `handlers/admin/users.py`

```python
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
```

### `keyboards/__init__.py`

```python

```

### `keyboards/admin.py`

```python
"""
كل أزرار لوحة الأدمن.
"""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ══════════════ اللوحة الرئيسية ══════════════

def admin_main_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📊 إحصائيات البوت", callback_data="admin:stats")
    b.button(text="📂 إدارة الأقسام", callback_data="admin:categories")
    b.button(text="📦 إدارة المنتجات", callback_data="admin:products_menu")
    b.button(text="📞 إدارة خدمات الأرقام", callback_data="admin:number_services")
    b.button(text="🌍 إدارة الدول", callback_data="admin:countries")
    b.button(text="🔌 مزودو الألعاب/SMM", callback_data="admin:api_providers")
    b.button(text="🌐 مزودو الأرقام", callback_data="admin:providers")
    b.button(text="💵 تعديل الأسعار", callback_data="admin:pricing")
    b.button(text="⭐ إدارة باقات النجوم", callback_data="admin:stars")
    b.button(text="🎟 إدارة الكوبونات", callback_data="admin:coupons")
    b.button(text="👥 إدارة المستخدمين", callback_data="admin:users")
    b.button(text="👨‍💼 إدارة الأدمنية", callback_data="admin:multi_admin")
    b.button(text="📌 الاشتراك الإجباري", callback_data="admin:channels")
    b.button(text="📢 إذاعة جماعية", callback_data="admin:broadcast")
    b.button(text="🔧 وضع الصيانة", callback_data="admin:maintenance")
    b.button(text="⚙️ الإعدادات العامة", callback_data="admin:settings")
    b.adjust(2, 2, 2, 2, 2, 2, 2, 2)
    return b.as_markup()


def admin_back_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔙 رجوع للوحة الرئيسية", callback_data="admin:main")
    return b.as_markup()


# ══════════════ الصيانة ══════════════

def admin_maintenance_kb(is_active: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if is_active:
        b.button(text="🟢 إيقاف الصيانة", callback_data="admin:maintenance_off")
    else:
        b.button(text="🔴 تفعيل الصيانة", callback_data="admin:maintenance_on")
    b.button(text="📝 تعديل رسالة الصيانة", callback_data="admin:maintenance_msg")
    b.button(text="🔙 رجوع", callback_data="admin:main")
    b.adjust(1)
    return b.as_markup()


# ══════════════ الأقسام ══════════════

def admin_categories_list_kb(categories) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for cat in categories:
        status = "🟢" if cat.is_active else "⚪"
        b.button(
            text=f"{status} {cat.emoji} {cat.name_ar}",
            callback_data=f"admin:cat_view:{cat.id}",
        )
    b.button(text="➕ إضافة قسم جديد", callback_data="admin:cat_add")
    b.button(text="🔙 رجوع", callback_data="admin:main")
    b.adjust(1)
    return b.as_markup()


def admin_category_detail_kb(category) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if category.is_active:
        b.button(text="⚪ تعطيل", callback_data=f"admin:cat_toggle:{category.id}")
    else:
        b.button(text="🟢 تفعيل", callback_data=f"admin:cat_toggle:{category.id}")
    b.button(text="📝 تعديل الاسم", callback_data=f"admin:cat_edit_name:{category.id}")
    b.button(text="🔢 تعديل الترتيب", callback_data=f"admin:cat_edit_sort:{category.id}")
    b.button(text="📂 الأقسام الفرعية", callback_data=f"admin:subcats:{category.id}")
    b.button(text="🗑 حذف", callback_data=f"admin:cat_delete:{category.id}")
    b.button(text="🔙 رجوع", callback_data="admin:categories")
    b.adjust(1)
    return b.as_markup()


# ══════════════ الأقسام الفرعية ══════════════

def admin_subcats_list_kb(category_id: int, sub_categories) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for sub in sub_categories:
        status = "🟢" if sub.is_active else "⚪"
        b.button(
            text=f"{status} {sub.emoji} {sub.name_ar}",
            callback_data=f"admin:subcat_view:{sub.id}",
        )
    b.button(text="➕ إضافة قسم فرعي", callback_data=f"admin:subcat_add:{category_id}")
    b.button(text="🔙 رجوع", callback_data=f"admin:cat_view:{category_id}")
    b.adjust(1)
    return b.as_markup()


def admin_subcat_detail_kb(sub_category, category_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if sub_category.is_active:
        b.button(text="⚪ تعطيل", callback_data=f"admin:subcat_toggle:{sub_category.id}")
    else:
        b.button(text="🟢 تفعيل", callback_data=f"admin:subcat_toggle:{sub_category.id}")
    b.button(text="📝 تعديل الاسم", callback_data=f"admin:subcat_edit_name:{sub_category.id}")
    b.button(text="📦 المنتجات", callback_data=f"admin:prods:{sub_category.id}")
    b.button(text="🗑 حذف", callback_data=f"admin:subcat_delete:{sub_category.id}")
    b.button(text="🔙 رجوع", callback_data=f"admin:subcats:{category_id}")
    b.adjust(1)
    return b.as_markup()


# ══════════════ المنتجات ══════════════

def admin_products_list_kb(sub_category_id: int, products) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for p in products:
        status = "🟢" if p.status.value == "active" else "⚪"
        b.button(
            text=f"{status} {p.name_ar} ({p.price_usd}$)",
            callback_data=f"admin:prod_view:{p.id}",
        )
    b.button(text="➕ إضافة منتج", callback_data=f"admin:prod_add:{sub_category_id}")
    b.button(text="🔙 رجوع", callback_data=f"admin:subcat_view:{sub_category_id}")
    b.adjust(1)
    return b.as_markup()


def admin_product_detail_kb(product, sub_category_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    is_active = product.status.value == "active"
    if is_active:
        b.button(text="⚪ تعطيل", callback_data=f"admin:prod_toggle:{product.id}")
    else:
        b.button(text="🟢 تفعيل", callback_data=f"admin:prod_toggle:{product.id}")
    b.button(text="💰 تعديل السعر", callback_data=f"admin:prod_edit_price:{product.id}")
    b.button(text="📝 تعديل الاسم", callback_data=f"admin:prod_edit_name:{product.id}")
    b.button(text="🔌 تعديل آيدي المزود", callback_data=f"admin:prod_edit_svc_id:{product.id}")
    b.button(text="🗑 حذف", callback_data=f"admin:prod_delete:{product.id}")
    b.button(text="🔙 رجوع", callback_data=f"admin:prods:{sub_category_id}")
    b.adjust(1)
    return b.as_markup()


# ══════════════ مزودو API ══════════════

def admin_api_providers_kb(providers) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for p in providers:
        status = "🟢" if p.is_active else "🔴"
        b.button(
            text=f"{status} {p.name} ({p.type.value})",
            callback_data=f"admin:aprov_view:{p.id}",
        )
    b.button(text="➕ إضافة مزود", callback_data="admin:aprov_add")
    b.button(text="🔙 رجوع", callback_data="admin:main")
    b.adjust(1)
    return b.as_markup()


def admin_api_provider_detail_kb(provider) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if provider.is_active:
        b.button(text="🔴 تعطيل", callback_data=f"admin:aprov_toggle:{provider.id}")
    else:
        b.button(text="🟢 تفعيل", callback_data=f"admin:aprov_toggle:{provider.id}")
    b.button(text="💰 فحص الرصيد", callback_data=f"admin:aprov_balance:{provider.id}")
    b.button(text="📝 تعديل الاسم", callback_data=f"admin:aprov_edit_name:{provider.id}")
    b.button(text="🔑 تعديل API Key", callback_data=f"admin:aprov_edit_key:{provider.id}")
    b.button(text="🗑 حذف", callback_data=f"admin:aprov_delete:{provider.id}")
    b.button(text="🔙 رجوع", callback_data="admin:api_providers")
    b.adjust(1)
    return b.as_markup()


# ══════════════ باقات النجوم ══════════════

def admin_stars_kb(packages) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for pkg in packages:
        status = "🟢" if pkg.is_active else "⚪"
        b.button(
            text=f"{status} {pkg.label} = {pkg.usd_amount}$",
            callback_data=f"admin:star_view:{pkg.id}",
        )
    b.button(text="➕ إضافة باقة", callback_data="admin:star_add")
    b.button(text="🔙 رجوع", callback_data="admin:main")
    b.adjust(1)
    return b.as_markup()


def admin_star_detail_kb(package) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if package.is_active:
        b.button(text="⚪ تعطيل", callback_data=f"admin:star_toggle:{package.id}")
    else:
        b.button(text="🟢 تفعيل", callback_data=f"admin:star_toggle:{package.id}")
    b.button(text="🗑 حذف", callback_data=f"admin:star_delete:{package.id}")
    b.button(text="🔙 رجوع", callback_data="admin:stars")
    b.adjust(1)
    return b.as_markup()


# ══════════════ الكوبونات ══════════════

def admin_coupons_kb(coupons) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for c in coupons:
        status = "🟢" if c.is_active else "⚪"
        b.button(
            text=f"{status} {c.code} ({c.used_count}/{c.max_uses})",
            callback_data=f"admin:coupon_view:{c.id}",
        )
    b.button(text="➕ إنشاء كوبون", callback_data="admin:coupon_add")
    b.button(text="🔙 رجوع", callback_data="admin:main")
    b.adjust(1)
    return b.as_markup()


def admin_coupon_detail_kb(coupon) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if coupon.is_active:
        b.button(text="⚪ تعطيل", callback_data=f"admin:coupon_toggle:{coupon.id}")
    else:
        b.button(text="🟢 تفعيل", callback_data=f"admin:coupon_toggle:{coupon.id}")
    b.button(text="🗑 حذف", callback_data=f"admin:coupon_delete:{coupon.id}")
    b.button(text="🔙 رجوع", callback_data="admin:coupons")
    b.adjust(1)
    return b.as_markup()


# ══════════════ الأدمنية ══════════════

def admin_multi_admin_kb(admins) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for admin in admins:
        b.button(
            text=f"👤 {admin.full_name or admin.telegram_id} (@{admin.username or '-'})",
            callback_data=f"admin:madmin_view:{admin.id}",
        )
    b.button(text="➕ إضافة أدمن", callback_data="admin:madmin_add")
    b.button(text="🔙 رجوع", callback_data="admin:main")
    b.adjust(1)
    return b.as_markup()


def admin_madmin_detail_kb(admin_user, is_primary: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if not is_primary:
        b.button(text="🗑 إزالة الأدمنية", callback_data=f"admin:madmin_remove:{admin_user.id}")
    b.button(text="🔙 رجوع", callback_data="admin:multi_admin")
    b.adjust(1)
    return b.as_markup()


# ══════════════ خدمات الأرقام ══════════════

def admin_number_services_kb(services) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for svc in services:
        status = "🟢" if svc.is_active else "⚪"
        b.button(
            text=f"{status} {svc.emoji} {svc.name_ar}",
            callback_data=f"admin:nsvc_view:{svc.id}",
        )
    b.button(text="➕ إضافة خدمة أرقام", callback_data="admin:nsvc_add")
    b.button(text="🔙 رجوع", callback_data="admin:main")
    b.adjust(1)
    return b.as_markup()


def admin_nsvc_detail_kb(service) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if service.is_active:
        b.button(text="⚪ تعطيل", callback_data=f"admin:nsvc_toggle:{service.id}")
    else:
        b.button(text="🟢 تفعيل", callback_data=f"admin:nsvc_toggle:{service.id}")
    b.button(text="📝 تعديل الاسم", callback_data=f"admin:nsvc_edit_name:{service.id}")
    b.button(text="🗑 حذف", callback_data=f"admin:nsvc_delete:{service.id}")
    b.button(text="🔙 رجوع", callback_data="admin:number_services")
    b.adjust(1)
    return b.as_markup()


# ══════════════ الدول ══════════════

def admin_countries_kb(countries) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for c in countries:
        status_icon = "🟢" if c.is_active else "⚪"
        b.button(
            text=f"{status_icon} {c.flag} {c.name_ar}",
            callback_data=f"admin:country_view:{c.id}",
        )
    b.button(text="➕ إضافة دولة جديدة", callback_data="admin:country_add")
    b.button(text="📋 أكواد 5sim المرجعية", callback_data="admin:country_reference_list")
    b.button(text="🔙 رجوع", callback_data="admin:main")
    b.adjust(2, 1, 1)
    return b.as_markup()


def admin_country_detail_kb(country) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if country.is_active:
        b.button(text="⚪ تعطيل", callback_data=f"admin:country_toggle:{country.id}")
    else:
        b.button(text="🟢 تفعيل", callback_data=f"admin:country_toggle:{country.id}")
    b.button(text="🗑 حذف", callback_data=f"admin:country_delete:{country.id}")
    b.button(text="🔙 رجوع", callback_data="admin:countries")
    b.adjust(1)
    return b.as_markup()


# ══════════════ الأسعار ══════════════

def admin_pricing_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📈 تعديل نسبة الربح العامة", callback_data="admin:set_margin")
    b.button(text="🔙 رجوع", callback_data="admin:main")
    b.adjust(1)
    return b.as_markup()


# ══════════════ الإعدادات ══════════════

def admin_settings_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🛠 يوزر الدعم", callback_data="admin:set_support")
    b.button(text="💳 طريقة الدفع", callback_data="admin:set_payment")
    b.button(text="🚨 حد التحويل الكبير", callback_data="admin:set_large_tx")
    b.button(text="⏳ مهلة انتظار الكود", callback_data="admin:set_order_timeout")
    b.button(text="📝 رسالة الترحيب", callback_data="admin:set_welcome")
    b.button(text="💰 نسبة الكاشباك", callback_data="admin:set_cashback")
    b.button(text="💎 نسبة الإحالة", callback_data="admin:set_referral_percent")
    b.button(text="⏱ Rate Limit", callback_data="admin:set_rate_limit")
    b.button(text="📢 قناة الإشعارات العامة", callback_data="admin:set_public_channel")
    b.button(text="💾 قناة البكاب", callback_data="admin:set_backup_channel")
    b.button(text="🔙 رجوع", callback_data="admin:main")
    b.adjust(2, 2, 2, 2, 2, 1)
    return b.as_markup()


# ══════════════ الإيداعات ══════════════

def deposit_decision_kb(deposit_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ قبول", callback_data=f"deposit_accept:{deposit_id}")
    b.button(text="❌ رفض", callback_data=f"deposit_reject:{deposit_id}")
    b.adjust(2)
    return b.as_markup()


# ══════════════ إدارة مستخدم ══════════════

def user_manage_kb(user_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➕ إضافة رصيد", callback_data=f"admin:user_add_balance:{user_id}")
    b.button(text="➖ خصم رصيد", callback_data=f"admin:user_deduct_balance:{user_id}")
    b.button(text="📋 سجل المعاملات", callback_data=f"admin:user_transactions:{user_id}")
    b.button(text="📩 إرسال رسالة", callback_data=f"admin:user_send_msg:{user_id}")
    if is_banned:
        b.button(text="✅ فك الحظر", callback_data=f"admin:user_unban:{user_id}")
    else:
        b.button(text="🚫 حظر", callback_data=f"admin:user_ban:{user_id}")
    b.button(text="🔙 رجوع", callback_data="admin:users")
    b.adjust(2, 2, 1, 1)
    return b.as_markup()


# ══════════════ القنوات ══════════════

def admin_channels_kb(channels) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for ch in channels:
        b.button(
            text=f"❌ حذف: {ch.title or ch.chat_id}",
            callback_data=f"admin:channel_del:{ch.id}",
        )
    b.button(text="➕ إضافة قناة", callback_data="admin:channel_add")
    b.button(text="🔙 رجوع", callback_data="admin:main")
    b.adjust(1)
    return b.as_markup()
```

### `keyboards/admin_categories_v2.py`

```python
"""
كل أزرار إدارة الأقسام الرئيسية والفرعية.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import Category, SubCategory, CategoryType


# ══════════════ قائمة الأقسام الرئيسية ══════════════

def categories_list_kb(
    categories: list[Category],
) -> InlineKeyboardMarkup:
    """قائمة كل الأقسام الرئيسية."""
    b = InlineKeyboardBuilder()

    for cat in categories:
        status_icon = "🟢" if cat.is_active else "🔴"
        subs_count = len(cat.sub_categories) if cat.sub_categories else 0
        b.button(
            text=(
                f"{status_icon} {cat.emoji} "
                f"{cat.name_ar} ({subs_count})"
            ),
            callback_data=f"admin:cat_view:{cat.id}",
        )

    b.button(
        text="➕ إضافة قسم رئيسي",
        callback_data="admin:cat_add",
    )
    b.button(
        text="🔙 رجوع",
        callback_data="admin:main",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ اختيار نوع القسم ══════════════

def select_category_type_kb() -> InlineKeyboardMarkup:
    """اختيار نوع القسم (SMM/Games/Apps)."""
    b = InlineKeyboardBuilder()

    b.button(
        text="📈 رشق سوشيال ميديا",
        callback_data=f"admin:cat_type:{CategoryType.SMM.value}",
    )
    b.button(
        text="🎮 شحن ألعاب",
        callback_data=f"admin:cat_type:{CategoryType.GAMES.value}",
    )
    b.button(
        text="📱 تطبيقات دردشة",
        callback_data=f"admin:cat_type:{CategoryType.APPS.value}",
    )
    b.button(
        text="🔙 رجوع",
        callback_data="admin:categories",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ اختيار الإيموجي ══════════════

COMMON_EMOJIS_SMM = [
    "📸", "📷", "📱", "🎵", "▶️",
    "👤", "🐦", "💬", "👻", "🔵",
    "🎮", "📈", "❤️", "👁", "👥",
]

COMMON_EMOJIS_GAMES = [
    "🎮", "🔫", "🔥", "⚔️", "🧱",
    "👑", "🏰", "🌟", "🏎", "⚽",
    "🎯", "🎲", "🎰", "🕹", "🎳",
]

COMMON_EMOJIS_APPS = [
    "📱", "💬", "🎵", "💎", "💜",
    "💛", "🌐", "💚", "🎁", "☎️",
    "📞", "📢", "🔔", "🎤", "🎧",
]


def select_emoji_kb(
    category_type: str = "smm",
) -> InlineKeyboardMarkup:
    """اختيار إيموجي للقسم."""
    b = InlineKeyboardBuilder()

    emojis_map = {
        "smm": COMMON_EMOJIS_SMM,
        "games": COMMON_EMOJIS_GAMES,
        "apps": COMMON_EMOJIS_APPS,
    }
    emojis = emojis_map.get(category_type, COMMON_EMOJIS_SMM)

    for emoji in emojis:
        b.button(
            text=emoji,
            callback_data=f"admin:cat_emoji:{emoji}",
        )

    b.button(
        text="✏️ إيموجي مخصص",
        callback_data="admin:cat_emoji:custom",
    )
    b.button(
        text="⏭ تخطي (استخدام افتراضي)",
        callback_data="admin:cat_emoji:default",
    )
    b.button(
        text="❌ إلغاء",
        callback_data="admin:categories",
    )

    b.adjust(5, 5, 5, 1, 1, 1)
    return b.as_markup()


# ══════════════ تفاصيل القسم الرئيسي ══════════════

def category_detail_kb(
    category: Category,
) -> InlineKeyboardMarkup:
    """أزرار تفاصيل القسم الرئيسي."""
    b = InlineKeyboardBuilder()

    if category.is_active:
        b.button(
            text="🔴 تعطيل القسم",
            callback_data=f"admin:cat_toggle:{category.id}",
        )
    else:
        b.button(
            text="🟢 تفعيل القسم",
            callback_data=f"admin:cat_toggle:{category.id}",
        )

    b.button(
        text="📂 عرض الأقسام الفرعية",
        callback_data=f"admin:subcat_list:{category.id}",
    )
    b.button(
        text="➕ إضافة قسم فرعي",
        callback_data=f"admin:subcat_add:{category.id}",
    )

    b.button(
        text="✏️ تعديل الاسم",
        callback_data=f"admin:cat_edit:name:{category.id}",
    )
    b.button(
        text="🎨 تعديل الإيموجي",
        callback_data=f"admin:cat_edit:emoji:{category.id}",
    )
    b.button(
        text="🔢 تعديل الترتيب",
        callback_data=f"admin:cat_edit:sort:{category.id}",
    )

    b.button(
        text="🗑 حذف القسم",
        callback_data=f"admin:cat_delete_confirm:{category.id}",
    )
    b.button(
        text="🔙 رجوع لقائمة الأقسام",
        callback_data="admin:categories",
    )

    b.adjust(1, 2, 3, 1, 1)
    return b.as_markup()


# ══════════════ تأكيد حذف قسم ══════════════

def confirm_delete_category_kb(
    category_id: int,
    subs_count: int,
) -> InlineKeyboardMarkup:
    """تأكيد حذف قسم رئيسي."""
    b = InlineKeyboardBuilder()

    b.button(
        text="⚠️ نعم، احذف نهائياً",
        callback_data=f"admin:cat_delete:{category_id}",
    )
    b.button(
        text="🔙 لا، إلغاء",
        callback_data=f"admin:cat_view:{category_id}",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ قائمة الأقسام الفرعية ══════════════

def sub_categories_list_kb(
    category_id: int,
    sub_categories: list[SubCategory],
) -> InlineKeyboardMarkup:
    """قائمة الأقسام الفرعية لقسم رئيسي."""
    b = InlineKeyboardBuilder()

    for sub in sub_categories:
        status_icon = "🟢" if sub.is_active else "🔴"
        products_count = len(sub.products) if sub.products else 0
        b.button(
            text=(
                f"{status_icon} {sub.emoji} "
                f"{sub.name_ar} ({products_count} منتج)"
            ),
            callback_data=f"admin:subcat_view:{sub.id}",
        )

    b.button(
        text="➕ إضافة قسم فرعي",
        callback_data=f"admin:subcat_add:{category_id}",
    )
    b.button(
        text="🔙 رجوع للقسم الرئيسي",
        callback_data=f"admin:cat_view:{category_id}",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ تفاصيل القسم الفرعي ══════════════

def sub_category_detail_kb(
    sub_category: SubCategory,
) -> InlineKeyboardMarkup:
    """أزرار تفاصيل القسم الفرعي."""
    b = InlineKeyboardBuilder()

    if sub_category.is_active:
        b.button(
            text="🔴 تعطيل القسم الفرعي",
            callback_data=(
                f"admin:subcat_toggle:{sub_category.id}"
            ),
        )
    else:
        b.button(
            text="🟢 تفعيل القسم الفرعي",
            callback_data=(
                f"admin:subcat_toggle:{sub_category.id}"
            ),
        )

    b.button(
        text="📦 عرض المنتجات",
        callback_data=(
            f"admin:prod_list:{sub_category.id}"
        ),
    )
    b.button(
        text="➕ إضافة منتج جديد",
        callback_data=(
            f"admin:prod_wizard_start:{sub_category.id}"
        ),
    )

    b.button(
        text="✏️ تعديل الاسم",
        callback_data=(
            f"admin:subcat_edit:name:{sub_category.id}"
        ),
    )
    b.button(
        text="🎨 تعديل الإيموجي",
        callback_data=(
            f"admin:subcat_edit:emoji:{sub_category.id}"
        ),
    )
    b.button(
        text="📝 تعديل الوصف",
        callback_data=(
            f"admin:subcat_edit:desc:{sub_category.id}"
        ),
    )
    b.button(
        text="🖼 تعديل الصورة",
        callback_data=(
            f"admin:subcat_edit:image:{sub_category.id}"
        ),
    )
    b.button(
        text="🔢 تعديل الترتيب",
        callback_data=(
            f"admin:subcat_edit:sort:{sub_category.id}"
        ),
    )

    b.button(
        text="🗑 حذف القسم الفرعي",
        callback_data=(
            f"admin:subcat_delete_confirm:{sub_category.id}"
        ),
    )
    b.button(
        text="🔙 رجوع لقائمة الأقسام الفرعية",
        callback_data=(
            f"admin:subcat_list:{sub_category.category_id}"
        ),
    )

    b.adjust(1, 2, 2, 2, 1, 1)
    return b.as_markup()


# ══════════════ تأكيد حذف قسم فرعي ══════════════

def confirm_delete_sub_category_kb(
    sub_category_id: int,
    category_id: int,
    products_count: int,
) -> InlineKeyboardMarkup:
    """تأكيد حذف قسم فرعي."""
    b = InlineKeyboardBuilder()

    b.button(
        text="⚠️ نعم، احذف نهائياً",
        callback_data=(
            f"admin:subcat_delete:{sub_category_id}"
        ),
    )
    b.button(
        text="🔙 لا، إلغاء",
        callback_data=(
            f"admin:subcat_view:{sub_category_id}"
        ),
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ خيارات إضافة صورة ══════════════

def image_options_kb(
    context: str = "subcat",
    entity_id: int = 0,
) -> InlineKeyboardMarkup:
    """خيارات إضافة صورة (رفع / رابط / تخطي)."""
    b = InlineKeyboardBuilder()

    b.button(
        text="📤 رفع صورة",
        callback_data=f"admin:{context}_img:upload:{entity_id}",
    )
    b.button(
        text="🔗 إدخال رابط صورة",
        callback_data=f"admin:{context}_img:url:{entity_id}",
    )
    b.button(
        text="⏭ تخطي (بدون صورة)",
        callback_data=f"admin:{context}_img:skip:{entity_id}",
    )
    b.button(
        text="❌ إلغاء",
        callback_data=f"admin:subcat_list:{entity_id}",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ إلغاء عمليات ══════════════

def cancel_add_kb(back_to: str) -> InlineKeyboardMarkup:
    """زر إلغاء عام أثناء الإدخال."""
    b = InlineKeyboardBuilder()
    b.button(
        text="❌ إلغاء",
        callback_data=back_to,
    )
    return b.as_markup()
```

### `keyboards/admin_products_v2.py`

```python
"""
كل أزرار إدارة المنتجات.
"""
from decimal import Decimal

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
```

### `keyboards/admin_products_wizard.py`

```python
"""
كل أزرار Wizard إنشاء منتج جديد.

يدعم مسارين:
1) إنشاء سريع (افتراضيات ذكية)
2) إنشاء مخصص (كل الخيارات)
"""
from decimal import Decimal

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import (
    ApiProvider,
    ProviderService,
    ProductPricingType,
    ProductDisplayType,
)


# ══════════════ اختيار وضع الإنشاء ══════════════

def creation_mode_kb(
    sub_category_id: int,
) -> InlineKeyboardMarkup:
    """
    اختيار وضع إنشاء المنتج.
    - سريع: افتراضيات ذكية (اسم من الخدمة، ربح 50%)
    - مخصص: كل الخيارات (وصف، صورة، تسعير، عرض)
    - يدوي: بدون ربط مزود
    """
    b = InlineKeyboardBuilder()

    b.button(
        text="⚡ إنشاء سريع (افتراضيات ذكية)",
        callback_data=(
            f"admin:pw_mode:quick:{sub_category_id}"
        ),
    )
    b.button(
        text="🛠 إنشاء مخصص (كل الخيارات)",
        callback_data=(
            f"admin:pw_mode:custom:{sub_category_id}"
        ),
    )
    b.button(
        text="✋ إنشاء يدوي (بدون مزود)",
        callback_data=(
            f"admin:pw_mode:manual:{sub_category_id}"
        ),
    )
    b.button(
        text="🔙 رجوع",
        callback_data=f"admin:subcat_view:{sub_category_id}",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ اختيار المزود ══════════════

def select_provider_kb(
    providers: list[ApiProvider],
    sub_category_id: int,
) -> InlineKeyboardMarkup:
    """اختيار المزود لإنشاء منتج من خدماته."""
    b = InlineKeyboardBuilder()

    for p in providers:
        if not p.is_active:
            continue

        services_count = p.total_services or 0
        b.button(
            text=(
                f"🔌 {p.name} "
                f"({services_count} خدمة)"
            ),
            callback_data=f"admin:pw_prov:{p.id}",
        )

    b.button(
        text="🔙 رجوع",
        callback_data=(
            f"admin:prod_wizard_start:{sub_category_id}"
        ),
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ خيارات تصفح خدمات المزود ══════════════

def browse_services_options_kb(
    provider_id: int,
) -> InlineKeyboardMarkup:
    """خيارات تصفح خدمات المزود."""
    b = InlineKeyboardBuilder()

    b.button(
        text="📋 عرض كل الخدمات",
        callback_data=(
            f"admin:pw_svc_page:{provider_id}:0"
        ),
    )
    b.button(
        text="🔍 البحث في الخدمات",
        callback_data=(
            f"admin:pw_svc_search:{provider_id}"
        ),
    )
    b.button(
        text="📂 تصفية بالتصنيف",
        callback_data=(
            f"admin:pw_svc_cats:{provider_id}"
        ),
    )
    b.button(
        text="🔙 رجوع",
        callback_data="admin:pw_back_to_providers",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ اختيار تصنيف ══════════════

def select_category_filter_kb(
    provider_id: int,
    categories: list[tuple[str, int]],
    current_page: int = 0,
) -> InlineKeyboardMarkup:
    """اختيار تصنيف من تصنيفات المزود."""
    b = InlineKeyboardBuilder()

    CATS_PER_PAGE = 10
    start = current_page * CATS_PER_PAGE
    end = start + CATS_PER_PAGE
    page_cats = categories[start:end]
    total_pages = max(
        1,
        (len(categories) + CATS_PER_PAGE - 1) // CATS_PER_PAGE,
    )

    for cat_name, count in page_cats:
        display = cat_name
        if len(display) > 35:
            display = display[:32] + "..."
        b.button(
            text=f"📁 {display} ({count})",
            callback_data=(
                f"admin:pw_svc_cat:{provider_id}:"
                f"{hash(cat_name) % 1000000}"
            ),
        )

    nav_count = 0
    if current_page > 0:
        b.button(
            text="◀️ السابق",
            callback_data=(
                f"admin:pw_cats_page:{provider_id}:"
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
                f"admin:pw_cats_page:{provider_id}:"
                f"{current_page + 1}"
            ),
        )
        nav_count += 1

    b.button(
        text="🔙 رجوع",
        callback_data=(
            f"admin:pw_svc_options:{provider_id}"
        ),
    )

    rows = [1] * len(page_cats)
    if nav_count > 0:
        rows.append(nav_count)
    rows.append(1)
    b.adjust(*rows)
    return b.as_markup()


# ══════════════ عرض الخدمات مع Pagination ══════════════

SERVICES_WIZARD_PER_PAGE = 6


def wizard_services_kb(
    provider_id: int,
    services: list[ProviderService],
    current_page: int,
    total_count: int,
    search_query: str | None = None,
    category_filter: str | None = None,
) -> InlineKeyboardMarkup:
    """قائمة خدمات المزود لاختيار واحدة لإنشاء منتج."""
    b = InlineKeyboardBuilder()

    for svc in services:
        display_name = svc.name
        if len(display_name) > 45:
            display_name = display_name[:42] + "..."

        b.button(
            text=(
                f"#{svc.external_service_id} - "
                f"{display_name} - {svc.rate_usd:.4f}$"
            ),
            callback_data=f"admin:pw_pick:{svc.id}",
        )

    total_pages = max(
        1,
        (total_count + SERVICES_WIZARD_PER_PAGE - 1)
        // SERVICES_WIZARD_PER_PAGE,
    )

    nav_count = 0

    if current_page > 0:
        if search_query:
            cb = (
                f"admin:pw_search_page:{provider_id}:"
                f"{current_page - 1}"
            )
        elif category_filter:
            cb = (
                f"admin:pw_cat_page:{provider_id}:"
                f"{current_page - 1}"
            )
        else:
            cb = (
                f"admin:pw_svc_page:{provider_id}:"
                f"{current_page - 1}"
            )
        b.button(text="◀️ السابق", callback_data=cb)
        nav_count += 1

    b.button(
        text=f"📄 {current_page + 1}/{total_pages}",
        callback_data="noop",
    )
    nav_count += 1

    if current_page < total_pages - 1:
        if search_query:
            cb = (
                f"admin:pw_search_page:{provider_id}:"
                f"{current_page + 1}"
            )
        elif category_filter:
            cb = (
                f"admin:pw_cat_page:{provider_id}:"
                f"{current_page + 1}"
            )
        else:
            cb = (
                f"admin:pw_svc_page:{provider_id}:"
                f"{current_page + 1}"
            )
        b.button(text="التالي ▶️", callback_data=cb)
        nav_count += 1

    b.button(
        text="🔍 بحث جديد",
        callback_data=(
            f"admin:pw_svc_search:{provider_id}"
        ),
    )
    b.button(
        text="🔙 رجوع لخيارات التصفح",
        callback_data=(
            f"admin:pw_svc_options:{provider_id}"
        ),
    )

    rows = [1] * len(services)
    rows.append(nav_count)
    rows.append(1)
    rows.append(1)
    b.adjust(*rows)
    return b.as_markup()


# ══════════════ تأكيد اختيار خدمة ══════════════

def confirm_service_selection_kb(
    service_id: int,
    provider_id: int,
) -> InlineKeyboardMarkup:
    """تأكيد اختيار الخدمة قبل بدء الـ Wizard."""
    b = InlineKeyboardBuilder()

    b.button(
        text="✅ نعم، أنشئ منتج من هذه الخدمة",
        callback_data=f"admin:pw_confirm:{service_id}",
    )
    b.button(
        text="🔙 اختيار خدمة أخرى",
        callback_data=(
            f"admin:pw_svc_page:{provider_id}:0"
        ),
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ خيارات الصورة ══════════════

def wizard_image_options_kb() -> InlineKeyboardMarkup:
    """خيارات إضافة صورة للمنتج."""
    b = InlineKeyboardBuilder()

    b.button(
        text="📤 رفع صورة",
        callback_data="admin:pw_img:upload",
    )
    b.button(
        text="🔗 إدخال رابط صورة",
        callback_data="admin:pw_img:url",
    )
    b.button(
        text="⏭ بدون صورة",
        callback_data="admin:pw_img:skip",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ اختيار نوع التسعير ══════════════

def select_pricing_type_kb() -> InlineKeyboardMarkup:
    """اختيار نوع التسعير."""
    b = InlineKeyboardBuilder()

    b.button(
        text="💰 نسبة ربح % (موصى به)",
        callback_data="admin:pw_pricing:margin",
    )
    b.button(
        text="💵 سعر ثابت",
        callback_data="admin:pw_pricing:fixed",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ اختيار طريقة عرض السعر ══════════════

def select_wizard_display_type_kb(
    supports_quantity: bool = True,
) -> InlineKeyboardMarkup:
    """اختيار طريقة عرض السعر للمستخدم."""
    b = InlineKeyboardBuilder()

    if supports_quantity:
        b.button(
            text="📊 السعر لكل 1000 (SMM)",
            callback_data="admin:pw_display:per_1000",
        )
        b.button(
            text="📦 السعر للحد الأدنى",
            callback_data="admin:pw_display:per_min",
        )

    b.button(
        text="💵 سعر ثابت للطلب (ألعاب)",
        callback_data="admin:pw_display:fixed",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ استخدام حدود المزود أو تخصيص ══════════════

def quantity_limits_kb() -> InlineKeyboardMarkup:
    """استخدام حدود المزود أو تخصيصها."""
    b = InlineKeyboardBuilder()

    b.button(
        text="✅ استخدام حدود المزود",
        callback_data="admin:pw_qty:use_provider",
    )
    b.button(
        text="✏️ تعديل الحدود",
        callback_data="admin:pw_qty:customize",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ تأكيد إنشاء المنتج النهائي ══════════════

def confirm_creation_kb() -> InlineKeyboardMarkup:
    """تأكيد نهائي قبل إنشاء المنتج."""
    b = InlineKeyboardBuilder()

    b.button(
        text="✅ نعم، أنشئ المنتج الآن",
        callback_data="admin:pw_create_final",
    )
    b.button(
        text="❌ إلغاء (لن يُحفظ شيء)",
        callback_data="admin:pw_cancel",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ تخطي حقل ══════════════

def skip_field_kb(field_name: str) -> InlineKeyboardMarkup:
    """زر تخطي حقل اختياري."""
    b = InlineKeyboardBuilder()

    b.button(
        text="⏭ تخطي",
        callback_data=f"admin:pw_skip:{field_name}",
    )
    b.button(
        text="❌ إلغاء الـ Wizard",
        callback_data="admin:pw_cancel",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ زر إلغاء الـ Wizard ══════════════

def cancel_wizard_kb() -> InlineKeyboardMarkup:
    """زر إلغاء الـ Wizard في أي مرحلة."""
    b = InlineKeyboardBuilder()

    b.button(
        text="❌ إلغاء الـ Wizard",
        callback_data="admin:pw_cancel",
    )
    return b.as_markup()


# ══════════════ خيارات "منتج يدوي" ══════════════

def manual_product_requires_kb() -> InlineKeyboardMarkup:
    """
    في المنتج اليدوي: اختيار ما يحتاجه المستخدم.
    """
    b = InlineKeyboardBuilder()

    b.button(
        text="🎮 يحتاج آيدي لاعب",
        callback_data="admin:pw_manual_req:player_id",
    )
    b.button(
        text="🔗 يحتاج رابط",
        callback_data="admin:pw_manual_req:link",
    )
    b.button(
        text="📊 يحتاج كمية",
        callback_data="admin:pw_manual_req:quantity",
    )
    b.button(
        text="📦 لا يحتاج شيء (منتج ثابت)",
        callback_data="admin:pw_manual_req:none",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ بعد نجاح الإنشاء ══════════════

def after_creation_kb(
    product_id: int,
    sub_category_id: int,
) -> InlineKeyboardMarkup:
    """أزرار بعد نجاح إنشاء المنتج."""
    b = InlineKeyboardBuilder()

    b.button(
        text="👁 عرض المنتج",
        callback_data=f"admin:prod_view:{product_id}",
    )
    b.button(
        text="➕ إضافة منتج آخر",
        callback_data=(
            f"admin:prod_wizard_start:{sub_category_id}"
        ),
    )
    b.button(
        text="📦 عرض كل المنتجات",
        callback_data=f"admin:prod_list:{sub_category_id}",
    )
    b.button(
        text="🔙 رجوع للقسم الفرعي",
        callback_data=f"admin:subcat_view:{sub_category_id}",
    )
    b.adjust(1)
    return b.as_markup()
```

### `keyboards/admin_providers_v2.py`

```python
"""
كل أزرار إدارة المزودين (V2 - محسّنة).
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import (
    ApiProvider,
    ApiProtocolType,
    ApiProviderType,
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
        text="🎮 Games (شحن ألعاب) - قياسي ⏳",
        callback_data="admin:aprov_proto:games_generic",
    )
    b.button(
        text="🛠 Custom (مخصص) - متقدم ⏳",
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
            f"🔙 رجوع لخدمات المزود"
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
```

### `keyboards/common.py`

```python
"""
أزرار مشتركة تُستخدم في أكثر من مكان.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def check_subscription_kb(
    channels,
    check_cb: str = "check_subscription",
) -> InlineKeyboardMarkup:
    """أزرار الاشتراك الإجباري."""
    builder = InlineKeyboardBuilder()
    for ch in channels:
        link = (
            ch.username_or_link
            or f"https://t.me/c/{str(ch.chat_id).replace('-100', '')}"
        )
        builder.row(InlineKeyboardButton(
            text=f"📢 {ch.title or 'قناة'}",
            url=link,
        ))
    builder.row(InlineKeyboardButton(
        text="✅ تحقق من الاشتراك",
        callback_data=check_cb,
    ))
    return builder.as_markup()


def yes_no_kb(
    yes_data: str,
    no_data: str,
) -> InlineKeyboardMarkup:
    """زر نعم / لا عام."""
    b = InlineKeyboardBuilder()
    b.button(text="✅ نعم", callback_data=yes_data)
    b.button(text="❌ لا", callback_data=no_data)
    b.adjust(2)
    return b.as_markup()


def cancel_kb(
    cancel_data: str = "back_to_main",
) -> InlineKeyboardMarkup:
    """زر إلغاء فقط."""
    b = InlineKeyboardBuilder()
    b.button(text="❌ إلغاء", callback_data=cancel_data)
    return b.as_markup()


def pagination_kb(
    base_callback: str,
    current_page: int,
    total_pages: int,
    back_callback: str = "back_to_main",
) -> InlineKeyboardMarkup:
    """أزرار تنقل بين الصفحات."""
    b = InlineKeyboardBuilder()
    if current_page > 0:
        b.button(
            text="◀️ السابق",
            callback_data=f"{base_callback}:{current_page - 1}",
        )
    b.button(
        text=f"📄 {current_page + 1}/{total_pages}",
        callback_data="noop",
    )
    if current_page < total_pages - 1:
        b.button(
            text="التالي ▶️",
            callback_data=f"{base_callback}:{current_page + 1}",
        )
    b.button(text="🔙 رجوع", callback_data=back_callback)
    if total_pages > 1:
        b.adjust(3, 1)
    else:
        b.adjust(1, 1)
    return b.as_markup()
```

### `keyboards/deposit_methods.py`

```python
"""
كل أزرار طرق الدفع الست.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ══════════════ القائمة الرئيسية لطرق الدفع ══════════════

def deposit_methods_kb(
    shamcash_manual_enabled: bool = True,
    stars_enabled: bool = True,
    usdt_manual_enabled: bool = True,
    shamcash_auto_enabled: bool = True,
    usdt_auto_enabled: bool = True,
    other_enabled: bool = True,
) -> InlineKeyboardMarkup:
    """
    قائمة طرق الشحن (حتى 6 أزرار).
    الأزرار تظهر فقط إذا كانت مفعلة من لوحة الأدمن.
    """
    b = InlineKeyboardBuilder()

    if shamcash_manual_enabled:
        b.button(
            text="💵 شام كاش يدوي",
            callback_data="deposit:shamcash_manual",
        )

    if stars_enabled:
        b.button(
            text="⭐ نجوم تليجرام",
            callback_data="deposit:stars",
        )

    if shamcash_auto_enabled:
        b.button(
            text="💳 شام كاش تلقائي",
            callback_data="deposit:shamcash_auto",
        )

    if usdt_auto_enabled:
        b.button(
            text="₮ USDT تلقائي",
            callback_data="deposit:usdt_auto",
        )

    if usdt_manual_enabled:
        b.button(
            text="₮ USDT يدوي",
            callback_data="deposit:usdt_manual",
        )

    if other_enabled:
        b.button(
            text="📞 طرق دفع أخرى",
            callback_data="deposit:other",
        )

    b.button(
        text="🔙 رجوع للقائمة الرئيسية",
        callback_data="back_to_main",
    )

    b.adjust(2, 2, 2, 1)
    return b.as_markup()


# ══════════════ زر البدء بعد الشرح ══════════════

def start_deposit_kb(method: str) -> InlineKeyboardMarkup:
    """يظهر بعد شرح الطريقة، للانتقال لإدخال المبلغ."""
    b = InlineKeyboardBuilder()
    b.button(
        text="✅ ابدأ الشحن",
        callback_data=f"deposit_start:{method}",
    )
    b.button(
        text="🔙 رجوع",
        callback_data="menu:deposit",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ اختيار شبكة USDT ══════════════

def usdt_networks_kb(mode: str) -> InlineKeyboardMarkup:
    """
    قائمة اختيار شبكة USDT.
    mode: "manual" أو "auto"
    """
    b = InlineKeyboardBuilder()

    if mode == "manual":
        b.button(
            text="🟢 TRC20 (الأرخص)",
            callback_data="usdt_net:manual:TRC20",
        )
        b.button(
            text="🔵 ERC20",
            callback_data="usdt_net:manual:ERC20",
        )
        b.button(
            text="🟡 BEP20",
            callback_data="usdt_net:manual:BEP20",
        )
    else:
        b.button(
            text="🟢 TRC20 (موصى به)",
            callback_data="usdt_net:auto:TRC20",
        )

    b.button(
        text="🔙 رجوع",
        callback_data="menu:deposit",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ اختيار عملة شام كاش تلقائي ══════════════

def shamcash_currency_kb() -> InlineKeyboardMarkup:
    """اختيار عملة الدفع (USD أو SYP) للفاتورة التلقائية."""
    b = InlineKeyboardBuilder()
    b.button(
        text="💵 دولار (USD)",
        callback_data="shamcash_curr:USD",
    )
    b.button(
        text="🇸🇾 ليرة سورية (SYP)",
        callback_data="shamcash_curr:SYP",
    )
    b.button(
        text="🔙 رجوع",
        callback_data="menu:deposit",
    )
    b.adjust(2, 1)
    return b.as_markup()


# ══════════════ أزرار الفاتورة التلقائية - شام كاش ══════════════

def shamcash_invoice_kb(
    invoice_id: int,
    payment_url: str | None = None,
) -> InlineKeyboardMarkup:
    """
    أزرار الفاتورة التلقائية لشام كاش.
    تعرض:
    - زر إدخال رقم العملية
    - رابط صفحة الدفع (اختياري)
    - إلغاء
    """
    b = InlineKeyboardBuilder()
    b.button(
        text="✅ أدخلت رقم العملية",
        callback_data=f"sc_verify:{invoice_id}",
    )

    if payment_url:
        b.row(InlineKeyboardButton(
            text="🌐 فتح صفحة الدفع",
            url=payment_url,
        ))

    b.button(
        text="❌ إلغاء الفاتورة",
        callback_data=f"sc_cancel:{invoice_id}",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ أزرار الفاتورة التلقائية - USDT ══════════════

def usdt_auto_invoice_kb(
    invoice_id: int,
    payment_url: str | None = None,
) -> InlineKeyboardMarkup:
    """
    أزرار الفاتورة التلقائية لـ USDT.
    """
    b = InlineKeyboardBuilder()
    b.button(
        text="🔄 تحقق الآن",
        callback_data=f"usdt_check:{invoice_id}",
    )

    if payment_url:
        b.row(InlineKeyboardButton(
            text="🌐 فتح صفحة الدفع",
            url=payment_url,
        ))

    b.button(
        text="❌ إلغاء الفاتورة",
        callback_data=f"usdt_cancel:{invoice_id}",
    )
    b.adjust(1)
    return b.as_markup()


# ══════════════ زر إلغاء عام ══════════════

def cancel_deposit_kb() -> InlineKeyboardMarkup:
    """زر إلغاء عملية الشحن."""
    b = InlineKeyboardBuilder()
    b.button(
        text="❌ إلغاء",
        callback_data="menu:deposit",
    )
    return b.as_markup()
```

### `keyboards/games.py`

```python
"""
أزرار شحن الألعاب والتطبيقات.
تُبنى ديناميكياً من قاعدة البيانات.
"""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import SubCategory, Product


def sub_categories_kb(
    category_id: int,
    sub_categories: list[SubCategory],
) -> InlineKeyboardMarkup:
    """قائمة الأقسام الفرعية لقسم رئيسي."""
    b = InlineKeyboardBuilder()
    for sub in sub_categories:
        b.button(
            text=f"{sub.emoji} {sub.name_ar}",
            callback_data=f"subcat:{sub.id}",
        )
    b.button(
        text="🔙 رجوع للقائمة",
        callback_data="back_to_main",
    )
    b.adjust(2)
    return b.as_markup()


def products_kb(
    sub_category_id: int,
    products: list[Product],
    category_id: int,
) -> InlineKeyboardMarkup:
    """قائمة المنتجات مع الأسعار بالدولار."""
    b = InlineKeyboardBuilder()
    for p in products:
        b.button(
            text=f"{p.name_ar} - {p.price_usd}$",
            callback_data=f"prod:{p.id}",
        )
    b.button(
        text="🔙 رجوع",
        callback_data=f"cat:{category_id}",
    )
    b.adjust(1)
    return b.as_markup()


def product_confirm_kb(
    product_id: int,
    sub_category_id: int,
) -> InlineKeyboardMarkup:
    """تأكيد شراء منتج."""
    b = InlineKeyboardBuilder()
    b.button(
        text="✅ تأكيد الشراء",
        callback_data=f"prod_confirm:{product_id}",
    )
    b.button(
        text="🎟 لدي كوبون خصم",
        callback_data=f"prod_coupon:{product_id}",
    )
    b.button(
        text="🔙 رجوع",
        callback_data=f"subcat:{sub_category_id}",
    )
    b.adjust(1)
    return b.as_markup()


def product_confirm_with_coupon_kb(
    product_id: int,
    sub_category_id: int,
    coupon_code: str,
    discount_usd: str,
) -> InlineKeyboardMarkup:
    """تأكيد شراء منتج بعد تطبيق كوبون."""
    b = InlineKeyboardBuilder()
    b.button(
        text=f"✅ تأكيد الشراء (خصم {discount_usd}$)",
        callback_data=(
            f"prod_confirm_coupon:{product_id}:{coupon_code}"
        ),
    )
    b.button(
        text="🔙 رجوع",
        callback_data=f"subcat:{sub_category_id}",
    )
    b.adjust(1)
    return b.as_markup()
```

### `keyboards/main_menu.py`

```python
"""
القائمة الرئيسية الديناميكية.
تُبنى تلقائياً من:
1) خدمات الأرقام المفعلة (جدول number_services)
2) الأقسام المفعلة (جدول categories)
3) أزرار ثابتة (شحن رصيد، حسابي، إلخ)
"""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import NumberService, Category


def build_main_menu(
    number_services: list[NumberService],
    categories: list[Category],
    balance_usd: str = "0.00",
) -> InlineKeyboardMarkup:
    """
    يبني القائمة الرئيسية ديناميكياً.
    number_services: خدمات الأرقام المفعلة من DB
    categories: الأقسام الرئيسية المفعلة من DB
    balance_usd: رصيد المستخدم لعرضه
    """
    b = InlineKeyboardBuilder()

    # ── خدمات الأرقام الديناميكية ──
    for svc in number_services:
        b.button(
            text=f"{svc.emoji} أرقام {svc.name_ar}",
            callback_data=f"num_svc:{svc.code}",
        )

    # ── الأقسام الرئيسية الديناميكية ──
    for cat in categories:
        b.button(
            text=f"{cat.emoji} {cat.name_ar}",
            callback_data=f"cat:{cat.id}",
        )

    # ── أزرار ثابتة ──
    b.button(
        text="💰 شحن الرصيد",
        callback_data="menu:deposit",
    )
    b.button(
        text=f"👤 حسابي ({balance_usd}$)",
        callback_data="menu:account",
    )
    b.button(
        text="💎 دعوة أصدقاء",
        callback_data="menu:referral",
    )
    b.button(
        text="🔄 تحويل رصيد",
        callback_data="menu:transfer",
    )
    b.button(
        text="🛠 الدعم الفني",
        callback_data="menu:support",
    )

    # ── ترتيب الأزرار ──
    num_svc_count = len(number_services)
    cat_count = len(categories)

    rows = []
    if num_svc_count > 0:
        rows.append(min(num_svc_count, 2))
        if num_svc_count > 2:
            rows.append(min(num_svc_count - 2, 2))
    if cat_count > 0:
        remaining = cat_count
        while remaining > 0:
            rows.append(min(remaining, 2))
            remaining -= 2

    rows.extend([2, 2, 2, 1])
    b.adjust(*rows)

    return b.as_markup()


def deposit_menu_kb(
    shamcash_manual_enabled: bool = True,
    stars_enabled: bool = True,
    usdt_manual_enabled: bool = True,
    shamcash_auto_enabled: bool = True,
    usdt_auto_enabled: bool = True,
    other_enabled: bool = True,
) -> InlineKeyboardMarkup:
    """
    قائمة طرق شحن الرصيد (6 طرق).
    كل طريقة تظهر فقط إذا كانت مفعلة من لوحة الأدمن.
    """
    b = InlineKeyboardBuilder()

    if shamcash_manual_enabled:
        b.button(
            text="💵 شام كاش يدوي",
            callback_data="deposit:shamcash_manual",
        )

    if stars_enabled:
        b.button(
            text="⭐ نجوم تليجرام",
            callback_data="deposit:stars",
        )

    if shamcash_auto_enabled:
        b.button(
            text="💳 شام كاش تلقائي",
            callback_data="deposit:shamcash_auto",
        )

    if usdt_auto_enabled:
        b.button(
            text="₮ USDT تلقائي",
            callback_data="deposit:usdt_auto",
        )

    if usdt_manual_enabled:
        b.button(
            text="₮ USDT يدوي",
            callback_data="deposit:usdt_manual",
        )

    if other_enabled:
        b.button(
            text="📞 طرق دفع أخرى",
            callback_data="deposit:other",
        )

    b.button(
        text="🔙 رجوع للقائمة الرئيسية",
        callback_data="back_to_main",
    )

    b.adjust(2, 2, 2, 1)
    return b.as_markup()


def stars_packages_kb(
    packages: list,
) -> InlineKeyboardMarkup:
    """قائمة باقات النجوم المتاحة."""
    b = InlineKeyboardBuilder()
    for pkg in packages:
        b.button(
            text=f"{pkg.label} = {pkg.usd_amount}$",
            callback_data=f"stars_buy:{pkg.id}",
        )
    b.button(
        text="🔙 رجوع",
        callback_data="menu:deposit",
    )
    b.adjust(2)
    return b.as_markup()


def insufficient_balance_kb() -> InlineKeyboardMarkup:
    """زر شحن الرصيد عند عدم كفاية الرصيد."""
    b = InlineKeyboardBuilder()
    b.button(
        text="💰 شحن رصيد الآن",
        callback_data="menu:deposit",
    )
    b.button(
        text="🔙 رجوع للقائمة",
        callback_data="back_to_main",
    )
    b.adjust(1)
    return b.as_markup()


def confirm_large_order_kb(
    confirm_data: str,
) -> InlineKeyboardMarkup:
    """تأكيد الطلبات الكبيرة."""
    b = InlineKeyboardBuilder()
    b.button(
        text="✅ نعم، متأكد",
        callback_data=confirm_data,
    )
    b.button(
        text="❌ إلغاء",
        callback_data="back_to_main",
    )
    b.adjust(2)
    return b.as_markup()


def back_to_main_kb() -> InlineKeyboardMarkup:
    """زر رجوع للقائمة الرئيسية فقط."""
    b = InlineKeyboardBuilder()
    b.button(
        text="🔙 رجوع للقائمة الرئيسية",
        callback_data="back_to_main",
    )
    return b.as_markup()
```

### `keyboards/numbers.py`

```python
"""
أزرار خدمة الأرقام.
تعمل مع النظام الديناميكي بالكامل.
"""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import Country, NumberService

COUNTRIES_PER_PAGE = 12


def number_services_kb(
    services: list[NumberService],
) -> InlineKeyboardMarkup:
    """قائمة خدمات الأرقام الديناميكية."""
    b = InlineKeyboardBuilder()
    for svc in services:
        b.button(
            text=f"{svc.emoji} أرقام {svc.name_ar}",
            callback_data=f"num_svc:{svc.code}",
        )
    b.button(
        text="🔙 رجوع للقائمة",
        callback_data="back_to_main",
    )
    b.adjust(2)
    return b.as_markup()


def countries_kb(
    service_code: str,
    countries: list[Country],
    page: int = 0,
) -> InlineKeyboardMarkup:
    """
    قائمة الدول مع Pagination.
    تعرض COUNTRIES_PER_PAGE دولة في كل صفحة.
    """
    b = InlineKeyboardBuilder()

    start = page * COUNTRIES_PER_PAGE
    end = start + COUNTRIES_PER_PAGE
    page_countries = countries[start:end]
    total_pages = (
        (len(countries) + COUNTRIES_PER_PAGE - 1)
        // COUNTRIES_PER_PAGE
    )

    for c in page_countries:
        b.button(
            text=f"{c.flag} {c.name_ar}",
            callback_data=(
                f"num_country:{service_code}:{c.code}"
            ),
        )

    # ── أزرار التنقل ──
    nav_buttons = []
    if page > 0:
        b.button(
            text="◀️ السابق",
            callback_data=(
                f"num_page:{service_code}:{page - 1}"
            ),
        )
        nav_buttons.append(1)
    if page < total_pages - 1:
        b.button(
            text="التالي ▶️",
            callback_data=(
                f"num_page:{service_code}:{page + 1}"
            ),
        )
        nav_buttons.append(1)

    b.button(
        text="🔙 رجوع",
        callback_data="back_to_main",
    )

    rows = [2] * (len(page_countries) // 2)
    if len(page_countries) % 2:
        rows.append(1)
    if nav_buttons:
        rows.append(len(nav_buttons))
    rows.append(1)

    b.adjust(*rows)
    return b.as_markup()


def confirm_purchase_kb(
    service_code: str,
    country_code: str,
) -> InlineKeyboardMarkup:
    """تأكيد شراء رقم مع عرض السعر."""
    b = InlineKeyboardBuilder()
    b.button(
        text="✅ تأكيد الشراء",
        callback_data=(
            f"num_confirm:{service_code}:{country_code}"
        ),
    )
    b.button(
        text="❌ إلغاء",
        callback_data="back_to_main",
    )
    b.adjust(1)
    return b.as_markup()


def order_actions_kb(order_id: int) -> InlineKeyboardMarkup:
    """أزرار أثناء انتظار الكود."""
    b = InlineKeyboardBuilder()
    b.button(
        text="🔄 تحديث",
        callback_data=f"num_refresh:{order_id}",
    )
    b.button(
        text="❌ إلغاء واسترجاع الرصيد",
        callback_data=f"num_cancel:{order_id}",
    )
    b.adjust(1)
    return b.as_markup()


def code_received_kb(
    order_id: int,
) -> InlineKeyboardMarkup:
    """تظهر بعد استلام الكود."""
    b = InlineKeyboardBuilder()
    b.button(
        text="🔄 انتظار كود إضافي",
        callback_data=f"num_extra:{order_id}",
    )
    b.button(
        text="✅ انتهيت",
        callback_data=f"num_finish:{order_id}",
    )
    b.adjust(1)
    return b.as_markup()
```

### `keyboards/smm.py`

```python
"""
أزرار رشق السوشيال ميديا.
تُبنى ديناميكياً من قاعدة البيانات.
نفس بنية أزرار الألعاب لأنها تعتمد على نفس النظام
(categories → sub_categories → products).
"""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import SubCategory, Product


def smm_platforms_kb(
    category_id: int,
    sub_categories: list[SubCategory],
) -> InlineKeyboardMarkup:
    """قائمة منصات السوشيال ميديا."""
    b = InlineKeyboardBuilder()
    for sub in sub_categories:
        b.button(
            text=f"{sub.emoji} {sub.name_ar}",
            callback_data=f"subcat:{sub.id}",
        )
    b.button(
        text="🔙 رجوع للقائمة",
        callback_data="back_to_main",
    )
    b.adjust(2)
    return b.as_markup()


def smm_services_kb(
    sub_category_id: int,
    products: list[Product],
    category_id: int,
) -> InlineKeyboardMarkup:
    """قائمة خدمات الرشق مع الأسعار والكميات."""
    b = InlineKeyboardBuilder()
    for p in products:
        if p.requires_quantity:
            price_text = f"{p.price_usd}$ / {p.min_quantity}"
            b.button(
                text=f"{p.name_ar} - {price_text}",
                callback_data=f"prod:{p.id}",
            )
        else:
            b.button(
                text=f"{p.name_ar} - {p.price_usd}$",
                callback_data=f"prod:{p.id}",
            )
    b.button(
        text="🔙 رجوع",
        callback_data=f"cat:{category_id}",
    )
    b.adjust(1)
    return b.as_markup()


def smm_confirm_kb(
    product_id: int,
    sub_category_id: int,
) -> InlineKeyboardMarkup:
    """تأكيد طلب رشق."""
    b = InlineKeyboardBuilder()
    b.button(
        text="✅ تأكيد الطلب",
        callback_data=f"prod_confirm:{product_id}",
    )
    b.button(
        text="🎟 لدي كوبون خصم",
        callback_data=f"prod_coupon:{product_id}",
    )
    b.button(
        text="🔙 رجوع",
        callback_data=f"subcat:{sub_category_id}",
    )
    b.adjust(1)
    return b.as_markup()
```

### `middlewares/__init__.py`

```python

```

### `middlewares/db_session.py`

```python
from aiogram import BaseMiddleware

from database.engine import async_session_maker


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        async with async_session_maker() as session:
            data["session"] = session
            return await handler(event, data)
```

### `middlewares/state_reset_middleware.py`

```python
"""
إذا كان المستخدم داخل تسلسل FSM (مثلاً بمنتصف شحن رصيد)
وضغط على زر من القائمة الرئيسية أو أرسل أمراً (/)،
هذا الميدلوير يصفّر حالته تلقائياً.

التحسين: بدل قائمة نصوص ثابتة، يتحقق من:
1) أي أمر يبدأ بـ /
2) أي callback يبدأ بـ menu: أو admin:
"""
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery


class StateResetMiddleware(BaseMiddleware):

    async def __call__(self, handler, event, data):
        should_reset = False

        if isinstance(event, Message):
            if event.text and event.text.startswith("/"):
                should_reset = True

        elif isinstance(event, CallbackQuery):
            if event.data and (
                event.data.startswith("menu:")
                or event.data.startswith("admin:")
                or event.data == "check_subscription"
                or event.data == "back_to_main"
            ):
                should_reset = True

        if should_reset:
            state = data.get("state")
            if state:
                current = await state.get_state()
                if current is not None:
                    await state.clear()

        return await handler(event, data)
```

### `middlewares/subscription_middleware.py`

```python
"""
يتحقق من اشتراك المستخدم بكل القنوات الإجبارية قبل السماح باستخدام أي زر.
مستثنى منه: الأدمن، أمر /start، وزر "تحقق من الاشتراك" نفسه.
"""
from aiogram.types import Message, CallbackQuery

from services.subscription_service import SubscriptionService
from keyboards.common import check_subscription_kb


class SubscriptionMiddleware:
    def __init__(self, bot):
        self.bot = bot

    async def __call__(self, handler, event, data):
        db_user = data.get("db_user")
        session = data.get("session")

        if db_user is None or db_user.is_admin:
            return await handler(event, data)

        if isinstance(event, Message) and event.text and event.text.startswith("/start"):
            return await handler(event, data)

        if isinstance(event, CallbackQuery) and event.data == "check_subscription":
            return await handler(event, data)

        is_ok, missing_channels = await SubscriptionService.is_user_subscribed_all(
            self.bot, session, db_user.telegram_id
        )

        if not is_ok:
            text = "⚠️ يجب عليك الاشتراك بالقنوات التالية أولاً لاستخدام البوت:"
            kb = check_subscription_kb(missing_channels)
            if isinstance(event, Message):
                await event.answer(text, reply_markup=kb)
            else:
                await event.message.answer(text, reply_markup=kb)
                await event.answer()
            return

        return await handler(event, data)
```

### `middlewares/user_middleware.py`

```python
"""
يضمن وجود المستخدم بقاعدة البيانات قبل أي معالجة.
يربط الإحالة إذا دخل عبر رابط ref_<telegram_id>.
يمنع المستخدم المحظور.
يمنع أي تفاعل أثناء وضع الصيانة (ما عدا الأدمن).
يحدّث last_activity_at.
"""
from datetime import datetime

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from database.models import User
from services.settings_service import SettingsService


class UserMiddleware(BaseMiddleware):

    async def __call__(self, handler, event, data):
        session = data["session"]
        tg_user = data.get("event_from_user")

        if tg_user is None:
            return await handler(event, data)

        result = await session.execute(
            select(User).where(User.telegram_id == tg_user.id)
        )
        user = result.scalar_one_or_none()

        # ── إنشاء مستخدم جديد ──
        if user is None:
            referrer_id = None
            if (
                isinstance(event, Message)
                and event.text
                and event.text.startswith("/start ref_")
            ):
                try:
                    ref_tg_id = int(
                        event.text.split("ref_")[1]
                    )
                    ref_result = await session.execute(
                        select(User).where(
                            User.telegram_id == ref_tg_id
                        )
                    )
                    ref_user = ref_result.scalar_one_or_none()
                    if (
                        ref_user
                        and ref_user.telegram_id != tg_user.id
                    ):
                        referrer_id = ref_user.id
                except (ValueError, IndexError):
                    pass

            user = User(
                telegram_id=tg_user.id,
                username=tg_user.username,
                full_name=tg_user.full_name,
                referrer_id=referrer_id,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        # ── تحديث بيانات المستخدم ──
        updated = False
        if user.username != tg_user.username:
            user.username = tg_user.username
            updated = True
        if user.full_name != tg_user.full_name:
            user.full_name = tg_user.full_name
            updated = True
        user.last_activity_at = datetime.utcnow()
        updated = True
        if updated:
            await session.commit()

        # ── فحص الحظر ──
        if user.is_banned:
            if isinstance(event, Message):
                await event.answer(
                    "🚫 تم حظرك من استخدام البوت.\n"
                    "تواصل مع الدعم الفني إذا كنت تعتقد "
                    "أن هذا خطأ."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "🚫 تم حظرك من استخدام البوت.",
                    show_alert=True,
                )
            return

        # ── فحص وضع الصيانة ──
        if not user.is_admin:
            maintenance_mode = await SettingsService.get_bool(
                "maintenance_mode", False
            )
            if maintenance_mode:
                maintenance_msg = await SettingsService.get(
                    "maintenance_message",
                    "⚙️ البوت تحت الصيانة حالياً، سيعود قريباً..."
                )
                if isinstance(event, Message):
                    await event.answer(maintenance_msg)
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        maintenance_msg,
                        show_alert=True,
                    )
                return

        data["db_user"] = user
        return await handler(event, data)
```

### `protocols/__init__.py`

```python
"""
مجلد بروتوكولات المزودين.
يحتوي على كل بروتوكولات التواصل مع مزودي API المختلفة.

البروتوكولات المدعومة:
- SMM V2 (رشق سوشيال ميديا)
- Games Generic (شحن ألعاب)
- Custom (مخصص لأي موقع)
"""
from protocols.base import (
    BaseProtocol,
    ProtocolBalance,
    ProtocolService,
    ProtocolOrder,
    ProtocolOrderStatus,
    ProtocolError,
)

__all__ = [
    "BaseProtocol",
    "ProtocolBalance",
    "ProtocolService",
    "ProtocolOrder",
    "ProtocolOrderStatus",
    "ProtocolError",
]
```

### `protocols/base.py`

```python
"""
الفئة الأساسية لكل بروتوكولات المزودين.

كل بروتوكول جديد (SMM V2, Games, Custom, إلخ)
يجب أن يرث من BaseProtocol ويطبق الدوال المطلوبة.

هذا يضمن واجهة موحدة للتعامل مع أي مزود.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


# ══════════════ Data Classes ══════════════

@dataclass
class ProtocolBalance:
    """رصيد المزود."""
    amount: Decimal
    currency: str
    raw: dict = field(default_factory=dict)


@dataclass
class ProtocolService:
    """
    خدمة مسحوبة من المزود.
    كل مزود يعيد خدماته بنفس هذا الشكل الموحد.
    """
    external_id: str
    name: str
    category: str | None = None
    service_type: str | None = None
    rate: Decimal = Decimal("0")
    min_quantity: int = 1
    max_quantity: int = 1000000
    description: str | None = None
    requires_link: bool = True
    requires_quantity: bool = True
    requires_player_id: bool = False
    supports_refill: bool = False
    supports_cancel: bool = False
    raw: dict = field(default_factory=dict)


@dataclass
class ProtocolOrder:
    """طلب مرسل للمزود."""
    external_order_id: str
    status: str = "pending"
    charge: Decimal | None = None
    remains: int | None = None
    start_count: int | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class ProtocolOrderStatus:
    """حالة طلب من المزود."""
    external_order_id: str
    status: str
    charge: Decimal | None = None
    remains: int | None = None
    start_count: int | None = None
    raw: dict = field(default_factory=dict)


# ══════════════ Exceptions ══════════════

class ProtocolError(Exception):
    """خطأ عام في البروتوكول."""
    pass


class ProtocolAuthError(ProtocolError):
    """خطأ في المصادقة مع المزود."""
    pass


class ProtocolConnectionError(ProtocolError):
    """خطأ في الاتصال بالمزود."""
    pass


class ProtocolInsufficientFundsError(ProtocolError):
    """الرصيد غير كافٍ عند المزود."""
    pass


class ProtocolInvalidServiceError(ProtocolError):
    """الخدمة المطلوبة غير موجودة."""
    pass


# ══════════════ Order Status Mapping ══════════════

ORDER_STATUS_MAPPING = {
    # حالات مكتملة
    "completed": "completed",
    "complete": "completed",
    "success": "completed",
    "done": "completed",
    "finished": "completed",
    "ok": "completed",

    # حالات فاشلة
    "failed": "failed",
    "fail": "failed",
    "error": "failed",
    "canceled": "failed",
    "cancelled": "failed",
    "rejected": "failed",

    # حالات قيد المعالجة
    "processing": "processing",
    "in_progress": "processing",
    "inprogress": "processing",
    "in progress": "processing",
    "pending": "pending",
    "waiting": "pending",
    "queued": "pending",

    # حالات جزئية
    "partial": "partial",
    "partial_complete": "partial",

    # حالات استرجاع
    "refunded": "refunded",
    "refund": "refunded",
}


def normalize_order_status(status: str) -> str:
    """يحول حالة الطلب من أي مزود إلى الحالات المعيارية."""
    if not status:
        return "pending"
    normalized = status.lower().strip().replace("_", " ")
    return ORDER_STATUS_MAPPING.get(
        normalized,
        ORDER_STATUS_MAPPING.get(status.lower(), "pending"),
    )


# ══════════════ Base Protocol ══════════════

class BaseProtocol(ABC):
    """
    الفئة الأساسية لكل بروتوكولات المزودين.

    كل بروتوكول جديد يجب أن يرث من هذه الفئة
    ويطبق كل الدوال المجرّدة (abstract methods).
    """

    name: str = "base"

    def __init__(
        self,
        api_url: str,
        api_key: str,
        custom_config: dict | None = None,
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.custom_config = custom_config or {}

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        يختبر الاتصال بالمزود.
        يرجع True إذا نجح، False إذا فشل.
        """
        pass

    @abstractmethod
    async def get_balance(self) -> ProtocolBalance:
        """
        يجلب رصيد الحساب لدى المزود.
        """
        pass

    @abstractmethod
    async def get_services(self) -> list[ProtocolService]:
        """
        يجلب كل الخدمات المتاحة لدى المزود.
        """
        pass

    @abstractmethod
    async def place_order(
        self,
        service_id: str,
        target: str,
        quantity: int,
        extra_params: dict | None = None,
    ) -> ProtocolOrder:
        """
        يرسل طلباً جديداً للمزود.

        service_id: آيدي الخدمة عند المزود
        target: الهدف (رابط أو Player ID)
        quantity: الكمية
        extra_params: معاملات إضافية اختيارية
        """
        pass

    @abstractmethod
    async def check_order_status(
        self, external_order_id: str
    ) -> ProtocolOrderStatus:
        """
        يفحص حالة طلب معين.
        """
        pass

    async def check_multiple_orders(
        self, order_ids: list[str]
    ) -> dict[str, ProtocolOrderStatus]:
        """
        يفحص حالة عدة طلبات دفعة واحدة.
        الافتراضي: يستدعي check_order_status لكل واحد.
        يمكن للبروتوكولات إعادة تعريفه لأداء أفضل.
        """
        results = {}
        for order_id in order_ids:
            try:
                status = await self.check_order_status(order_id)
                results[order_id] = status
            except Exception:
                pass
        return results

    async def cancel_order(
        self, external_order_id: str
    ) -> bool:
        """
        يلغي طلباً معيناً.
        الافتراضي: غير مدعوم (يرجع False).
        """
        return False

    async def refill_order(
        self, external_order_id: str
    ) -> bool:
        """
        يعيد ملء طلب معين (إذا نقص).
        الافتراضي: غير مدعوم (يرجع False).
        """
        return False
```

### `protocols/factory.py`

```python
"""
مصنع البروتوكولات (Protocol Factory).

يستخدم Factory Pattern لإنشاء instance من البروتوكول المناسب
حسب نوع المزود المطلوب.

مثال:
    from protocols.factory import ProtocolFactory
    from database.models import ApiProtocolType

    protocol = ProtocolFactory.create(
        protocol_type=ApiProtocolType.SMM_V2,
        api_url="https://jumbosmm.com/api/v2",
        api_key="xxx",
    )
    balance = await protocol.get_balance()
"""
import logging

from database.models import ApiProtocolType, ApiProvider
from protocols.base import BaseProtocol, ProtocolError
from protocols.smm_v2 import SmmV2Protocol

logger = logging.getLogger(__name__)


class ProtocolFactory:
    """
    مصنع البروتوكولات.
    ينشئ instance من البروتوكول المناسب حسب النوع.
    """

    _protocols: dict[ApiProtocolType, type[BaseProtocol]] = {
        ApiProtocolType.SMM_V2: SmmV2Protocol,
    }

    @classmethod
    def register(
        cls,
        protocol_type: ApiProtocolType,
        protocol_class: type[BaseProtocol],
    ) -> None:
        """
        يسجل بروتوكول جديد في المصنع.
        يُستخدم لإضافة بروتوكولات مستقبلية بسهولة.
        """
        cls._protocols[protocol_type] = protocol_class
        logger.info(
            f"تم تسجيل بروتوكول: "
            f"{protocol_type.value} -> "
            f"{protocol_class.__name__}"
        )

    @classmethod
    def create(
        cls,
        protocol_type: ApiProtocolType,
        api_url: str,
        api_key: str,
        custom_config: dict | None = None,
    ) -> BaseProtocol:
        """
        ينشئ instance من البروتوكول المطلوب.

        Raises:
            ProtocolError: إذا كان النوع غير مدعوم.
        """
        protocol_class = cls._protocols.get(protocol_type)
        if not protocol_class:
            available = ", ".join(
                p.value for p in cls._protocols.keys()
            )
            raise ProtocolError(
                f"البروتوكول '{protocol_type.value}' غير مدعوم. "
                f"المتاح: {available}"
            )

        return protocol_class(
            api_url=api_url,
            api_key=api_key,
            custom_config=custom_config,
        )

    @classmethod
    def create_from_provider(
        cls, provider: ApiProvider
    ) -> BaseProtocol:
        """
        ينشئ instance من مزود محفوظ في قاعدة البيانات.
        طريقة مختصرة تُستخدم كثيراً.
        """
        custom_config = None
        if provider.custom_config:
            try:
                import json
                custom_config = json.loads(provider.custom_config)
            except Exception as e:
                logger.warning(
                    f"فشل تحليل custom_config للمزود "
                    f"{provider.id}: {e}"
                )

        return cls.create(
            protocol_type=provider.protocol_type,
            api_url=provider.api_url,
            api_key=provider.api_key,
            custom_config=custom_config,
        )

    @classmethod
    def get_supported_protocols(
        cls,
    ) -> list[ApiProtocolType]:
        """يرجع قائمة البروتوكولات المدعومة حالياً."""
        return list(cls._protocols.keys())

    @classmethod
    def is_supported(
        cls, protocol_type: ApiProtocolType
    ) -> bool:
        """يتحقق إذا كان البروتوكول مدعوماً."""
        return protocol_type in cls._protocols
```

### `protocols/provider_sync_service.py`

```python
"""
خدمة تزامن ومزامنة الخدمات من المزودين.

المهام الرئيسية:
1) سحب كل خدمات المزود وحفظها في قاعدة البيانات
2) تحديث الخدمات الموجودة إذا تغيرت
3) تعطيل الخدمات المحذوفة من المزود
4) تحويل الأسعار من عملة المزود إلى دولار
5) فحص رصيد المزود
6) البحث في خدمات مزود معين
"""
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, and_, or_, func
from sqlalchemy.exc import IntegrityError

from database.engine import async_session_maker
from database.models import (
    ApiProvider,
    ProviderService,
    ProviderServiceStatus,
    ProviderPriceType,
    Product,
    ProductStatus,
)
from protocols.base import ProtocolError
from protocols.factory import ProtocolFactory
from services.currency_service import CurrencyService

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """نتيجة عملية التزامن."""
    provider_id: int
    provider_name: str
    total_fetched: int = 0
    new_services: int = 0
    updated_services: int = 0
    deactivated_services: int = 0
    reactivated_services: int = 0
    failed_services: int = 0
    products_affected: int = 0
    success: bool = True
    error_message: str | None = None
    duration_seconds: float = 0

    def summary(self) -> str:
        """ملخص نصي للنتيجة."""
        if not self.success:
            return (
                f"❌ فشل تزامن {self.provider_name}\n"
                f"السبب: {self.error_message}"
            )

        return (
            f"✅ اكتمل تزامن {self.provider_name}\n\n"
            f"📊 <b>النتائج:</b>\n"
            f"• تم سحب: {self.total_fetched} خدمة\n"
            f"• جديدة: {self.new_services}\n"
            f"• محدّثة: {self.updated_services}\n"
            f"• معطّلة (محذوفة من المزود): "
            f"{self.deactivated_services}\n"
            f"• أعيد تفعيلها: {self.reactivated_services}\n"
            f"• فشلت: {self.failed_services}\n"
            f"• منتجات متأثرة: {self.products_affected}\n"
            f"⏱ الوقت: {self.duration_seconds:.1f} ثانية"
        )


class ProviderSyncService:
    """خدمة تزامن الخدمات من المزودين."""

    @staticmethod
    async def test_provider_connection(
        provider: ApiProvider,
    ) -> tuple[bool, str, Decimal | None, str | None]:
        """
        يختبر الاتصال بمزود ويجلب رصيده.

        Returns:
            (success, message, balance, currency)
        """
        try:
            protocol = ProtocolFactory.create_from_provider(
                provider
            )
        except ProtocolError as e:
            return False, f"خطأ في البروتوكول: {e}", None, None

        try:
            balance_obj = await protocol.get_balance()
            return (
                True,
                "اتصال ناجح",
                balance_obj.amount,
                balance_obj.currency,
            )
        except ProtocolError as e:
            return False, str(e), None, None
        except Exception as e:
            logger.error(
                f"خطأ غير متوقع اختبار مزود "
                f"{provider.id}: {e}"
            )
            return False, f"خطأ غير متوقع: {e}", None, None

    @staticmethod
    async def update_provider_balance(
        provider_id: int,
    ) -> tuple[bool, str]:
        """يحدّث رصيد المزود في قاعدة البيانات."""
        async with async_session_maker() as session:
            provider = await session.get(
                ApiProvider, provider_id
            )
            if not provider:
                return False, "المزود غير موجود"

            success, message, balance, currency = (
                await ProviderSyncService.test_provider_connection(
                    provider
                )
            )

            provider.last_checked_at = datetime.utcnow()

            if not success:
                provider.last_error = message[:500]
                await session.commit()
                return False, message

            provider.balance = balance
            if currency:
                provider.currency = currency
            provider.last_error = None
            await session.commit()

            return True, (
                f"الرصيد الحالي: {balance} {currency}"
            )

    @staticmethod
    async def sync_provider_services(
        provider_id: int,
    ) -> SyncResult:
        """
        يسحب كل خدمات المزود ويحفظها/يحدّثها.

        هذه الدالة الرئيسية للتزامن.
        """
        start_time = datetime.utcnow()

        async with async_session_maker() as session:
            provider = await session.get(
                ApiProvider, provider_id
            )
            if not provider:
                return SyncResult(
                    provider_id=provider_id,
                    provider_name="Unknown",
                    success=False,
                    error_message="المزود غير موجود",
                )

            result = SyncResult(
                provider_id=provider_id,
                provider_name=provider.name,
            )

            try:
                protocol = ProtocolFactory.create_from_provider(
                    provider
                )
            except ProtocolError as e:
                result.success = False
                result.error_message = (
                    f"خطأ في البروتوكول: {e}"
                )
                return result

            try:
                services = await protocol.get_services()
                result.total_fetched = len(services)
            except ProtocolError as e:
                result.success = False
                result.error_message = str(e)
                provider.last_error = str(e)[:500]
                await session.commit()
                return result
            except Exception as e:
                logger.error(
                    f"خطأ غير متوقع سحب خدمات "
                    f"{provider.id}: {e}"
                )
                result.success = False
                result.error_message = f"خطأ غير متوقع: {e}"
                return result

            existing_result = await session.execute(
                select(ProviderService).where(
                    ProviderService.api_provider_id == provider_id
                )
            )
            existing_services = {
                s.external_service_id: s
                for s in existing_result.scalars().all()
            }

            rate_to_usd = provider.rate_to_usd or Decimal("1")
            if provider.currency and provider.currency != "USD":
                if rate_to_usd == Decimal("1"):
                    rate_to_usd = (
                        await CurrencyService.get_rate_to_usd(
                            provider.currency
                        )
                    )
                    provider.rate_to_usd = rate_to_usd

            fetched_ids = set()

            for service in services:
                try:
                    fetched_ids.add(service.external_id)

                    rate_usd = (
                        service.rate * rate_to_usd
                    ).quantize(Decimal("0.0001"))

                    raw_json = json.dumps(
                        service.raw,
                        ensure_ascii=False,
                    )[:5000]

                    existing = existing_services.get(
                        service.external_id
                    )

                    if existing:
                        was_deleted = (
                            existing.status
                            == ProviderServiceStatus.DELETED_FROM_PROVIDER
                        )

                        existing.name = service.name
                        existing.category = service.category
                        existing.service_type = (
                            service.service_type
                        )
                        existing.rate = service.rate
                        existing.rate_usd = rate_usd
                        existing.min_quantity = (
                            service.min_quantity
                        )
                        existing.max_quantity = (
                            service.max_quantity
                        )
                        existing.description = (
                            service.description
                        )
                        existing.requires_link = (
                            service.requires_link
                        )
                        existing.requires_quantity = (
                            service.requires_quantity
                        )
                        existing.requires_player_id = (
                            service.requires_player_id
                        )
                        existing.supports_refill = (
                            service.supports_refill
                        )
                        existing.supports_cancel = (
                            service.supports_cancel
                        )
                        existing.raw_data = raw_json
                        existing.last_updated = (
                            datetime.utcnow()
                        )

                        if was_deleted:
                            existing.status = (
                                ProviderServiceStatus.ACTIVE
                            )
                            result.reactivated_services += 1
                        else:
                            result.updated_services += 1
                    else:
                        new_service = ProviderService(
                            api_provider_id=provider_id,
                            external_service_id=(
                                service.external_id
                            ),
                            name=service.name,
                            category=service.category,
                            service_type=service.service_type,
                            rate=service.rate,
                            rate_usd=rate_usd,
                            price_type=(
                                ProviderPriceType.PER_1000
                            ),
                            min_quantity=service.min_quantity,
                            max_quantity=service.max_quantity,
                            description=service.description,
                            requires_link=service.requires_link,
                            requires_quantity=(
                                service.requires_quantity
                            ),
                            requires_player_id=(
                                service.requires_player_id
                            ),
                            supports_refill=(
                                service.supports_refill
                            ),
                            supports_cancel=(
                                service.supports_cancel
                            ),
                            status=(
                                ProviderServiceStatus.ACTIVE
                            ),
                            raw_data=raw_json,
                        )
                        session.add(new_service)
                        result.new_services += 1

                except Exception as e:
                    logger.warning(
                        f"فشل حفظ خدمة "
                        f"{service.external_id}: {e}"
                    )
                    result.failed_services += 1
                    continue

            deleted_ids = (
                set(existing_services.keys()) - fetched_ids
            )
            for deleted_id in deleted_ids:
                existing = existing_services[deleted_id]
                if (
                    existing.status
                    != ProviderServiceStatus.DELETED_FROM_PROVIDER
                ):
                    existing.status = (
                        ProviderServiceStatus.DELETED_FROM_PROVIDER
                    )
                    result.deactivated_services += 1

                    products_result = await session.execute(
                        select(Product).where(
                            Product.provider_service_ref_id
                            == existing.id
                        )
                    )
                    affected_products = (
                        products_result.scalars().all()
                    )
                    for product in affected_products:
                        product.status = (
                            ProductStatus.INACTIVE
                        )
                        result.products_affected += 1

            provider.last_sync_at = datetime.utcnow()
            provider.total_services = (
                result.total_fetched
                - result.deactivated_services
                + result.new_services
            )
            provider.last_error = None

            try:
                await session.commit()
            except IntegrityError as e:
                await session.rollback()
                logger.error(
                    f"خطأ integrity في تزامن "
                    f"{provider.id}: {e}"
                )
                result.success = False
                result.error_message = str(e)[:200]
                return result

            duration = (
                datetime.utcnow() - start_time
            ).total_seconds()
            result.duration_seconds = duration

            logger.info(
                f"تزامن {provider.name} انتهى: "
                f"{result.new_services} جديدة, "
                f"{result.updated_services} محدّثة, "
                f"{result.deactivated_services} معطّلة "
                f"في {duration:.1f}s"
            )

            return result

    @staticmethod
    async def get_provider_services_count(
        provider_id: int,
        active_only: bool = True,
    ) -> int:
        """يجلب عدد خدمات مزود معين."""
        async with async_session_maker() as session:
            query = select(
                func.count(ProviderService.id)
            ).where(
                ProviderService.api_provider_id == provider_id
            )

            if active_only:
                query = query.where(
                    ProviderService.status
                    == ProviderServiceStatus.ACTIVE
                )

            result = await session.execute(query)
            return result.scalar_one()

    @staticmethod
    async def get_provider_services(
        provider_id: int,
        limit: int = 20,
        offset: int = 0,
        active_only: bool = True,
        search: str | None = None,
        category: str | None = None,
    ) -> list[ProviderService]:
        """
        يجلب خدمات مزود مع دعم البحث والـ Pagination.
        """
        async with async_session_maker() as session:
            query = select(ProviderService).where(
                ProviderService.api_provider_id == provider_id
            )

            if active_only:
                query = query.where(
                    ProviderService.status
                    == ProviderServiceStatus.ACTIVE
                )

            if search:
                search_lower = f"%{search.lower()}%"
                query = query.where(
                    or_(
                        func.lower(
                            ProviderService.name
                        ).like(search_lower),
                        func.lower(
                            ProviderService.category
                        ).like(search_lower),
                        ProviderService.external_service_id
                        == search,
                    )
                )

            if category:
                query = query.where(
                    ProviderService.category == category
                )

            query = query.order_by(
                ProviderService.category,
                ProviderService.name,
            )
            query = query.limit(limit).offset(offset)

            result = await session.execute(query)
            return list(result.scalars().all())

    @staticmethod
    async def get_provider_categories(
        provider_id: int,
    ) -> list[tuple[str, int]]:
        """
        يجلب كل التصنيفات لدى مزود معين مع عدد الخدمات في كل واحد.
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(
                    ProviderService.category,
                    func.count(ProviderService.id).label(
                        "count"
                    ),
                )
                .where(
                    and_(
                        ProviderService.api_provider_id
                        == provider_id,
                        ProviderService.status
                        == ProviderServiceStatus.ACTIVE,
                        ProviderService.category.isnot(
                            None
                        ),
                    )
                )
                .group_by(ProviderService.category)
                .order_by(ProviderService.category)
            )

            return [
                (row.category, row.count)
                for row in result.all()
            ]

    @staticmethod
    async def get_service_by_id(
        service_id: int,
    ) -> ProviderService | None:
        """يجلب خدمة مزود بواسطة الـ ID الداخلي."""
        async with async_session_maker() as session:
            return await session.get(
                ProviderService, service_id
            )
```

### `protocols/smm_v2.py`

```python
"""
بروتوكول SMM V2 القياسي.

هذا البروتوكول يُستخدم في 90%+ من مواقع SMM حول العالم.
كل مواقع SMM تستخدم نفس الـ endpoint (/api/v2) ونفس الـ actions.

مواقع مختبرة تعمل بهذا البروتوكول:
- JumboSMM
- SMMGold
- Justanotherpanel
- PeakSMM
- SMMKings
- SMMShop
- MediaMister (بعض النسخ)

الطلبات كلها POST إلى نفس الـ URL
مع action مختلف في body.

Actions:
- balance   : جلب الرصيد
- services  : جلب كل الخدمات
- add       : إرسال طلب جديد
- status    : فحص حالة طلب
- refill    : إعادة ملء طلب
- cancel    : إلغاء طلب
"""
import json
import logging
from decimal import Decimal

import aiohttp

from protocols.base import (
    BaseProtocol,
    ProtocolBalance,
    ProtocolService,
    ProtocolOrder,
    ProtocolOrderStatus,
    ProtocolError,
    ProtocolAuthError,
    ProtocolConnectionError,
    ProtocolInsufficientFundsError,
    ProtocolInvalidServiceError,
    normalize_order_status,
)

logger = logging.getLogger(__name__)


class SmmV2Protocol(BaseProtocol):
    """
    بروتوكول SMM V2 القياسي.

    الاستخدام:
        protocol = SmmV2Protocol(
            api_url="https://jumbosmm.com/api/v2",
            api_key="your_api_key",
        )

        balance = await protocol.get_balance()
        services = await protocol.get_services()
        order = await protocol.place_order(
            service_id="123",
            target="https://instagram.com/user",
            quantity=1000,
        )
    """

    name = "smm_v2"

    def __init__(
        self,
        api_url: str,
        api_key: str,
        custom_config: dict | None = None,
    ):
        super().__init__(api_url, api_key, custom_config)
        self.timeout = 30

    async def _request(
        self,
        data: dict,
    ) -> dict | list:
        """
        يرسل طلب POST إلى الـ API.
        كل طلبات SMM V2 تُرسل بـ POST مع بيانات في form-data.
        """
        data_with_key = {
            "key": self.api_key,
            **data,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    data=data_with_key,
                    timeout=aiohttp.ClientTimeout(
                        total=self.timeout
                    ),
                ) as resp:
                    text = await resp.text()

                    if resp.status == 401 or resp.status == 403:
                        raise ProtocolAuthError(
                            f"مفتاح API غير صالح: {text[:200]}"
                        )

                    if resp.status not in (200, 201):
                        raise ProtocolConnectionError(
                            f"HTTP {resp.status}: {text[:200]}"
                        )

                    try:
                        result = await resp.json(
                            content_type=None
                        )
                    except (json.JSONDecodeError, Exception):
                        raise ProtocolError(
                            f"استجابة غير صالحة "
                            f"(JSON parsing failed): "
                            f"{text[:200]}"
                        )

                    if isinstance(result, dict):
                        error = result.get("error")
                        if error:
                            error_str = str(error).lower()
                            if "insufficient" in error_str or (
                                "balance" in error_str
                                and "not enough" in error_str
                            ):
                                raise ProtocolInsufficientFundsError(
                                    str(error)
                                )
                            if "service" in error_str and (
                                "not found" in error_str
                                or "invalid" in error_str
                            ):
                                raise ProtocolInvalidServiceError(
                                    str(error)
                                )
                            raise ProtocolError(str(error))

                    return result

        except aiohttp.ClientError as e:
            raise ProtocolConnectionError(
                f"خطأ اتصال: {e}"
            )
        except aiohttp.ClientTimeout:
            raise ProtocolConnectionError(
                f"انتهت مهلة الاتصال ({self.timeout} ثانية)"
            )

    async def test_connection(self) -> bool:
        """
        يختبر الاتصال بجلب الرصيد.
        """
        try:
            await self.get_balance()
            return True
        except Exception as e:
            logger.warning(
                f"فشل اختبار الاتصال مع SMM V2: {e}"
            )
            return False

    async def get_balance(self) -> ProtocolBalance:
        """
        يجلب رصيد الحساب.

        الاستجابة المتوقعة:
        {
            "balance": "100.05",
            "currency": "USD"
        }
        """
        data = await self._request({"action": "balance"})

        if not isinstance(data, dict):
            raise ProtocolError(
                "استجابة غير متوقعة (ليست dict)"
            )

        balance_raw = data.get("balance", "0")
        currency = data.get("currency", "USD")

        try:
            balance_amount = Decimal(str(balance_raw))
        except Exception:
            balance_amount = Decimal("0")

        return ProtocolBalance(
            amount=balance_amount,
            currency=currency,
            raw=data,
        )

    async def get_services(self) -> list[ProtocolService]:
        """
        يجلب كل الخدمات المتاحة.

        الاستجابة المتوقعة:
        [
            {
                "service": 1,
                "name": "Followers",
                "type": "Default",
                "category": "First Category",
                "rate": "0.90",
                "min": "50",
                "max": "10000",
                "refill": true,
                "cancel": true
            },
            ...
        ]
        """
        data = await self._request({"action": "services"})

        if not isinstance(data, list):
            if isinstance(data, dict) and "services" in data:
                data = data["services"]
            elif isinstance(data, dict) and "data" in data:
                data = data["data"]
            else:
                raise ProtocolError(
                    "استجابة الخدمات ليست قائمة"
                )

        services = []
        for item in data:
            if not isinstance(item, dict):
                continue

            try:
                service = self._parse_service(item)
                services.append(service)
            except Exception as e:
                logger.warning(
                    f"فشل تحليل خدمة: {item} - {e}"
                )
                continue

        return services

    def _parse_service(
        self, item: dict
    ) -> ProtocolService:
        """يحول dict خدمة إلى ProtocolService."""
        external_id = str(item.get(
            "service", item.get("id", "")
        ))

        if not external_id:
            raise ProtocolError("خدمة بدون معرّف")

        name = str(item.get("name", "Unknown Service"))
        category = item.get("category")
        service_type = item.get("type")

        rate_raw = item.get("rate", "0")
        try:
            rate = Decimal(str(rate_raw))
        except Exception:
            rate = Decimal("0")

        try:
            min_qty = int(item.get("min", 1))
        except (ValueError, TypeError):
            min_qty = 1

        try:
            max_qty = int(item.get("max", 1000000))
        except (ValueError, TypeError):
            max_qty = 1000000

        description = item.get("description")
        refill = bool(item.get("refill", False))
        cancel = bool(item.get("cancel", False))

        return ProtocolService(
            external_id=external_id,
            name=name,
            category=str(category) if category else None,
            service_type=(
                str(service_type) if service_type else None
            ),
            rate=rate,
            min_quantity=min_qty,
            max_quantity=max_qty,
            description=(
                str(description) if description else None
            ),
            requires_link=True,
            requires_quantity=True,
            requires_player_id=False,
            supports_refill=refill,
            supports_cancel=cancel,
            raw=item,
        )

    async def place_order(
        self,
        service_id: str,
        target: str,
        quantity: int,
        extra_params: dict | None = None,
    ) -> ProtocolOrder:
        """
        يرسل طلب جديد.

        الاستجابة المتوقعة:
        {
            "order": 23501
        }
        """
        request_data = {
            "action": "add",
            "service": service_id,
            "link": target,
            "quantity": quantity,
        }

        if extra_params:
            request_data.update(extra_params)

        data = await self._request(request_data)

        if not isinstance(data, dict):
            raise ProtocolError(
                "استجابة غير متوقعة عند الطلب"
            )

        order_id = data.get("order")
        if not order_id:
            raise ProtocolError(
                f"لم يُرجع المزود order_id: {data}"
            )

        return ProtocolOrder(
            external_order_id=str(order_id),
            status="pending",
            raw=data,
        )

    async def check_order_status(
        self, external_order_id: str
    ) -> ProtocolOrderStatus:
        """
        يفحص حالة طلب معين.

        الاستجابة المتوقعة:
        {
            "charge": "0.27819",
            "start_count": "3572",
            "status": "Partial",
            "remains": "157",
            "currency": "USD"
        }
        """
        data = await self._request({
            "action": "status",
            "order": external_order_id,
        })

        if not isinstance(data, dict):
            raise ProtocolError(
                "استجابة غير متوقعة عند فحص الحالة"
            )

        raw_status = data.get("status", "pending")
        normalized = normalize_order_status(raw_status)

        charge = None
        if "charge" in data:
            try:
                charge = Decimal(str(data["charge"]))
            except Exception:
                pass

        remains = None
        if "remains" in data:
            try:
                remains = int(data["remains"])
            except (ValueError, TypeError):
                pass

        start_count = None
        if "start_count" in data:
            try:
                start_count = int(data["start_count"])
            except (ValueError, TypeError):
                pass

        return ProtocolOrderStatus(
            external_order_id=external_order_id,
            status=normalized,
            charge=charge,
            remains=remains,
            start_count=start_count,
            raw=data,
        )

    async def check_multiple_orders(
        self, order_ids: list[str]
    ) -> dict[str, ProtocolOrderStatus]:
        """
        يفحص حالة عدة طلبات دفعة واحدة.
        SMM V2 يدعم هذا عبر إرسال orders (بصيغة CSV).
        """
        if not order_ids:
            return {}

        if len(order_ids) == 1:
            try:
                status = await self.check_order_status(
                    order_ids[0]
                )
                return {order_ids[0]: status}
            except Exception:
                return {}

        orders_csv = ",".join(order_ids)

        try:
            data = await self._request({
                "action": "status",
                "orders": orders_csv,
            })
        except Exception as e:
            logger.warning(
                f"فشل فحص متعدد للطلبات: {e}"
            )
            return await super().check_multiple_orders(order_ids)

        if not isinstance(data, dict):
            return {}

        results = {}
        for order_id, order_data in data.items():
            if not isinstance(order_data, dict):
                continue

            raw_status = order_data.get("status", "pending")
            normalized = normalize_order_status(raw_status)

            charge = None
            if "charge" in order_data:
                try:
                    charge = Decimal(str(order_data["charge"]))
                except Exception:
                    pass

            remains = None
            if "remains" in order_data:
                try:
                    remains = int(order_data["remains"])
                except (ValueError, TypeError):
                    pass

            start_count = None
            if "start_count" in order_data:
                try:
                    start_count = int(
                        order_data["start_count"]
                    )
                except (ValueError, TypeError):
                    pass

            results[str(order_id)] = ProtocolOrderStatus(
                external_order_id=str(order_id),
                status=normalized,
                charge=charge,
                remains=remains,
                start_count=start_count,
                raw=order_data,
            )

        return results

    async def cancel_order(
        self, external_order_id: str
    ) -> bool:
        """يلغي طلباً معيناً."""
        try:
            data = await self._request({
                "action": "cancel",
                "orders": external_order_id,
            })

            if isinstance(data, dict):
                error = data.get("error")
                if error:
                    logger.warning(
                        f"فشل إلغاء الطلب "
                        f"{external_order_id}: {error}"
                    )
                    return False
            return True
        except Exception as e:
            logger.error(
                f"خطأ في إلغاء الطلب "
                f"{external_order_id}: {e}"
            )
            return False

    async def refill_order(
        self, external_order_id: str
    ) -> bool:
        """يعيد ملء طلب معين."""
        try:
            data = await self._request({
                "action": "refill",
                "order": external_order_id,
            })

            if isinstance(data, dict):
                error = data.get("error")
                if error:
                    logger.warning(
                        f"فشل refill للطلب "
                        f"{external_order_id}: {error}"
                    )
                    return False
            return True
        except Exception as e:
            logger.error(
                f"خطأ في refill الطلب "
                f"{external_order_id}: {e}"
            )
            return False
```

### `providers/__init__.py`

```python

```

### `providers/base.py`

```python
"""
الواجهة الأساسية لكل مزودي الأرقام.
العملة الداخلية: دولار أمريكي (USD).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class PurchasedNumber:
    provider_order_id: str
    phone_number: str
    cost_usd: Decimal
    raw: dict


@dataclass
class OrderStatusResult:
    status: str
    sms_code: str | None
    full_text: str | None
    raw: dict


class BaseProvider(ABC):
    name: str

    @abstractmethod
    async def get_balance(self) -> Decimal:
        """يجلب رصيد الحساب لدى المزود بالدولار."""
        ...

    @abstractmethod
    async def get_price(
        self, country: str, service: str
    ) -> Decimal | None:
        """
        يجلب سعر التكلفة بالدولار.
        يرجع None إذا لم تكن الخدمة متاحة.
        """
        ...

    @abstractmethod
    async def buy_number(
        self,
        country: str,
        service: str,
        operator: str | None = None,
    ) -> PurchasedNumber:
        """يشتري رقماً ويرجع بيانات الشراء."""
        ...

    @abstractmethod
    async def check_status(
        self, order_id: str
    ) -> OrderStatusResult:
        """يتحقق من حالة الطلب ويرجع الكود إذا وصل."""
        ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """يلغي الطلب ويرجع True إذا نجح."""
        ...

    @abstractmethod
    async def finish_order(self, order_id: str) -> bool:
        """يُنهي الطلب بعد استلام الكود."""
        ...

    @abstractmethod
    async def get_countries_services(self) -> list[dict]:
        """يجلب قائمة الدول والخدمات المتاحة."""
        ...
```

### `providers/countries.py`

```python
"""
الدول وخدمات الأرقام تُدار بالكامل من لوحة الأدمن عبر قاعدة البيانات.
لا يوجد أي دولة أو خدمة مبرمجة مسبقاً بالكود.
"""
from sqlalchemy import select

from database.models import Country, NumberService


async def get_active_countries(session) -> list[Country]:
    """يجلب الدول المفعلة مرتبة حسب sort_order ثم الاسم."""
    result = await session.execute(
        select(Country)
        .where(Country.is_active == True)
        .order_by(Country.sort_order, Country.name_ar)
    )
    return list(result.scalars().all())


async def get_country_by_code(
    session, code: str
) -> Country | None:
    result = await session.execute(
        select(Country).where(Country.code == code)
    )
    return result.scalar_one_or_none()


async def get_all_countries(session) -> list[Country]:
    """لعرضها بلوحة الأدمن (نشطة وغير نشطة معاً)."""
    result = await session.execute(
        select(Country).order_by(Country.sort_order, Country.name_ar)
    )
    return list(result.scalars().all())


async def get_active_number_services(
    session,
) -> list[NumberService]:
    """يجلب خدمات الأرقام المفعلة (واتساب، تيليجرام، إلخ)."""
    result = await session.execute(
        select(NumberService)
        .where(NumberService.is_active == True)
        .order_by(NumberService.sort_order, NumberService.id)
    )
    return list(result.scalars().all())


async def get_number_service_by_code(
    session, code: str
) -> NumberService | None:
    result = await session.execute(
        select(NumberService).where(NumberService.code == code)
    )
    return result.scalar_one_or_none()


async def get_all_number_services(
    session,
) -> list[NumberService]:
    """لعرضها بلوحة الأدمن."""
    result = await session.execute(
        select(NumberService)
        .order_by(NumberService.sort_order, NumberService.id)
    )
    return list(result.scalars().all())
```

### `providers/fivesim.py`

```python
"""
مزود أرقام 5sim.
يحول الأسعار من الروبل إلى الدولار تلقائياً.
"""
import logging
from decimal import Decimal

import aiohttp

from providers.base import BaseProvider, PurchasedNumber, OrderStatusResult
from config import settings

logger = logging.getLogger(__name__)

FIVESIM_BASE = "https://5sim.net/v1/"
FIVESIM_RUB_TO_USD_RATE = Decimal("100")


class ProviderAPIError(Exception):
    pass


class FiveSimProvider(BaseProvider):
    name = "fivesim"

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {settings.FIVESIM_API_KEY}",
            "Accept": "application/json",
        }

    async def _request(
        self, method: str, path: str, **kwargs
    ):
        url = FIVESIM_BASE + path
        async with aiohttp.ClientSession(
            headers=self.headers
        ) as session:
            async with session.request(
                method,
                url,
                timeout=aiohttp.ClientTimeout(total=20),
                **kwargs,
            ) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise ProviderAPIError(
                        f"5sim error {resp.status}: {text}"
                    )
                try:
                    return await resp.json(content_type=None)
                except Exception:
                    return text

    def _rub_to_usd(self, amount_rub: Decimal) -> Decimal:
        """يحول الروبل للدولار بسعر صرف 5sim الداخلي."""
        return (amount_rub / FIVESIM_RUB_TO_USD_RATE).quantize(
            Decimal("0.0001")
        )

    async def get_balance(self) -> Decimal:
        data = await self._request("GET", "user/profile")
        balance_rub = Decimal(str(data.get("balance", 0)))
        return self._rub_to_usd(balance_rub)

    async def get_countries_services(self) -> list[dict]:
        raise NotImplementedError(
            "يُستخدم get_price مباشرة"
        )

    async def list_countries(self) -> list[str]:
        """
        قائمة مرجعية بأكواد الدول المتاحة لدى 5sim.
        تُستخدم فقط لمساعدة الأدمن.
        """
        data = await self._request("GET", "guest/countries")
        result = []
        for code, info in data.items():
            name = (info or {}).get("text_en") or code
            result.append(f"<code>{code}</code> — {name}")
        return sorted(result)

    async def get_price(
        self, country: str, service: str
    ) -> Decimal | None:
        data = await self._request(
            "GET",
            f"guest/prices?country={country}&product={service}"
        )
        try:
            country_data = data[country][service]
            cheapest = None
            for operator, info in country_data.items():
                if info.get("count", 0) > 0:
                    cost_rub = Decimal(str(info["cost"]))
                    cost_usd = self._rub_to_usd(cost_rub)
                    if cheapest is None or cost_usd < cheapest:
                        cheapest = cost_usd
            return cheapest
        except (KeyError, TypeError):
            return None

    async def buy_number(
        self,
        country: str,
        service: str,
        operator: str = "any",
    ) -> PurchasedNumber:
        data = await self._request(
            "GET",
            f"user/buy/activation/{country}/{operator}/{service}"
        )
        cost_rub = Decimal(str(data["price"]))
        cost_usd = self._rub_to_usd(cost_rub)
        return PurchasedNumber(
            provider_order_id=str(data["id"]),
            phone_number=data["phone"],
            cost_usd=cost_usd,
            raw=data,
        )

    async def check_status(
        self, order_id: str
    ) -> OrderStatusResult:
        data = await self._request(
            "GET", f"user/check/{order_id}"
        )
        status = data.get("status")
        sms_list = data.get("sms") or []
        code = None
        full_text = None

        if sms_list:
            code = sms_list[0].get("code")
            full_text = sms_list[0].get("text")

        mapped = "pending"
        if code:
            mapped = "code_received"
        elif status == "CANCELED":
            mapped = "cancelled"
        elif status in ("TIMEOUT", "EXPIRED"):
            mapped = "expired"

        return OrderStatusResult(
            status=mapped,
            sms_code=code,
            full_text=full_text,
            raw=data,
        )

    async def cancel_order(self, order_id: str) -> bool:
        try:
            await self._request(
                "GET", f"user/cancel/{order_id}"
            )
            return True
        except Exception as e:
            logger.error(
                f"فشل إلغاء الطلب {order_id} من 5sim: {e}"
            )
            return False

    async def finish_order(self, order_id: str) -> bool:
        try:
            await self._request(
                "GET", f"user/finish/{order_id}"
            )
            return True
        except Exception as e:
            logger.error(
                f"فشل إتمام الطلب {order_id} من 5sim: {e}"
            )
            return False
```

### `providers/games_provider.py`

```python
"""
مزود شحن الألعاب والتطبيقات.
يتصل بـ API الخاص بمزود شحن الألعاب لتنفيذ الطلبات تلقائياً.
يدعم أي مزود يستخدم REST API مع JSON.
"""
import logging
from decimal import Decimal

import aiohttp

from database.models import ApiProvider

logger = logging.getLogger(__name__)


class GamesProviderError(Exception):
    pass


class GamesProviderClient:
    """
    عميل عام للتواصل مع مزودي شحن الألعاب.
    كل مزود يُخزن بياناته (api_url, api_key) في جدول api_providers.
    """

    def __init__(self, provider: ApiProvider):
        self.provider = provider
        self.api_url = provider.api_url.rstrip("/")
        self.api_key = provider.api_key

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        url = f"{self.api_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            async with aiohttp.ClientSession(
                headers=headers
            ) as session:
                async with session.request(
                    method,
                    url,
                    json=data,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    text = await resp.text()
                    if resp.status not in (200, 201):
                        raise GamesProviderError(
                            f"خطأ من مزود الألعاب "
                            f"{self.provider.name}: "
                            f"HTTP {resp.status}: {text[:200]}"
                        )
                    try:
                        return await resp.json(
                            content_type=None
                        )
                    except Exception:
                        raise GamesProviderError(
                            f"استجابة غير صالحة من "
                            f"{self.provider.name}: {text[:200]}"
                        )
        except aiohttp.ClientError as e:
            raise GamesProviderError(
                f"خطأ اتصال مع {self.provider.name}: {e}"
            )

    async def get_balance(self) -> Decimal:
        """يجلب رصيد الحساب لدى المزود."""
        try:
            data = await self._request("GET", "balance")
            balance = data.get("balance", data.get("data", {}).get("balance", 0))
            return Decimal(str(balance))
        except Exception as e:
            logger.error(
                f"فشل جلب رصيد مزود الألعاب "
                f"{self.provider.name}: {e}"
            )
            raise

    async def place_order(
        self,
        service_id: str,
        target: str,
        quantity: int = 1,
    ) -> dict:
        """
        يرسل طلب شحن لعبة/تطبيق.
        service_id: آيدي الخدمة عند المزود
        target: آيدي اللاعب أو الحساب
        quantity: الكمية
        يرجع dict يحتوي على order_id على الأقل.
        """
        try:
            data = await self._request(
                "POST",
                "order",
                data={
                    "service_id": service_id,
                    "target": target,
                    "quantity": quantity,
                },
            )

            order_id = data.get(
                "order_id",
                data.get("id", data.get("data", {}).get("order_id"))
            )

            if order_id is None:
                raise GamesProviderError(
                    f"لم يُرجع المزود {self.provider.name} "
                    f"رقم طلب. الاستجابة: {data}"
                )

            return {
                "order_id": str(order_id),
                "status": data.get("status", "pending"),
                "raw": data,
            }
        except GamesProviderError:
            raise
        except Exception as e:
            raise GamesProviderError(
                f"فشل إرسال الطلب لمزود "
                f"{self.provider.name}: {e}"
            )

    async def check_order_status(
        self, order_id: str
    ) -> dict:
        """
        يتحقق من حالة الطلب.
        يرجع dict يحتوي status و message.
        """
        try:
            data = await self._request(
                "GET",
                f"order/{order_id}",
            )

            status = data.get(
                "status",
                data.get("data", {}).get("status", "pending")
            )
            message = data.get(
                "message",
                data.get("data", {}).get("message", "")
            )

            status_map = {
                "completed": "completed",
                "success": "completed",
                "done": "completed",
                "failed": "failed",
                "error": "failed",
                "cancelled": "failed",
                "canceled": "failed",
                "refunded": "refunded",
                "processing": "processing",
                "pending": "pending",
                "in_progress": "processing",
                "partial": "partial",
            }

            normalized_status = status_map.get(
                status.lower(), "pending"
            )

            return {
                "status": normalized_status,
                "message": message,
                "raw": data,
            }
        except GamesProviderError:
            raise
        except Exception as e:
            raise GamesProviderError(
                f"فشل فحص حالة الطلب {order_id} "
                f"من {self.provider.name}: {e}"
            )

    async def get_services(self) -> list[dict]:
        """يجلب قائمة الخدمات المتاحة (اختياري)."""
        try:
            data = await self._request("GET", "services")
            services = data if isinstance(data, list) else data.get(
                "data", data.get("services", [])
            )
            return services
        except Exception as e:
            logger.warning(
                f"فشل جلب خدمات مزود {self.provider.name}: {e}"
            )
            return []
```

### `providers/herosms.py`

```python
"""
مزود أرقام HeroSMS.
يعمل بنمط SMS-Activate الكلاسيكي (action-based).
يحول الأسعار من الروبل إلى الدولار تلقائياً.
"""
import json
import logging
from decimal import Decimal

import aiohttp

from providers.base import BaseProvider, PurchasedNumber, OrderStatusResult
from config import settings

logger = logging.getLogger(__name__)

HEROSMS_BASE = "https://hero-sms.com/stubs/handler_api.php"
HEROSMS_RUB_TO_USD_RATE = Decimal("100")


class ProviderAPIError(Exception):
    pass


class HeroSMSProvider(BaseProvider):
    name = "herosms"

    def __init__(self):
        self.api_key = settings.HEROSMS_API_KEY

    async def _request(self, params: dict) -> str:
        params = {"api_key": self.api_key, **params}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                HEROSMS_BASE,
                params=params,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise ProviderAPIError(
                        f"HeroSMS error {resp.status}: {text}"
                    )
                return text.strip()

    def _rub_to_usd(self, amount_rub: Decimal) -> Decimal:
        """يحول الروبل للدولار بسعر صرف HeroSMS الداخلي."""
        return (amount_rub / HEROSMS_RUB_TO_USD_RATE).quantize(
            Decimal("0.0001")
        )

    async def get_balance(self) -> Decimal:
        result = await self._request({"action": "getBalance"})
        if result.startswith("ACCESS_BALANCE:"):
            balance_rub = Decimal(result.split(":")[1])
            return self._rub_to_usd(balance_rub)
        raise ProviderAPIError(
            f"استجابة غير متوقعة من HeroSMS: {result}"
        )

    async def get_countries_services(self) -> list[dict]:
        raise NotImplementedError(
            "يُستخدم get_price مباشرة"
        )

    async def get_price(
        self, country: str, service: str
    ) -> Decimal | None:
        result = await self._request({
            "action": "getPrices",
            "country": country,
            "service": service,
        })
        try:
            data = json.loads(result)
            country_data = data.get(country, {}).get(service, {})
            if not country_data:
                return None
            first_operator = list(country_data.values())[0]
            cost = first_operator.get("cost")
            if cost is None:
                return None
            cost_rub = Decimal(str(cost))
            return self._rub_to_usd(cost_rub)
        except Exception:
            return None

    async def buy_number(
        self,
        country: str,
        service: str,
        operator: str | None = None,
    ) -> PurchasedNumber:
        result = await self._request({
            "action": "getNumber",
            "service": service,
            "country": country,
        })
        if result.startswith("ACCESS_NUMBER:"):
            parts = result.split(":")
            order_id = parts[1]
            phone = parts[2]
            price = await self.get_price(country, service)
            cost_usd = price if price is not None else Decimal("0")
            return PurchasedNumber(
                provider_order_id=order_id,
                phone_number=phone,
                cost_usd=cost_usd,
                raw={"raw_response": result},
            )
        raise ProviderAPIError(
            f"فشل شراء رقم من HeroSMS: {result}"
        )

    async def check_status(
        self, order_id: str
    ) -> OrderStatusResult:
        result = await self._request({
            "action": "getStatus",
            "id": order_id,
        })
        mapped = "pending"
        code = None

        if result.startswith("STATUS_OK:"):
            code = result.split(":")[1]
            mapped = "code_received"
        elif result == "STATUS_CANCEL":
            mapped = "cancelled"

        return OrderStatusResult(
            status=mapped,
            sms_code=code,
            full_text=result,
            raw={"raw": result},
        )

    async def cancel_order(self, order_id: str) -> bool:
        try:
            await self._request({
                "action": "setStatus",
                "id": order_id,
                "status": 8,
            })
            return True
        except Exception as e:
            logger.error(
                f"فشل إلغاء الطلب {order_id} من HeroSMS: {e}"
            )
            return False

    async def finish_order(self, order_id: str) -> bool:
        try:
            await self._request({
                "action": "setStatus",
                "id": order_id,
                "status": 6,
            })
            return True
        except Exception as e:
            logger.error(
                f"فشل إتمام الطلب {order_id} من HeroSMS: {e}"
            )
            return False
```

### `providers/manager.py`

```python
"""
مدير مزودي الأرقام مع Failover تلقائي.

المنطق:
1) يجلب أسعار كل المزودين المتاحين للدولة/الخدمة.
2) يرتبهم حسب السعر (الأرخص أولاً).
3) يحاول الشراء من الأرخص، إذا فشل ينتقل للتالي.
4) يتحقق من is_online قبل المحاولة لتجنب التأخير.
5) العملة: دولار أمريكي (USD) بالكامل.
"""
import logging
from dataclasses import dataclass
from decimal import Decimal

from database.models import Country, NumberService, ProviderName, ProviderStatus
from providers.fivesim import FiveSimProvider
from providers.herosms import HeroSMSProvider
from providers.sms_activate import SMSActivateProvider
from providers.smshub import SMSHubProvider
from config import settings

logger = logging.getLogger(__name__)


class ProviderUnavailableError(Exception):
    pass


@dataclass
class BuyResult:
    provider: ProviderName
    provider_order_id: str
    phone_number: str
    cost_usd: Decimal


class ProviderManager:

    def __init__(self):
        self._providers: dict[ProviderName, object] = {}
        self._init_providers()

    def _init_providers(self):
        """يُنشئ المزودين الذين لديهم API key فقط."""
        if settings.FIVESIM_API_KEY:
            self._providers[ProviderName.FIVESIM] = FiveSimProvider()

        if settings.HEROSMS_API_KEY:
            self._providers[ProviderName.HEROSMS] = HeroSMSProvider()

        if settings.SMS_ACTIVATE_API_KEY:
            self._providers[ProviderName.SMS_ACTIVATE] = SMSActivateProvider()

        if settings.SMSHUB_API_KEY:
            self._providers[ProviderName.SMSHUB] = SMSHubProvider()

        logger.info(
            f"تم تهيئة {len(self._providers)} مزود أرقام: "
            f"{', '.join(p.value for p in self._providers.keys())}"
        )

    def _get_instance(self, provider: ProviderName):
        instance = self._providers.get(provider)
        if instance is None:
            raise ProviderUnavailableError(
                f"المزود {provider.value} غير مهيأ (لا يوجد API Key)"
            )
        return instance

    def _get_provider_code(
        self,
        provider: ProviderName,
        country: Country,
    ) -> str | None:
        """يجلب كود الدولة الخاص بمزود معين."""
        code_map = {
            ProviderName.FIVESIM: country.fivesim_code,
            ProviderName.HEROSMS: country.herosms_code,
            ProviderName.SMS_ACTIVATE: country.sms_activate_code,
            ProviderName.SMSHUB: country.smshub_code,
        }
        return code_map.get(provider)

    def _get_service_code(
        self,
        provider: ProviderName,
        service: NumberService,
    ) -> str | None:
        """يجلب كود الخدمة الخاص بمزود معين."""
        code_map = {
            ProviderName.FIVESIM: service.fivesim_code,
            ProviderName.HEROSMS: service.herosms_code,
            ProviderName.SMS_ACTIVATE: service.sms_activate_code,
            ProviderName.SMSHUB: service.smshub_code,
        }
        return code_map.get(provider)

    async def _is_provider_online(
        self,
        session,
        provider: ProviderName,
    ) -> bool:
        """يتحقق من حالة المزود في قاعدة البيانات."""
        status = await session.get(ProviderStatus, provider)
        if status is None:
            return False
        return status.is_online

    async def get_cheapest_price(
        self,
        service: NumberService,
        country: Country,
        session=None,
    ) -> dict[ProviderName, Decimal]:
        """
        يجلب أسعار كل المزودين المتاحين لخدمة/دولة معينة.
        يرجع dict مع المزود كمفتاح والسعر بالدولار كقيمة.
        """
        result = {}

        for provider_name, instance in self._providers.items():
            country_code = self._get_provider_code(
                provider_name, country
            )
            service_code = self._get_service_code(
                provider_name, service
            )

            if not country_code or not service_code:
                continue

            if session:
                is_online = await self._is_provider_online(
                    session, provider_name
                )
                if not is_online:
                    continue

            try:
                price = await instance.get_price(
                    country_code, service_code
                )
                if price is not None:
                    result[provider_name] = price
            except Exception as e:
                logger.warning(
                    f"فشل جلب سعر من {provider_name.value}: {e}"
                )

        return result

    async def buy_number(
        self,
        service: NumberService,
        country: Country,
        session=None,
    ) -> BuyResult:
        """
        يشتري رقماً من أرخص مزود متاح.
        إذا فشل ينتقل تلقائياً للمزود التالي (Failover).
        """
        prices = await self.get_cheapest_price(
            service, country, session
        )

        if not prices:
            raise ProviderUnavailableError(
                f"لا يوجد مزود متاح لـ "
                f"{service.name_ar} - {country.name_ar}"
            )

        sorted_providers = sorted(
            prices.items(), key=lambda x: x[1]
        )

        errors = []

        for provider_name, estimated_price in sorted_providers:
            instance = self._providers[provider_name]
            country_code = self._get_provider_code(
                provider_name, country
            )
            service_code = self._get_service_code(
                provider_name, service
            )

            try:
                purchased = await instance.buy_number(
                    country_code, service_code
                )
                logger.info(
                    f"شراء ناجح من {provider_name.value}: "
                    f"{purchased.phone_number} "
                    f"بتكلفة {purchased.cost_usd}$"
                )
                return BuyResult(
                    provider=provider_name,
                    provider_order_id=purchased.provider_order_id,
                    phone_number=purchased.phone_number,
                    cost_usd=purchased.cost_usd,
                )
            except Exception as e:
                errors.append(
                    f"{provider_name.value}: {e}"
                )
                logger.warning(
                    f"فشل الشراء من {provider_name.value}: {e}"
                )
                continue

        raise ProviderUnavailableError(
            f"فشل الشراء من كل المزودين المتاحين. "
            f"{' | '.join(errors)}"
        )

    async def check_status(
        self,
        provider: ProviderName,
        order_id: str,
    ):
        """يتحقق من حالة طلب عند مزود محدد."""
        return await self._get_instance(provider).check_status(
            order_id
        )

    async def cancel_order(
        self,
        provider: ProviderName,
        order_id: str,
    ) -> bool:
        """يلغي طلباً عند مزود محدد."""
        return await self._get_instance(provider).cancel_order(
            order_id
        )

    async def finish_order(
        self,
        provider: ProviderName,
        order_id: str,
    ) -> bool:
        """يُنهي طلباً عند مزود محدد بعد استلام الكود."""
        return await self._get_instance(provider).finish_order(
            order_id
        )

    async def get_balance(
        self,
        provider: ProviderName,
    ) -> Decimal:
        """يجلب رصيد مزود محدد بالدولار."""
        return await self._get_instance(provider).get_balance()

    def get_available_providers(self) -> list[ProviderName]:
        """يجلب قائمة المزودين المهيأين (لديهم API Key)."""
        return list(self._providers.keys())


provider_manager = ProviderManager()
```

### `providers/smm_provider.py`

```python
"""
مزود رشق السوشيال ميديا.
يدعم أي موقع SMM يستخدم البروتوكول القياسي v2 API.
البروتوكول القياسي يستخدم 4 endpoints:
- balance: جلب الرصيد
- services: جلب الخدمات
- order: إرسال طلب
- status: فحص حالة الطلب
"""
import logging
from decimal import Decimal

import aiohttp

from database.models import ApiProvider

logger = logging.getLogger(__name__)


class SMMProviderError(Exception):
    pass


class SMMProviderClient:
    """
    عميل عام لأي موقع SMM يدعم v2 API.
    الأدمن يضيف المزود من لوحة التحكم بإدخال:
    - api_url: رابط الـ API (مثل https://example.com/api/v2)
    - api_key: مفتاح الـ API
    """

    def __init__(self, provider: ApiProvider):
        self.provider = provider
        self.api_url = provider.api_url.rstrip("/")
        self.api_key = provider.api_key

    async def _request(
        self,
        data: dict,
    ) -> dict | list:
        """
        يرسل طلب POST لـ API المزود.
        كل طلبات SMM v2 API تُرسل عبر POST بنفس الرابط.
        """
        data["key"] = self.api_key

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    text = await resp.text()
                    if resp.status != 200:
                        raise SMMProviderError(
                            f"خطأ من مزود SMM "
                            f"{self.provider.name}: "
                            f"HTTP {resp.status}: {text[:200]}"
                        )
                    try:
                        result = await resp.json(
                            content_type=None
                        )
                    except Exception:
                        raise SMMProviderError(
                            f"استجابة غير صالحة من "
                            f"{self.provider.name}: {text[:200]}"
                        )

                    if isinstance(result, dict) and result.get("error"):
                        raise SMMProviderError(
                            f"خطأ من {self.provider.name}: "
                            f"{result.get('error')}"
                        )

                    return result
        except aiohttp.ClientError as e:
            raise SMMProviderError(
                f"خطأ اتصال مع {self.provider.name}: {e}"
            )

    async def get_balance(self) -> Decimal:
        """يجلب رصيد الحساب لدى المزود."""
        try:
            data = await self._request({
                "action": "balance",
            })
            balance = data.get(
                "balance",
                data.get("data", {}).get("balance", 0)
            )
            return Decimal(str(balance))
        except Exception as e:
            logger.error(
                f"فشل جلب رصيد مزود SMM "
                f"{self.provider.name}: {e}"
            )
            raise

    async def get_services(self) -> list[dict]:
        """
        يجلب كل الخدمات المتاحة من المزود.
        كل خدمة تحتوي: service (id), name, rate, min, max, type, category.
        """
        try:
            result = await self._request({
                "action": "services",
            })
            if isinstance(result, list):
                return result
            return result.get("data", result.get("services", []))
        except Exception as e:
            logger.warning(
                f"فشل جلب خدمات مزود SMM "
                f"{self.provider.name}: {e}"
            )
            return []

    async def place_order(
        self,
        service_id: str,
        link: str,
        quantity: int,
    ) -> dict:
        """
        يرسل طلب رشق.
        service_id: آيدي الخدمة عند المزود
        link: رابط الحساب/المنشور
        quantity: الكمية المطلوبة
        يرجع dict يحتوي order_id.
        """
        try:
            data = await self._request({
                "action": "add",
                "service": service_id,
                "link": link,
                "quantity": str(quantity),
            })

            order_id = data.get("order")
            if order_id is None:
                raise SMMProviderError(
                    f"لم يُرجع المزود {self.provider.name} "
                    f"رقم طلب. الاستجابة: {data}"
                )

            return {
                "order_id": str(order_id),
                "status": "pending",
                "raw": data,
            }
        except SMMProviderError:
            raise
        except Exception as e:
            raise SMMProviderError(
                f"فشل إرسال طلب SMM لمزود "
                f"{self.provider.name}: {e}"
            )

    async def check_order_status(
        self, order_id: str
    ) -> dict:
        """
        يتحقق من حالة الطلب.
        يرجع status, start_count, remains, charge.
        """
        try:
            data = await self._request({
                "action": "status",
                "order": order_id,
            })

            status = data.get("status", "pending")

            status_map = {
                "Completed": "completed",
                "completed": "completed",
                "In progress": "processing",
                "in_progress": "processing",
                "Processing": "processing",
                "processing": "processing",
                "Pending": "pending",
                "pending": "pending",
                "Partial": "partial",
                "partial": "partial",
                "Canceled": "failed",
                "canceled": "failed",
                "Cancelled": "failed",
                "cancelled": "failed",
                "Refunded": "refunded",
                "refunded": "refunded",
                "Error": "failed",
                "error": "failed",
                "Fail": "failed",
            }

            normalized_status = status_map.get(
                status, "pending"
            )

            return {
                "status": normalized_status,
                "start_count": data.get("start_count"),
                "remains": data.get("remains"),
                "charge": data.get("charge"),
                "raw": data,
            }
        except SMMProviderError:
            raise
        except Exception as e:
            raise SMMProviderError(
                f"فشل فحص حالة الطلب {order_id} "
                f"من {self.provider.name}: {e}"
            )

    async def check_multiple_orders(
        self, order_ids: list[str]
    ) -> dict:
        """
        يتحقق من حالة عدة طلبات دفعة واحدة.
        يرجع dict بمفتاح order_id وقيمة حالة الطلب.
        """
        try:
            data = await self._request({
                "action": "status",
                "orders": ",".join(order_ids),
            })
            return data
        except Exception as e:
            logger.warning(
                f"فشل فحص طلبات متعددة من "
                f"{self.provider.name}: {e}"
            )
            return {}
```

### `providers/sms_activate.py`

```python
"""
مزود أرقام SMS-Activate.
يعمل بنمط SMS-Activate الكلاسيكي (action-based).
https://sms-activate.org/
"""
import json
import logging
from decimal import Decimal

import aiohttp

from providers.base import BaseProvider, PurchasedNumber, OrderStatusResult
from config import settings

logger = logging.getLogger(__name__)

SMS_ACTIVATE_BASE = "https://api.sms-activate.org/stubs/handler_api.php"
SMS_ACTIVATE_RUB_TO_USD_RATE = Decimal("100")


class ProviderAPIError(Exception):
    pass


class SMSActivateProvider(BaseProvider):
    name = "sms_activate"

    def __init__(self):
        self.api_key = settings.SMS_ACTIVATE_API_KEY

    async def _request(self, params: dict) -> str:
        params = {"api_key": self.api_key, **params}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                SMS_ACTIVATE_BASE,
                params=params,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise ProviderAPIError(
                        f"SMS-Activate error {resp.status}: {text}"
                    )
                return text.strip()

    def _rub_to_usd(self, amount_rub: Decimal) -> Decimal:
        return (amount_rub / SMS_ACTIVATE_RUB_TO_USD_RATE).quantize(
            Decimal("0.0001")
        )

    async def get_balance(self) -> Decimal:
        result = await self._request({"action": "getBalance"})
        if result.startswith("ACCESS_BALANCE:"):
            balance_rub = Decimal(result.split(":")[1])
            return self._rub_to_usd(balance_rub)
        raise ProviderAPIError(
            f"استجابة غير متوقعة من SMS-Activate: {result}"
        )

    async def get_countries_services(self) -> list[dict]:
        raise NotImplementedError(
            "يُستخدم get_price مباشرة"
        )

    async def get_price(
        self, country: str, service: str
    ) -> Decimal | None:
        result = await self._request({
            "action": "getPrices",
            "country": country,
            "service": service,
        })
        try:
            data = json.loads(result)
            country_data = data.get(country, {}).get(service, {})
            if not country_data:
                return None
            first_operator = list(country_data.values())[0]
            cost = first_operator.get("cost")
            if cost is None:
                return None
            return self._rub_to_usd(Decimal(str(cost)))
        except Exception:
            return None

    async def buy_number(
        self,
        country: str,
        service: str,
        operator: str | None = None,
    ) -> PurchasedNumber:
        result = await self._request({
            "action": "getNumber",
            "service": service,
            "country": country,
        })
        if result.startswith("ACCESS_NUMBER:"):
            parts = result.split(":")
            order_id = parts[1]
            phone = parts[2]
            price = await self.get_price(country, service)
            cost_usd = price if price is not None else Decimal("0")
            return PurchasedNumber(
                provider_order_id=order_id,
                phone_number=phone,
                cost_usd=cost_usd,
                raw={"raw_response": result},
            )
        raise ProviderAPIError(
            f"فشل شراء رقم من SMS-Activate: {result}"
        )

    async def check_status(
        self, order_id: str
    ) -> OrderStatusResult:
        result = await self._request({
            "action": "getStatus",
            "id": order_id,
        })
        mapped = "pending"
        code = None

        if result.startswith("STATUS_OK:"):
            code = result.split(":")[1]
            mapped = "code_received"
        elif result == "STATUS_CANCEL":
            mapped = "cancelled"
        elif result.startswith("STATUS_WAIT_CODE"):
            mapped = "pending"
        elif result.startswith("STATUS_WAIT_RETRY"):
            mapped = "pending"

        return OrderStatusResult(
            status=mapped,
            sms_code=code,
            full_text=result,
            raw={"raw": result},
        )

    async def cancel_order(self, order_id: str) -> bool:
        try:
            await self._request({
                "action": "setStatus",
                "id": order_id,
                "status": 8,
            })
            return True
        except Exception as e:
            logger.error(
                f"فشل إلغاء الطلب {order_id} من SMS-Activate: {e}"
            )
            return False

    async def finish_order(self, order_id: str) -> bool:
        try:
            await self._request({
                "action": "setStatus",
                "id": order_id,
                "status": 6,
            })
            return True
        except Exception as e:
            logger.error(
                f"فشل إتمام الطلب {order_id} من SMS-Activate: {e}"
            )
            return False
```

### `providers/smshub.py`

```python
"""
مزود أرقام SMSHub.
يعمل بنمط SMS-Activate الكلاسيكي (action-based).
https://smshub.org/
"""
import json
import logging
from decimal import Decimal

import aiohttp

from providers.base import BaseProvider, PurchasedNumber, OrderStatusResult
from config import settings

logger = logging.getLogger(__name__)

SMSHUB_BASE = "https://smshub.org/stubs/handler_api.php"
SMSHUB_RUB_TO_USD_RATE = Decimal("100")


class ProviderAPIError(Exception):
    pass


class SMSHubProvider(BaseProvider):
    name = "smshub"

    def __init__(self):
        self.api_key = settings.SMSHUB_API_KEY

    async def _request(self, params: dict) -> str:
        params = {"api_key": self.api_key, **params}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                SMSHUB_BASE,
                params=params,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise ProviderAPIError(
                        f"SMSHub error {resp.status}: {text}"
                    )
                return text.strip()

    def _rub_to_usd(self, amount_rub: Decimal) -> Decimal:
        return (amount_rub / SMSHUB_RUB_TO_USD_RATE).quantize(
            Decimal("0.0001")
        )

    async def get_balance(self) -> Decimal:
        result = await self._request({"action": "getBalance"})
        if result.startswith("ACCESS_BALANCE:"):
            balance_rub = Decimal(result.split(":")[1])
            return self._rub_to_usd(balance_rub)
        raise ProviderAPIError(
            f"استجابة غير متوقعة من SMSHub: {result}"
        )

    async def get_countries_services(self) -> list[dict]:
        raise NotImplementedError(
            "يُستخدم get_price مباشرة"
        )

    async def get_price(
        self, country: str, service: str
    ) -> Decimal | None:
        result = await self._request({
            "action": "getPrices",
            "country": country,
            "service": service,
        })
        try:
            data = json.loads(result)
            country_data = data.get(country, {}).get(service, {})
            if not country_data:
                return None
            first_operator = list(country_data.values())[0]
            cost = first_operator.get("cost")
            if cost is None:
                return None
            return self._rub_to_usd(Decimal(str(cost)))
        except Exception:
            return None

    async def buy_number(
        self,
        country: str,
        service: str,
        operator: str | None = None,
    ) -> PurchasedNumber:
        result = await self._request({
            "action": "getNumber",
            "service": service,
            "country": country,
        })
        if result.startswith("ACCESS_NUMBER:"):
            parts = result.split(":")
            order_id = parts[1]
            phone = parts[2]
            price = await self.get_price(country, service)
            cost_usd = price if price is not None else Decimal("0")
            return PurchasedNumber(
                provider_order_id=order_id,
                phone_number=phone,
                cost_usd=cost_usd,
                raw={"raw_response": result},
            )
        raise ProviderAPIError(
            f"فشل شراء رقم من SMSHub: {result}"
        )

    async def check_status(
        self, order_id: str
    ) -> OrderStatusResult:
        result = await self._request({
            "action": "getStatus",
            "id": order_id,
        })
        mapped = "pending"
        code = None

        if result.startswith("STATUS_OK:"):
            code = result.split(":")[1]
            mapped = "code_received"
        elif result == "STATUS_CANCEL":
            mapped = "cancelled"
        elif result.startswith("STATUS_WAIT_CODE"):
            mapped = "pending"
        elif result.startswith("STATUS_WAIT_RETRY"):
            mapped = "pending"

        return OrderStatusResult(
            status=mapped,
            sms_code=code,
            full_text=result,
            raw={"raw": result},
        )

    async def cancel_order(self, order_id: str) -> bool:
        try:
            await self._request({
                "action": "setStatus",
                "id": order_id,
                "status": 8,
            })
            return True
        except Exception as e:
            logger.error(
                f"فشل إلغاء الطلب {order_id} من SMSHub: {e}"
            )
            return False

    async def finish_order(self, order_id: str) -> bool:
        try:
            await self._request({
                "action": "setStatus",
                "id": order_id,
                "status": 6,
            })
            return True
        except Exception as e:
            logger.error(
                f"فشل إتمام الطلب {order_id} من SMSHub: {e}"
            )
            return False
```

### `services/__init__.py`

```python

```

### `services/audit_service.py`

```python
"""
خدمة سجل تعديلات الأدمن (Audit Log).
تُستخدم لتسجيل كل عملية مهمة يقوم بها أي أدمن.

الفائدة:
- تتبع من عدل ماذا ومتى
- إمكانية استرجاع الأخطاء
- شفافية الإدارة عند وجود أكثر من أدمن
"""
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select, desc, and_
from sqlalchemy.orm import selectinload

from database.engine import async_session_maker
from database.models import AuditLog, AuditAction, User

logger = logging.getLogger(__name__)


class AuditService:
    """خدمة تسجيل وقراءة سجل تعديلات الأدمن."""

    @staticmethod
    def _serialize_value(value: Any) -> str | None:
        """يحول القيمة إلى نص قابل للحفظ."""
        if value is None:
            return None
        if isinstance(value, (str, int, bool)):
            return str(value)
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, (list, dict)):
            try:
                return json.dumps(value, ensure_ascii=False)
            except Exception:
                return str(value)
        return str(value)

    @staticmethod
    async def log(
        admin_id: int,
        action: AuditAction,
        entity_type: str,
        entity_id: int | None = None,
        entity_name: str | None = None,
        old_value: Any = None,
        new_value: Any = None,
        description: str | None = None,
        session=None,
    ) -> None:
        """
        يسجل عملية جديدة في السجل.

        Args:
            admin_id: آيدي الأدمن (users.id)
            action: نوع العملية (create/update/delete/إلخ)
            entity_type: نوع الكائن (category/product/provider/إلخ)
            entity_id: آيدي الكائن (اختياري)
            entity_name: اسم الكائن (اختياري)
            old_value: القيمة القديمة (اختياري)
            new_value: القيمة الجديدة (اختياري)
            description: وصف تفصيلي (اختياري)
            session: جلسة قاعدة بيانات (اختيارية)
        """
        try:
            audit_entry = AuditLog(
                admin_id=admin_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=(
                    entity_name[:255]
                    if entity_name else None
                ),
                old_value=(
                    AuditService._serialize_value(old_value)
                ),
                new_value=(
                    AuditService._serialize_value(new_value)
                ),
                description=(
                    description[:500]
                    if description else None
                ),
            )

            if session:
                session.add(audit_entry)
                await session.commit()
            else:
                async with async_session_maker() as new_session:
                    new_session.add(audit_entry)
                    await new_session.commit()

            logger.info(
                f"AUDIT: admin={admin_id} "
                f"action={action.value} "
                f"entity={entity_type}#{entity_id}"
            )
        except Exception as e:
            logger.error(f"فشل تسجيل Audit Log: {e}")

    @staticmethod
    async def log_create(
        admin_id: int,
        entity_type: str,
        entity_id: int,
        entity_name: str,
        new_value: Any = None,
        session=None,
    ) -> None:
        """اختصار لتسجيل عملية إنشاء."""
        await AuditService.log(
            admin_id=admin_id,
            action=AuditAction.CREATE,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            new_value=new_value,
            description=f"إنشاء {entity_type}: {entity_name}",
            session=session,
        )

    @staticmethod
    async def log_update(
        admin_id: int,
        entity_type: str,
        entity_id: int,
        entity_name: str,
        field: str,
        old_value: Any,
        new_value: Any,
        session=None,
    ) -> None:
        """اختصار لتسجيل عملية تعديل."""
        await AuditService.log(
            admin_id=admin_id,
            action=AuditAction.UPDATE,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            old_value={"field": field, "value": old_value},
            new_value={"field": field, "value": new_value},
            description=(
                f"تعديل {field} في {entity_type}: "
                f"{entity_name}"
            ),
            session=session,
        )

    @staticmethod
    async def log_delete(
        admin_id: int,
        entity_type: str,
        entity_id: int,
        entity_name: str,
        session=None,
    ) -> None:
        """اختصار لتسجيل عملية حذف."""
        await AuditService.log(
            admin_id=admin_id,
            action=AuditAction.DELETE,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            description=f"حذف {entity_type}: {entity_name}",
            session=session,
        )

    @staticmethod
    async def log_toggle(
        admin_id: int,
        entity_type: str,
        entity_id: int,
        entity_name: str,
        new_status: bool,
        session=None,
    ) -> None:
        """اختصار لتسجيل تفعيل/تعطيل."""
        action = (
            AuditAction.ACTIVATE if new_status
            else AuditAction.DEACTIVATE
        )
        status_ar = "تفعيل" if new_status else "تعطيل"
        await AuditService.log(
            admin_id=admin_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            new_value=str(new_status),
            description=(
                f"{status_ar} {entity_type}: {entity_name}"
            ),
            session=session,
        )

    @staticmethod
    async def log_price_change(
        admin_id: int,
        entity_type: str,
        entity_id: int,
        entity_name: str,
        old_price: Decimal,
        new_price: Decimal,
        session=None,
    ) -> None:
        """اختصار لتسجيل تغيير سعر."""
        change_percent = 0
        if old_price > 0:
            change_percent = (
                (new_price - old_price) / old_price * 100
            )

        await AuditService.log(
            admin_id=admin_id,
            action=AuditAction.PRICE_CHANGE,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            old_value=str(old_price),
            new_value=str(new_price),
            description=(
                f"تغيير سعر {entity_name} "
                f"من {old_price}$ إلى {new_price}$ "
                f"({change_percent:+.1f}%)"
            ),
            session=session,
        )

    @staticmethod
    async def log_sync(
        admin_id: int,
        entity_type: str,
        entity_id: int,
        entity_name: str,
        description: str,
        session=None,
    ) -> None:
        """اختصار لتسجيل عملية مزامنة."""
        await AuditService.log(
            admin_id=admin_id,
            action=AuditAction.SYNC,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            description=description,
            session=session,
        )

    @staticmethod
    async def get_recent_logs(
        limit: int = 50,
        offset: int = 0,
        admin_id: int | None = None,
        entity_type: str | None = None,
        action: AuditAction | None = None,
    ) -> list[AuditLog]:
        """يجلب آخر السجلات مع دعم الفلترة."""
        async with async_session_maker() as session:
            query = select(AuditLog).options(
                selectinload(AuditLog.admin)
            )

            filters = []
            if admin_id is not None:
                filters.append(AuditLog.admin_id == admin_id)
            if entity_type:
                filters.append(
                    AuditLog.entity_type == entity_type
                )
            if action:
                filters.append(AuditLog.action == action)

            if filters:
                query = query.where(and_(*filters))

            query = query.order_by(
                desc(AuditLog.created_at)
            ).limit(limit).offset(offset)

            result = await session.execute(query)
            return list(result.scalars().all())

    @staticmethod
    async def get_entity_history(
        entity_type: str,
        entity_id: int,
        limit: int = 20,
    ) -> list[AuditLog]:
        """يجلب كل تعديلات كائن معين."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(AuditLog)
                .options(selectinload(AuditLog.admin))
                .where(
                    and_(
                        AuditLog.entity_type == entity_type,
                        AuditLog.entity_id == entity_id,
                    )
                )
                .order_by(desc(AuditLog.created_at))
                .limit(limit)
            )
            return list(result.scalars().all())

    @staticmethod
    def format_log_entry(log: AuditLog) -> str:
        """يحول سجل إلى نص قابل للعرض."""
        action_emoji = {
            AuditAction.CREATE: "➕",
            AuditAction.UPDATE: "✏️",
            AuditAction.DELETE: "🗑",
            AuditAction.ACTIVATE: "🟢",
            AuditAction.DEACTIVATE: "🔴",
            AuditAction.SYNC: "🔄",
            AuditAction.PRICE_CHANGE: "💰",
            AuditAction.OTHER: "📝",
        }.get(log.action, "📝")

        admin_name = "غير معروف"
        if log.admin:
            admin_name = (
                log.admin.full_name
                or f"@{log.admin.username}"
                if log.admin.username
                else str(log.admin.telegram_id)
            )

        time_str = log.created_at.strftime("%Y-%m-%d %H:%M")

        text = (
            f"{action_emoji} <b>{log.action.value}</b>\n"
            f"👤 {admin_name}\n"
            f"📁 {log.entity_type}"
        )
        if log.entity_name:
            text += f" - {log.entity_name}"
        text += f"\n📅 {time_str}"

        if log.description:
            text += f"\n💬 {log.description}"

        return text
```

### `services/balance_service.py`

```python
"""
الخدمة المركزية الوحيدة المسموح فيها بتعديل رصيد أي مستخدم.
تستخدم قفل (asyncio.Lock) لكل مستخدم لمنع أي race condition.
العملة الداخلية: دولار أمريكي (USD) بالكامل.
"""
import asyncio
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select, desc

from database.models import User, Transaction, TransactionType


class InsufficientBalanceError(Exception):
    pass


class BalanceService:
    """
    ⚠️ القفل يعمل على مستوى العملية الواحدة فقط.
    لو تم توسيع الاستضافة لأكثر من instance يلزم قفل موزع عبر Redis.
    """
    _locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    @classmethod
    def _get_lock(cls, user_id: int) -> asyncio.Lock:
        return cls._locks[user_id]

    @classmethod
    def cleanup_idle_locks(cls) -> int:
        idle_user_ids = [
            uid for uid, lock in cls._locks.items()
            if not lock.locked()
        ]
        for uid in idle_user_ids:
            cls._locks.pop(uid, None)
        return len(idle_user_ids)

    @classmethod
    async def get_balance(cls, session, user_id: int) -> Decimal:
        """يجلب رصيد المستخدم الحالي بالدولار."""
        user = await session.get(User, user_id)
        if user is None:
            return Decimal("0")
        return user.balance

    @classmethod
    async def check_sufficient(
        cls, session, user_id: int, amount: Decimal
    ) -> bool:
        """
        يتحقق من كفاية الرصيد بدون خصم.
        يُستخدم لعرض رسالة الرصيد غير الكافي قبل بدء عملية الشراء.
        """
        balance = await cls.get_balance(session, user_id)
        return balance >= amount

    @classmethod
    async def add_balance(
        cls,
        session,
        user_id: int,
        amount: Decimal,
        tx_type: TransactionType,
        description: str | None = None,
        related_table: str | None = None,
        related_id: int | None = None,
    ) -> User:
        if amount <= 0:
            raise ValueError("المبلغ يجب أن يكون أكبر من صفر")

        async with cls._get_lock(user_id):
            user = await session.get(User, user_id)
            if user is None:
                raise ValueError(f"المستخدم {user_id} غير موجود")

            user.balance = user.balance + amount

            session.add(Transaction(
                user_id=user_id,
                type=tx_type,
                amount=amount,
                balance_after=user.balance,
                description=description,
                related_table=related_table,
                related_id=related_id,
            ))

            await session.commit()
            await session.refresh(user)
            return user

    @classmethod
    async def deduct_balance(
        cls,
        session,
        user_id: int,
        amount: Decimal,
        tx_type: TransactionType,
        description: str | None = None,
        related_table: str | None = None,
        related_id: int | None = None,
        is_purchase: bool = False,
    ) -> User:
        if amount <= 0:
            raise ValueError("المبلغ يجب أن يكون أكبر من صفر")

        async with cls._get_lock(user_id):
            user = await session.get(User, user_id)
            if user is None:
                raise ValueError(f"المستخدم {user_id} غير موجود")

            if user.balance < amount:
                raise InsufficientBalanceError(
                    f"رصيد غير كافٍ: المتاح {user.balance}$، المطلوب {amount}$"
                )

            user.balance = user.balance - amount

            if is_purchase:
                user.total_spent_usd = user.total_spent_usd + amount
                user.total_orders = user.total_orders + 1

            session.add(Transaction(
                user_id=user_id,
                type=tx_type,
                amount=-amount,
                balance_after=user.balance,
                description=description,
                related_table=related_table,
                related_id=related_id,
            ))

            await session.commit()
            await session.refresh(user)
            return user

    @classmethod
    async def get_transactions(
        cls,
        session,
        user_id: int,
        limit: int = 10,
        offset: int = 0,
    ) -> list[Transaction]:
        """يجلب سجل معاملات المستخدم مرتبة من الأحدث للأقدم."""
        result = await session.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(desc(Transaction.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
```

### `services/cashback_service.py`

```python
"""
خدمة الكاشباك.
تحسب وتضيف الكاشباك لرصيد المستخدم بعد كل شراء ناجح.
النسبة تُقرأ من إعدادات البوت وقابلة للتغيير من لوحة الأدمن.
"""
import logging
from decimal import Decimal

from database.models import TransactionType, CashbackLog
from services.balance_service import BalanceService
from services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class CashbackService:

    @staticmethod
    async def calculate_cashback(
        order_amount_usd: Decimal,
    ) -> Decimal:
        """
        يحسب مبلغ الكاشباك بالدولار.
        إذا كانت النسبة 0 يرجع 0 بدون استعلام إضافي.
        """
        percent = await SettingsService.get_decimal(
            "cashback_percent", Decimal("0")
        )
        if percent <= 0:
            return Decimal("0")

        cashback = order_amount_usd * (percent / Decimal("100"))
        return cashback.quantize(Decimal("0.0001"))

    @staticmethod
    async def apply_cashback(
        session,
        user_id: int,
        order_id: int,
        order_type: str,
        order_amount_usd: Decimal,
    ) -> Decimal:
        """
        يحسب ويضيف الكاشباك لرصيد المستخدم.
        يسجل العملية في cashback_logs.
        يرجع مبلغ الكاشباك المضاف (0 إذا لم يكن هناك كاشباك).
        """
        cashback_usd = await CashbackService.calculate_cashback(
            order_amount_usd
        )

        if cashback_usd <= 0:
            return Decimal("0")

        await BalanceService.add_balance(
            session=session,
            user_id=user_id,
            amount=cashback_usd,
            tx_type=TransactionType.CASHBACK,
            description=(
                f"كاشباك {order_type} #{order_id} "
                f"({order_amount_usd}$)"
            ),
            related_table=order_type,
            related_id=order_id,
        )

        session.add(CashbackLog(
            user_id=user_id,
            order_id=order_id,
            order_type=order_type,
            order_amount_usd=order_amount_usd,
            cashback_usd=cashback_usd,
        ))
        await session.commit()

        logger.info(
            f"كاشباك {cashback_usd}$ للمستخدم {user_id} "
            f"عن طلب {order_type} #{order_id}"
        )

        return cashback_usd

    @staticmethod
    async def get_user_total_cashback(
        session, user_id: int
    ) -> Decimal:
        """يجلب إجمالي الكاشباك الذي حصل عليه المستخدم."""
        from sqlalchemy import select, func
        result = await session.execute(
            select(func.coalesce(func.sum(CashbackLog.cashback_usd), 0))
            .where(CashbackLog.user_id == user_id)
        )
        return Decimal(str(result.scalar_one()))
```

### `services/coupon_service.py`

```python
"""
خدمة كوبونات الخصم.
تتحقق من صلاحية الكوبون وتحسب الخصم وتسجل الاستخدام.
"""
import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from database.models import Coupon, CouponUsage, TransactionType
from services.balance_service import BalanceService

logger = logging.getLogger(__name__)


class CouponError(Exception):
    pass


class CouponService:

    @staticmethod
    async def validate_coupon(
        session,
        code: str,
        user_id: int,
        order_amount_usd: Decimal,
    ) -> Coupon:
        """
        يتحقق من صلاحية الكوبون.
        يرمي CouponError مع رسالة واضحة إذا كان الكوبون غير صالح.
        """
        result = await session.execute(
            select(Coupon).where(Coupon.code == code.upper().strip())
        )
        coupon = result.scalar_one_or_none()

        if coupon is None:
            raise CouponError("❌ الكوبون غير موجود.")

        if not coupon.is_active:
            raise CouponError("❌ هذا الكوبون غير مفعل.")

        if coupon.expires_at and datetime.utcnow() > coupon.expires_at:
            raise CouponError("❌ انتهت صلاحية هذا الكوبون.")

        if coupon.used_count >= coupon.max_uses:
            raise CouponError("❌ تم استنفاد عدد استخدامات هذا الكوبون.")

        if order_amount_usd < coupon.min_order_usd:
            raise CouponError(
                f"❌ هذا الكوبون يتطلب حداً أدنى للطلب "
                f"{coupon.min_order_usd}$."
            )

        already_used = await session.execute(
            select(CouponUsage).where(
                CouponUsage.coupon_id == coupon.id,
                CouponUsage.user_id == user_id,
            )
        )
        if already_used.scalar_one_or_none():
            raise CouponError("❌ لقد استخدمت هذا الكوبون مسبقاً.")

        return coupon

    @staticmethod
    def calculate_discount(
        coupon: Coupon,
        order_amount_usd: Decimal,
    ) -> Decimal:
        """
        يحسب مبلغ الخصم بالدولار.
        discount_type: percent → خصم نسبة مئوية
        discount_type: fixed  → خصم مبلغ ثابت
        """
        if coupon.discount_type == "percent":
            discount = order_amount_usd * (
                coupon.discount_value / Decimal("100")
            )
        else:
            discount = coupon.discount_value

        return min(discount, order_amount_usd).quantize(
            Decimal("0.0001")
        )

    @staticmethod
    async def apply_coupon(
        session,
        coupon: Coupon,
        user_id: int,
        discount_applied: Decimal,
    ) -> None:
        """
        يسجل استخدام الكوبون ويزيد العداد.
        يُستدعى فقط بعد نجاح عملية الشراء.
        """
        coupon.used_count = coupon.used_count + 1

        session.add(CouponUsage(
            coupon_id=coupon.id,
            user_id=user_id,
            discount_applied=discount_applied,
        ))

        await session.commit()
        logger.info(
            f"تم تطبيق الكوبون {coupon.code} "
            f"للمستخدم {user_id} "
            f"بخصم {discount_applied}$"
        )

    @staticmethod
    async def get_coupon_by_code(
        session, code: str
    ) -> Coupon | None:
        result = await session.execute(
            select(Coupon).where(
                Coupon.code == code.upper().strip()
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_coupons(session) -> list[Coupon]:
        result = await session.execute(
            select(Coupon).order_by(Coupon.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_coupon(
        session,
        code: str,
        discount_type: str,
        discount_value: Decimal,
        max_uses: int,
        created_by: int,
        min_order_usd: Decimal = Decimal("0"),
        expires_at: datetime | None = None,
    ) -> Coupon:
        coupon = Coupon(
            code=code.upper().strip(),
            discount_type=discount_type,
            discount_value=discount_value,
            max_uses=max_uses,
            min_order_usd=min_order_usd,
            expires_at=expires_at,
            created_by=created_by,
            is_active=True,
        )
        session.add(coupon)
        await session.commit()
        await session.refresh(coupon)
        return coupon

    @staticmethod
    async def toggle_coupon(
        session, coupon_id: int
    ) -> Coupon | None:
        coupon = await session.get(Coupon, coupon_id)
        if coupon is None:
            return None
        coupon.is_active = not coupon.is_active
        await session.commit()
        await session.refresh(coupon)
        return coupon

    @staticmethod
    async def delete_coupon(session, coupon_id: int) -> bool:
        coupon = await session.get(Coupon, coupon_id)
        if coupon is None:
            return False
        await session.delete(coupon)
        await session.commit()
        return True
```

### `services/currency_service.py`

```python
"""
خدمة تحويل العملات.
تُستخدم لتحويل عملات المزودين إلى دولار.
"""
import logging
from decimal import Decimal, ROUND_HALF_UP

from services.settings_service import SettingsService

logger = logging.getLogger(__name__)


# ── أسعار صرف افتراضية (يمكن تحديثها من لوحة الأدمن) ──
DEFAULT_RATES_TO_USD = {
    "USD": Decimal("1"),
    "EUR": Decimal("1.08"),
    "RUB": Decimal("0.011"),
    "TRY": Decimal("0.03"),
    "IDR": Decimal("0.000064"),
    "INR": Decimal("0.012"),
    "PKR": Decimal("0.0036"),
    "BDT": Decimal("0.0091"),
    "SYP": Decimal("0.000067"),
    "SAR": Decimal("0.27"),
    "AED": Decimal("0.27"),
    "EGP": Decimal("0.020"),
    "IQD": Decimal("0.00076"),
    "JOD": Decimal("1.41"),
    "LBP": Decimal("0.000011"),
    "MAD": Decimal("0.10"),
    "DZD": Decimal("0.0075"),
    "TND": Decimal("0.32"),
    "LYD": Decimal("0.21"),
    "YER": Decimal("0.004"),
    "SDG": Decimal("0.0017"),
    "QAR": Decimal("0.27"),
    "OMR": Decimal("2.60"),
    "KWD": Decimal("3.25"),
    "BHD": Decimal("2.65"),
    "IRR": Decimal("0.000024"),
    "CNY": Decimal("0.14"),
    "GBP": Decimal("1.27"),
    "CAD": Decimal("0.73"),
    "AUD": Decimal("0.65"),
    "BRL": Decimal("0.20"),
    "MXN": Decimal("0.058"),
    "ARS": Decimal("0.001"),
    "COP": Decimal("0.00025"),
    "VND": Decimal("0.000041"),
    "THB": Decimal("0.029"),
    "PHP": Decimal("0.018"),
    "MYR": Decimal("0.22"),
    "SGD": Decimal("0.75"),
    "KRW": Decimal("0.00074"),
    "JPY": Decimal("0.0068"),
    "HKD": Decimal("0.13"),
    "TWD": Decimal("0.031"),
    "ZAR": Decimal("0.055"),
    "NGN": Decimal("0.00065"),
    "UAH": Decimal("0.025"),
    "PLN": Decimal("0.25"),
    "UZS": Decimal("0.000080"),
    "KZT": Decimal("0.0022"),
}


class CurrencyService:
    """خدمة تحويل العملات إلى دولار."""

    @staticmethod
    def get_default_rate(currency: str) -> Decimal:
        """يجلب سعر الصرف الافتراضي لعملة."""
        return DEFAULT_RATES_TO_USD.get(
            currency.upper(), Decimal("1")
        )

    @staticmethod
    async def get_rate_to_usd(
        currency: str, session=None
    ) -> Decimal:
        """
        يجلب سعر تحويل العملة إلى الدولار.
        أولاً من الإعدادات، ثم من القيم الافتراضية.
        """
        currency = currency.upper()

        if currency == "USD":
            return Decimal("1")

        setting_key = f"rate_{currency.lower()}_to_usd"
        rate_str = await SettingsService.get(setting_key)

        if rate_str:
            try:
                return Decimal(rate_str)
            except Exception:
                pass

        return CurrencyService.get_default_rate(currency)

    @staticmethod
    async def convert_to_usd(
        amount: Decimal,
        currency: str,
        session=None,
    ) -> Decimal:
        """
        يحول مبلغ من عملة معينة إلى دولار.
        """
        if currency.upper() == "USD":
            return amount

        rate = await CurrencyService.get_rate_to_usd(
            currency, session
        )
        result = amount * rate
        return result.quantize(
            Decimal("0.0001"),
            rounding=ROUND_HALF_UP,
        )

    @staticmethod
    def get_supported_currencies() -> list[str]:
        """يجلب قائمة العملات المدعومة."""
        return list(DEFAULT_RATES_TO_USD.keys())

    @staticmethod
    async def set_custom_rate(
        session,
        currency: str,
        rate: Decimal,
    ) -> None:
        """يحفظ سعر صرف مخصص لعملة."""
        currency = currency.upper()
        setting_key = f"rate_{currency.lower()}_to_usd"
        await SettingsService.set(session, setting_key, str(rate))
        logger.info(
            f"تم تحديث سعر الصرف: 1 {currency} = {rate} USD"
        )
```

### `services/dynamic_service.py`

```python
"""
خدمة النظام الديناميكي.
تجلب كل الأقسام والمنتجات والمزودين من قاعدة البيانات.
تُستخدم من القائمة الرئيسية وكل الهاندلرز لضمان أن كل شيء ديناميكي.
"""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.models import (
    Category, SubCategory, Product, ApiProvider,
    NumberService, StarsPackage, CategoryType,
    ProductStatus, ApiProviderType
)


class DynamicService:

    # ══════════════ الأقسام الرئيسية ══════════════

    @staticmethod
    async def get_active_categories(session) -> list[Category]:
        """يجلب كل الأقسام الرئيسية المفعلة مرتبة حسب sort_order."""
        result = await session.execute(
            select(Category)
            .where(Category.is_active == True)
            .order_by(Category.sort_order, Category.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_all_categories(session) -> list[Category]:
        """يجلب كل الأقسام (للأدمن)."""
        result = await session.execute(
            select(Category)
            .order_by(Category.sort_order, Category.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_category(session, category_id: int) -> Category | None:
        return await session.get(Category, category_id)

    @staticmethod
    async def create_category(
        session,
        name_ar: str,
        emoji: str,
        category_type: CategoryType,
        sort_order: int = 0,
    ) -> Category:
        category = Category(
            name_ar=name_ar,
            emoji=emoji,
            type=category_type,
            sort_order=sort_order,
            is_active=True,
        )
        session.add(category)
        await session.commit()
        await session.refresh(category)
        return category

    @staticmethod
    async def update_category(
        session,
        category_id: int,
        **kwargs,
    ) -> Category | None:
        category = await session.get(Category, category_id)
        if category is None:
            return None
        for key, value in kwargs.items():
            if hasattr(category, key):
                setattr(category, key, value)
        await session.commit()
        await session.refresh(category)
        return category

    @staticmethod
    async def delete_category(session, category_id: int) -> bool:
        category = await session.get(Category, category_id)
        if category is None:
            return False
        await session.delete(category)
        await session.commit()
        return True

    # ══════════════ الأقسام الفرعية ══════════════

    @staticmethod
    async def get_active_sub_categories(
        session, category_id: int
    ) -> list[SubCategory]:
        """يجلب الأقسام الفرعية المفعلة لقسم رئيسي معين."""
        result = await session.execute(
            select(SubCategory)
            .where(
                SubCategory.category_id == category_id,
                SubCategory.is_active == True,
            )
            .order_by(SubCategory.sort_order, SubCategory.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_all_sub_categories(
        session, category_id: int
    ) -> list[SubCategory]:
        """يجلب كل الأقسام الفرعية لقسم رئيسي (للأدمن)."""
        result = await session.execute(
            select(SubCategory)
            .where(SubCategory.category_id == category_id)
            .order_by(SubCategory.sort_order, SubCategory.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_sub_category(
        session, sub_category_id: int
    ) -> SubCategory | None:
        return await session.get(SubCategory, sub_category_id)

    @staticmethod
    async def create_sub_category(
        session,
        category_id: int,
        name_ar: str,
        emoji: str,
        description: str | None = None,
        sort_order: int = 0,
    ) -> SubCategory:
        sub = SubCategory(
            category_id=category_id,
            name_ar=name_ar,
            emoji=emoji,
            description=description,
            sort_order=sort_order,
            is_active=True,
        )
        session.add(sub)
        await session.commit()
        await session.refresh(sub)
        return sub

    @staticmethod
    async def update_sub_category(
        session,
        sub_category_id: int,
        **kwargs,
    ) -> SubCategory | None:
        sub = await session.get(SubCategory, sub_category_id)
        if sub is None:
            return None
        for key, value in kwargs.items():
            if hasattr(sub, key):
                setattr(sub, key, value)
        await session.commit()
        await session.refresh(sub)
        return sub

    @staticmethod
    async def delete_sub_category(
        session, sub_category_id: int
    ) -> bool:
        sub = await session.get(SubCategory, sub_category_id)
        if sub is None:
            return False
        await session.delete(sub)
        await session.commit()
        return True

    # ══════════════ المنتجات ══════════════

    @staticmethod
    async def get_active_products(
        session, sub_category_id: int
    ) -> list[Product]:
        """يجلب المنتجات المفعلة لقسم فرعي معين."""
        result = await session.execute(
            select(Product)
            .where(
                Product.sub_category_id == sub_category_id,
                Product.status == ProductStatus.ACTIVE,
            )
            .order_by(Product.sort_order, Product.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_all_products(
        session, sub_category_id: int
    ) -> list[Product]:
        """يجلب كل منتجات قسم فرعي (للأدمن)."""
        result = await session.execute(
            select(Product)
            .where(Product.sub_category_id == sub_category_id)
            .order_by(Product.sort_order, Product.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_product(session, product_id: int) -> Product | None:
        result = await session.execute(
            select(Product)
            .where(Product.id == product_id)
            .options(
                selectinload(Product.sub_category),
                selectinload(Product.api_provider),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_product(
        session,
        sub_category_id: int,
        name_ar: str,
        price_usd: Decimal,
        cost_price_usd: Decimal = Decimal("0"),
        api_provider_id: int | None = None,
        provider_service_id: str | None = None,
        description: str | None = None,
        min_quantity: int = 1,
        max_quantity: int = 1,
        requires_player_id: bool = False,
        requires_link: bool = False,
        requires_quantity: bool = False,
        sort_order: int = 0,
    ) -> Product:
        product = Product(
            sub_category_id=sub_category_id,
            name_ar=name_ar,
            price_usd=price_usd,
            cost_price_usd=cost_price_usd,
            api_provider_id=api_provider_id,
            provider_service_id=provider_service_id,
            description=description,
            min_quantity=min_quantity,
            max_quantity=max_quantity,
            requires_player_id=requires_player_id,
            requires_link=requires_link,
            requires_quantity=requires_quantity,
            sort_order=sort_order,
            status=ProductStatus.ACTIVE,
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)
        return product

    @staticmethod
    async def update_product(
        session,
        product_id: int,
        **kwargs,
    ) -> Product | None:
        product = await session.get(Product, product_id)
        if product is None:
            return None
        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)
        await session.commit()
        await session.refresh(product)
        return product

    @staticmethod
    async def delete_product(session, product_id: int) -> bool:
        product = await session.get(Product, product_id)
        if product is None:
            return False
        await session.delete(product)
        await session.commit()
        return True

    @staticmethod
    async def increment_product_sold(
        session, product_id: int, quantity: int = 1
    ) -> None:
        """يزيد عداد المبيعات عند كل عملية شراء ناجحة."""
        product = await session.get(Product, product_id)
        if product:
            product.total_sold = product.total_sold + quantity
            await session.commit()

    # ══════════════ مزودو API (ألعاب/SMM) ══════════════

    @staticmethod
    async def get_active_providers(
        session,
        provider_type: ApiProviderType | None = None,
    ) -> list[ApiProvider]:
        """يجلب المزودين المفعلين مرتبين حسب الأولوية."""
        query = select(ApiProvider).where(ApiProvider.is_active == True)
        if provider_type:
            query = query.where(ApiProvider.type == provider_type)
        query = query.order_by(ApiProvider.priority, ApiProvider.id)
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_all_providers(session) -> list[ApiProvider]:
        """يجلب كل المزودين (للأدمن)."""
        result = await session.execute(
            select(ApiProvider)
            .order_by(ApiProvider.type, ApiProvider.priority)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_provider(
        session, provider_id: int
    ) -> ApiProvider | None:
        return await session.get(ApiProvider, provider_id)

    @staticmethod
    async def create_provider(
        session,
        name: str,
        provider_type: ApiProviderType,
        api_url: str,
        api_key: str,
        priority: int = 1,
        low_balance_threshold: Decimal = Decimal("10"),
    ) -> ApiProvider:
        provider = ApiProvider(
            name=name,
            type=provider_type,
            api_url=api_url,
            api_key=api_key,
            priority=priority,
            low_balance_threshold=low_balance_threshold,
            is_active=True,
        )
        session.add(provider)
        await session.commit()
        await session.refresh(provider)
        return provider

    @staticmethod
    async def update_provider(
        session,
        provider_id: int,
        **kwargs,
    ) -> ApiProvider | None:
        provider = await session.get(ApiProvider, provider_id)
        if provider is None:
            return None
        for key, value in kwargs.items():
            if hasattr(provider, key):
                setattr(provider, key, value)
        await session.commit()
        await session.refresh(provider)
        return provider

    @staticmethod
    async def delete_provider(session, provider_id: int) -> bool:
        provider = await session.get(ApiProvider, provider_id)
        if provider is None:
            return False
        await session.delete(provider)
        await session.commit()
        return True

    # ══════════════ خدمات الأرقام الديناميكية ══════════════

    @staticmethod
    async def get_active_number_services(
        session,
    ) -> list[NumberService]:
        """يجلب خدمات الأرقام المفعلة مرتبة حسب sort_order."""
        result = await session.execute(
            select(NumberService)
            .where(NumberService.is_active == True)
            .order_by(NumberService.sort_order, NumberService.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_all_number_services(session) -> list[NumberService]:
        """يجلب كل خدمات الأرقام (للأدمن)."""
        result = await session.execute(
            select(NumberService)
            .order_by(NumberService.sort_order, NumberService.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_number_service_by_code(
        session, code: str
    ) -> NumberService | None:
        result = await session.execute(
            select(NumberService)
            .where(NumberService.code == code)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_number_service(
        session,
        code: str,
        name_ar: str,
        emoji: str,
        fivesim_code: str | None = None,
        herosms_code: str | None = None,
        sms_activate_code: str | None = None,
        smshub_code: str | None = None,
        sort_order: int = 0,
    ) -> NumberService:
        svc = NumberService(
            code=code,
            name_ar=name_ar,
            emoji=emoji,
            fivesim_code=fivesim_code,
            herosms_code=herosms_code,
            sms_activate_code=sms_activate_code,
            smshub_code=smshub_code,
            sort_order=sort_order,
            is_active=True,
        )
        session.add(svc)
        await session.commit()
        await session.refresh(svc)
        return svc

    @staticmethod
    async def update_number_service(
        session,
        service_id: int,
        **kwargs,
    ) -> NumberService | None:
        svc = await session.get(NumberService, service_id)
        if svc is None:
            return None
        for key, value in kwargs.items():
            if hasattr(svc, key):
                setattr(svc, key, value)
        await session.commit()
        await session.refresh(svc)
        return svc

    @staticmethod
    async def delete_number_service(
        session, service_id: int
    ) -> bool:
        svc = await session.get(NumberService, service_id)
        if svc is None:
            return False
        await session.delete(svc)
        await session.commit()
        return True

    # ══════════════ باقات النجوم ══════════════

    @staticmethod
    async def get_active_stars_packages(
        session,
    ) -> list[StarsPackage]:
        """يجلب باقات النجوم المفعلة مرتبة حسب sort_order."""
        result = await session.execute(
            select(StarsPackage)
            .where(StarsPackage.is_active == True)
            .order_by(StarsPackage.sort_order, StarsPackage.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_all_stars_packages(session) -> list[StarsPackage]:
        """يجلب كل باقات النجوم (للأدمن)."""
        result = await session.execute(
            select(StarsPackage)
            .order_by(StarsPackage.sort_order, StarsPackage.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_stars_package(
        session, package_id: int
    ) -> StarsPackage | None:
        return await session.get(StarsPackage, package_id)

    @staticmethod
    async def create_stars_package(
        session,
        stars_amount: int,
        usd_amount: Decimal,
        label: str,
        sort_order: int = 0,
    ) -> StarsPackage:
        pkg = StarsPackage(
            stars_amount=stars_amount,
            usd_amount=usd_amount,
            label=label,
            sort_order=sort_order,
            is_active=True,
        )
        session.add(pkg)
        await session.commit()
        await session.refresh(pkg)
        return pkg

    @staticmethod
    async def update_stars_package(
        session,
        package_id: int,
        **kwargs,
    ) -> StarsPackage | None:
        pkg = await session.get(StarsPackage, package_id)
        if pkg is None:
            return None
        for key, value in kwargs.items():
            if hasattr(pkg, key):
                setattr(pkg, key, value)
        await session.commit()
        await session.refresh(pkg)
        return pkg

    @staticmethod
    async def delete_stars_package(
        session, package_id: int
    ) -> bool:
        pkg = await session.get(StarsPackage, package_id)
        if pkg is None:
            return False
        await session.delete(pkg)
        await session.commit()
        return True
```

### `services/notification_service.py`

```python
"""
خدمة الإشعارات المركزية.

مسؤوليات هذا الملف:
1) إرسال إشعارات للأدمن (قناة خاصة).
2) إرسال إشعارات للقناة العامة (عمليات ناجحة).
3) إرسال إشعارات للمستخدمين.
4) إرسال إشعارات البكاب.
5) إخفاء اسم المستخدم جزئياً في القناة العامة.
"""
import logging
from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from services.settings_service import SettingsService

logger = logging.getLogger(__name__)


def _mask_username(username: str | None, full_name: str | None) -> str:
    """
    يخفي اسم المستخدم جزئياً للقناة العامة.
    مثال: "Ahmed Ali" → "Ah***Ali"
    مثال: "@sanad" → "@sa***"
    """
    name = username or full_name or "مستخدم"
    if len(name) <= 3:
        return name[0] + "***"
    visible_start = name[:2]
    visible_end = name[-2:] if len(name) > 4 else ""
    return f"{visible_start}***{visible_end}"


class NotificationService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def notify_admin(
        self,
        text: str,
        reply_markup=None,
        parse_mode: str = "HTML"
    ) -> int | None:
        """
        يرسل إشعاراً نصياً لقناة الأدمن.
        يرجع message_id إذا نجح، أو None إذا فشل.
        """
        from config import settings
        chat_id = settings.ADMIN_NOTIFY_CHAT_ID
        if not chat_id:
            logger.error("ADMIN_NOTIFY_CHAT_ID غير محدد في .env")
            return None
        try:
            sent = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return sent.message_id
        except TelegramForbiddenError:
            logger.error(
                f"البوت محظور أو ليس أدمن في قناة الأدمن (chat_id={chat_id}). "
                "تأكد أن البوت أدمن في القناة."
            )
            return None
        except TelegramBadRequest as e:
            logger.error(f"خطأ في إرسال إشعار الأدمن (chat_id={chat_id}): {e}")
            return None
        except Exception as e:
            logger.error(f"خطأ غير متوقع في إرسال إشعار الأدمن: {e}")
            return None

    async def notify_admin_photo(
        self,
        photo_file_id: str,
        caption: str,
        reply_markup=None,
        parse_mode: str = "HTML"
    ) -> int | None:
        """
        يرسل إشعاراً بصورة لقناة الأدمن.
        يرجع message_id إذا نجح، أو None إذا فشل.
        """
        from config import settings
        chat_id = settings.ADMIN_NOTIFY_CHAT_ID
        if not chat_id:
            logger.error("ADMIN_NOTIFY_CHAT_ID غير محدد في .env")
            return None
        try:
            sent = await self.bot.send_photo(
                chat_id=chat_id,
                photo=photo_file_id,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return sent.message_id
        except TelegramForbiddenError:
            logger.error(
                f"البوت محظور أو ليس أدمن في قناة الأدمن (chat_id={chat_id}). "
                "تأكد أن البوت أدمن في القناة."
            )
            return None
        except TelegramBadRequest as e:
            logger.error(f"خطأ في إرسال صورة إشعار الأدمن (chat_id={chat_id}): {e}")
            return None
        except Exception as e:
            logger.error(f"خطأ غير متوقع في إرسال صورة إشعار الأدمن: {e}")
            return None

    async def notify_user(
        self,
        telegram_id: int,
        text: str,
        reply_markup=None,
        parse_mode: str = "HTML"
    ) -> bool:
        """
        يرسل إشعاراً للمستخدم.
        يرجع True إذا نجح، False إذا فشل.
        """
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return True
        except TelegramForbiddenError:
            logger.warning(
                f"المستخدم {telegram_id} حظر البوت، تخطي الإشعار."
            )
            return False
        except TelegramBadRequest as e:
            logger.warning(
                f"خطأ في إرسال إشعار للمستخدم {telegram_id}: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"خطأ غير متوقع في إرسال إشعار للمستخدم {telegram_id}: {e}"
            )
            return False

    async def notify_public_channel(
        self,
        text: str,
        parse_mode: str = "HTML"
    ) -> bool:
        """
        يرسل إشعار عملية ناجحة للقناة العامة.
        يرجع True إذا نجح، False إذا فشل أو القناة غير محددة.
        """
        channel_id_str = await SettingsService.get("public_channel_id", "0")
        try:
            channel_id = int(channel_id_str)
        except (ValueError, TypeError):
            channel_id = 0

        if not channel_id:
            return False

        try:
            await self.bot.send_message(
                chat_id=channel_id,
                text=text,
                parse_mode=parse_mode,
            )
            return True
        except TelegramForbiddenError:
            logger.error(
                f"البوت محظور أو ليس أدمن في القناة العامة (chat_id={channel_id})."
            )
            return False
        except TelegramBadRequest as e:
            logger.error(f"خطأ في إرسال إشعار للقناة العامة: {e}")
            return False
        except Exception as e:
            logger.error(f"خطأ غير متوقع في إرسال إشعار للقناة العامة: {e}")
            return False

    async def notify_backup_channel(
        self,
        document_bytes: bytes,
        filename: str,
        caption: str,
    ) -> bool:
        """
        يرسل ملف البكاب لقناة البكاب.
        يرجع True إذا نجح، False إذا فشل.
        """
        channel_id_str = await SettingsService.get("backup_channel_id", "0")
        try:
            channel_id = int(channel_id_str)
        except (ValueError, TypeError):
            channel_id = 0

        if not channel_id:
            logger.warning("backup_channel_id غير محدد، تخطي البكاب.")
            return False

        try:
            from aiogram.types import BufferedInputFile
            file = BufferedInputFile(document_bytes, filename=filename)
            await self.bot.send_document(
                chat_id=channel_id,
                document=file,
                caption=caption,
            )
            return True
        except Exception as e:
            logger.error(f"خطأ في إرسال البكاب: {e}")
            return False

    async def notify_successful_number_order(
        self,
        username: str | None,
        full_name: str | None,
        service_name: str,
        price_usd: str,
    ) -> None:
        """
        يرسل إشعار شراء رقم ناجح للقناة العامة.
        """
        masked = _mask_username(username, full_name)
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        text = (
            "✅ <b>عملية شراء ناجحة!</b>\n\n"
            f"👤 المستخدم: {masked}\n"
            f"📞 الخدمة: {service_name}\n"
            f"💰 المبلغ: {price_usd}$\n"
            f"📅 التاريخ: {now} UTC"
        )
        await self.notify_public_channel(text)

    async def notify_successful_unified_order(
        self,
        username: str | None,
        full_name: str | None,
        product_name: str,
        price_usd: str,
    ) -> None:
        """
        يرسل إشعار شراء منتج (لعبة/تطبيق/SMM) ناجح للقناة العامة.
        """
        masked = _mask_username(username, full_name)
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        text = (
            "✅ <b>عملية شراء ناجحة!</b>\n\n"
            f"👤 المستخدم: {masked}\n"
            f"🛒 المنتج: {product_name}\n"
            f"💰 المبلغ: {price_usd}$\n"
            f"📅 التاريخ: {now} UTC"
        )
        await self.notify_public_channel(text)

    async def notify_provider_low_balance(
        self,
        provider_name: str,
        balance: str,
        threshold: str,
    ) -> None:
        """
        يرسل تنبيه لقناة الأدمن عند انخفاض رصيد مزود عن الحد المحدد.
        """
        text = (
            "⚠️ <b>تنبيه: رصيد منخفض!</b>\n\n"
            f"🔌 المزود: {provider_name}\n"
            f"💰 الرصيد الحالي: {balance}$\n"
            f"🚨 الحد الأدنى المحدد: {threshold}$\n\n"
            "يرجى شحن رصيد المزود في أقرب وقت."
        )
        await self.notify_admin(text)

    async def notify_provider_offline(
        self,
        provider_name: str,
        error: str,
    ) -> None:
        """
        يرسل تنبيه لقناة الأدمن عند توقف مزود عن الاستجابة.
        """
        text = (
            "🔴 <b>تنبيه: مزود غير متاح!</b>\n\n"
            f"🔌 المزود: {provider_name}\n"
            f"⚠️ الخطأ: {error[:200]}\n\n"
            "تم تعطيل المزود تلقائياً حتى يعود للعمل."
        )
        await self.notify_admin(text)

    async def notify_new_deposit(
        self,
        user_telegram_id: int,
        username: str | None,
        amount_usd: str,
        tx_number: str,
        deposit_id: int,
        photo_file_id: str,
        reply_markup,
    ) -> int | None:
        """
        يرسل إشعار إيداع جديد لقناة الأدمن مع صورة الإثبات وأزرار القبول/الرفض.
        يرجع message_id الرسالة في القناة.
        """
        caption = (
            "🆕 <b>طلب شحن رصيد جديد</b>\n\n"
            f"👤 المستخدم: {user_telegram_id}"
            f" (@{username or '-'})\n"
            f"💵 المبلغ: <b>{amount_usd}$</b>\n"
            f"🔢 رقم العملية: <code>{tx_number}</code>\n"
            f"🆔 رقم الطلب: #{deposit_id}\n"
            f"⏰ الوقت: "
            f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"
        )
        return await self.notify_admin_photo(
            photo_file_id=photo_file_id,
            caption=caption,
            reply_markup=reply_markup,
        )

    async def notify_deposit_approved(
        self,
        user_telegram_id: int,
        amount_usd: str,
    ) -> None:
        """يرسل إشعار قبول الإيداع للمستخدم."""
        await self.notify_user(
            telegram_id=user_telegram_id,
            text=(
                "✅ <b>تم قبول طلب شحن رصيدك!</b>\n\n"
                f"💰 تمت إضافة <b>{amount_usd}$</b> إلى رصيدك.\n"
                "يمكنك الآن استخدام رصيدك لشراء الخدمات."
            ),
        )

    async def notify_deposit_rejected(
        self,
        user_telegram_id: int,
        reason: str | None = None,
    ) -> None:
        """يرسل إشعار رفض الإيداع للمستخدم."""
        text = (
            "❌ <b>تم رفض طلب شحن رصيدك</b>\n\n"
        )
        if reason:
            text += f"📝 السبب: {reason}\n\n"
        text += (
            "يرجى التأكد من صحة بيانات التحويل "
            "والمحاولة مجدداً، أو التواصل مع الدعم الفني."
        )
        await self.notify_user(
            telegram_id=user_telegram_id,
            text=text,
        )

    async def notify_order_completed(
        self,
        user_telegram_id: int,
        product_name: str,
        result_text: str,
    ) -> None:
        """يرسل إشعار اكتمال طلب للمستخدم."""
        await self.notify_user(
            telegram_id=user_telegram_id,
            text=(
                "✅ <b>تم تنفيذ طلبك بنجاح!</b>\n\n"
                f"🛒 المنتج: {product_name}\n\n"
                f"{result_text}"
            ),
        )

    async def notify_order_failed(
        self,
        user_telegram_id: int,
        product_name: str,
        amount_usd: str,
    ) -> None:
        """يرسل إشعار فشل طلب مع استرجاع الرصيد للمستخدم."""
        await self.notify_user(
            telegram_id=user_telegram_id,
            text=(
                "❌ <b>فشل تنفيذ طلبك</b>\n\n"
                f"🛒 المنتج: {product_name}\n"
                f"💰 تم استرجاع <b>{amount_usd}$</b> "
                "إلى رصيدك تلقائياً."
            ),
        )

    async def notify_insufficient_balance(
        self,
        user_telegram_id: int,
        required_usd: str,
        current_balance_usd: str,
        reply_markup=None,
    ) -> None:
        """يرسل إشعار رصيد غير كافٍ للمستخدم مع زر شحن الرصيد."""
        await self.notify_user(
            telegram_id=user_telegram_id,
            text=(
                "⚠️ <b>رصيدك غير كافٍ!</b>\n\n"
                f"💰 رصيدك الحالي: <b>{current_balance_usd}$</b>\n"
                f"💵 المبلغ المطلوب: <b>{required_usd}$</b>\n\n"
                "اشحن رصيدك للمتابعة."
            ),
            reply_markup=reply_markup,
        )

    async def notify_large_order_confirmation(
        self,
        user_telegram_id: int,
        product_name: str,
        amount_usd: str,
        reply_markup,
    ) -> None:
        """يطلب تأكيد الطلبات الكبيرة من المستخدم."""
        await self.notify_user(
            telegram_id=user_telegram_id,
            text=(
                "⚠️ <b>تأكيد الطلب</b>\n\n"
                f"🛒 المنتج: {product_name}\n"
                f"💰 المبلغ: <b>{amount_usd}$</b>\n\n"
                "هذا طلب بمبلغ كبير. هل أنت متأكد من المتابعة؟"
            ),
            reply_markup=reply_markup,
        )
```

### `services/plisio_service.py`

```python
"""
عميل Plisio API لمعالجة مدفوعات USDT التلقائية.

بديل نظيف عن Cryptomus:
- بدون KYC
- يدعم عدة عملات (USDT_TRX, USDT_BSC, BNB)
- Polling للتحقق من الحالة
- واجهة متوافقة مع الكود القديم
"""
import asyncio
import logging
from decimal import Decimal
from typing import Any

import aiohttp

from config import settings

logger = logging.getLogger(__name__)


class PlisioError(Exception):
    """خطأ عام في Plisio."""
    pass


class PlisioConnectionError(PlisioError):
    """خطأ اتصال مع Plisio."""
    pass


class PlisioAPIError(PlisioError):
    """خطأ من Plisio API."""
    pass


class PlisioClient:
    """
    عميل Plisio API.

    الاستخدام:
        client = PlisioClient()
        invoice = await client.create_payment(
            amount=10.5,
            order_id="user_123_1234567890",
            currency="USDT_TRX",
        )
        status = await client.get_payment_info(invoice["uuid"])
    """

    BASE_URL = "https://api.plisio.net/api/v1"

    # حالات Plisio والمقابل لها في نظامنا
    PAID_STATUSES = {"completed", "mismatch"}
    FAILED_STATUSES = {"error", "expired", "cancelled"}
    PENDING_STATUSES = {"new", "pending", "confirming"}

    def __init__(self):
        self.secret_key = settings.PLISIO_SECRET_KEY
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """يحصل على session نشطة."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def close(self):
        """يغلق الـ session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
    ) -> dict:
        """
        يرسل طلب لـ Plisio API.

        Args:
            method: GET أو POST
            endpoint: مسار الـ API
            params: البيانات

        Returns:
            رد Plisio كـ dict
        """
        url = f"{self.BASE_URL}{endpoint}"

        if params is None:
            params = {}
        params["api_key"] = self.secret_key

        try:
            session = await self._get_session()

            if method == "GET":
                async with session.get(
                    url, params=params
                ) as response:
                    data = await response.json()
            else:
                async with session.post(
                    url, data=params
                ) as response:
                    data = await response.json()

            if data.get("status") == "error":
                error_msg = data.get(
                    "data", {}
                ).get("message", "Unknown error")
                logger.error(
                    f"Plisio API error: {error_msg}"
                )
                raise PlisioAPIError(error_msg)

            return data.get("data", {})

        except aiohttp.ClientError as e:
            logger.error(f"Plisio connection error: {e}")
            raise PlisioConnectionError(
                f"فشل الاتصال بـ Plisio: {e}"
            )
        except asyncio.TimeoutError:
            logger.error("Plisio request timeout")
            raise PlisioConnectionError(
                "انتهت مهلة الاتصال بـ Plisio"
            )
        except Exception as e:
            logger.error(
                f"Plisio unexpected error: {e}"
            )
            raise PlisioError(str(e))

    async def create_payment(
        self,
        amount: Decimal | float | str,
        order_id: str,
        currency: str = "USDT_TRX",
        order_name: str | None = None,
        callback_url: str | None = None,
        email: str | None = None,
        lifetime: int = 1800,
    ) -> dict:
        """
        ينشئ فاتورة دفع جديدة.

        Args:
            amount: المبلغ (بالدولار)
            order_id: معرف الطلب الفريد
            currency: العملة (USDT_TRX, USDT_BSC, BNB)
            order_name: اسم الطلب
            callback_url: رابط الـ callback (اختياري)
            email: بريد العميل (اختياري)
            lifetime: مدة الصلاحية بالثواني (افتراضي: 30 دقيقة)

        Returns:
            dict فيها:
            - uuid: معرف الفاتورة في Plisio
            - address: عنوان الدفع
            - amount: المبلغ المطلوب
            - invoice_total_sum: المبلغ الإجمالي
            - expected_confirmations: عدد التأكيدات
            - qr_code: QR code
            - invoice_url: رابط صفحة الفاتورة
            - expire_utc: وقت الانتهاء
        """
        params = {
            "source_amount": str(amount),
            "source_currency": "USD",
            "order_number": order_id,
            "currency": currency,
        }

        if order_name:
            params["order_name"] = order_name
        else:
            params["order_name"] = f"Deposit {order_id}"

        if callback_url:
            params["callback_url"] = callback_url

        if email:
            params["email"] = email

        result = await self._request(
            "GET", "/invoices/new", params
        )

        # تحويل الاستجابة لتتوافق مع الواجهة القديمة
        # (لسهولة استبدال Cryptomus بدون تعديل الكود القديم)
        return {
            "uuid": result.get("txn_id"),
            "address": result.get("wallet_hash"),
            "amount": result.get("amount"),
            "payer_amount": result.get("amount"),
            "currency": result.get("currency"),
            "network": self._get_network_name(currency),
            "url": result.get("invoice_url"),
            "qr_code": result.get("qr_code"),
            "expired_at": result.get("expire_utc"),
            "raw": result,
        }

    async def get_payment_info(
        self, uuid: str
    ) -> dict:
        """
        يجلب معلومات فاتورة.

        Args:
            uuid: معرف الفاتورة (txn_id في Plisio)

        Returns:
            dict فيها:
            - status: حالة الفاتورة
            - amount: المبلغ
            - address: العنوان
            - confirmations: عدد التأكيدات
            - وغيرها
        """
        result = await self._request(
            "GET", f"/operations/{uuid}"
        )

        # تحويل الاستجابة لتتوافق مع Cryptomus
        status_map = {
            "completed": "paid",
            "mismatch": "paid",
            "new": "process",
            "pending": "process",
            "confirming": "check",
            "expired": "cancel",
            "cancelled": "cancel",
            "error": "fail",
        }

        plisio_status = result.get("status", "new")
        mapped_status = status_map.get(
            plisio_status, plisio_status
        )

        return {
            "status": mapped_status,
            "uuid": result.get("id"),
            "amount": result.get("amount"),
            "address": result.get("wallet_hash"),
            "confirmations": result.get(
                "confirmations", 0
            ),
            "raw": result,
        }

    def is_paid_status(self, status: str) -> bool:
        """يتحقق إذا كانت الحالة تعني الدفع الناجح."""
        return status in {"paid", "completed", "mismatch"}

    def is_failed_status(self, status: str) -> bool:
        """يتحقق إذا كانت الحالة تعني الفشل."""
        return status in {
            "fail", "cancel", "expired", "error", "cancelled"
        }

    def is_pending_status(self, status: str) -> bool:
        """يتحقق إذا كانت الحالة تعني الانتظار."""
        return status in {
            "process", "check", "new", "pending",
            "confirming",
        }

    def _get_network_name(self, currency: str) -> str:
        """يحول رمز العملة لاسم الشبكة."""
        network_map = {
            "USDT_TRX": "TRC20",
            "USDT_BSC": "BEP20",
            "USDT_ETH": "ERC20",
            "BNB": "BEP20",
            "BTC": "BTC",
            "ETH": "ERC20",
        }
        return network_map.get(currency, currency)

    async def get_supported_currencies(self) -> list:
        """يجلب قائمة العملات المدعومة."""
        try:
            result = await self._request(
                "GET", "/currencies"
            )
            return result if isinstance(
                result, list
            ) else []
        except Exception as e:
            logger.error(
                f"فشل جلب العملات: {e}"
            )
            return []

    async def get_balance(
        self, currency: str = "USDT_TRX"
    ) -> Decimal:
        """
        يجلب رصيد محفظتك في Plisio.

        Args:
            currency: العملة

        Returns:
            الرصيد كـ Decimal
        """
        try:
            result = await self._request(
                "GET",
                "/balances",
                {"currency": currency},
            )
            balance = result.get("balance", "0")
            return Decimal(str(balance))
        except Exception as e:
            logger.error(
                f"فشل جلب الرصيد: {e}"
            )
            return Decimal("0")


# ══════════════════════════════════════════════
# ══════════════ Instance جاهز للاستخدام ══════════════
# ══════════════════════════════════════════════

plisio_client = PlisioClient()

# للتوافق مع الكود القديم (استخدام نفس الأسماء)
cryptomus_client = plisio_client  # ⭐ Alias للسهولة
CryptomusError = PlisioError  # ⭐ Alias للاستثناءات
```

### `services/pricing_service.py`

```python
"""
حساب سعر البيع النهائي = تكلفة المزود + نسبة/مبلغ ربح.
العملة: دولار أمريكي (USD) بالكامل.
منطق الأولوية عند البحث عن نسبة مخصصة:
(خدمة+دولة+مزود) > (خدمة+دولة) > (خدمة+مزود) > (خدمة فقط) > النسبة العامة.
"""
from decimal import Decimal, ROUND_UP

from sqlalchemy import select

from database.models import ServicePricing, ProviderName
from services.settings_service import SettingsService


class PricingService:

    @staticmethod
    async def get_margin(
        session,
        service: str,
        country_code: str,
        provider: ProviderName,
    ) -> tuple[str, Decimal]:
        """
        يجلب نسبة الربح المناسبة حسب الأولوية.
        يرجع (margin_type, margin_value).
        """
        result = await session.execute(
            select(ServicePricing).where(
                ServicePricing.service == service
            )
        )
        rows = result.scalars().all()

        best = None
        best_score = -1

        for row in rows:
            score = 0

            if row.country_code is not None:
                if row.country_code != country_code:
                    continue
                score += 2

            if row.provider is not None:
                if row.provider != provider:
                    continue
                score += 1

            if score > best_score:
                best_score = score
                best = row

        if best:
            return best.margin_type, best.margin_value

        default_margin = await SettingsService.get_decimal(
            "default_profit_margin_percent", Decimal("50")
        )
        return "percent", default_margin

    @staticmethod
    def apply_margin(
        cost_usd: Decimal,
        margin_type: str,
        margin_value: Decimal,
    ) -> Decimal:
        """
        يطبق نسبة الربح على سعر التكلفة بالدولار.
        margin_type: percent → نسبة مئوية
        margin_type: fixed   → مبلغ ثابت
        """
        if margin_type == "percent":
            sell = cost_usd * (
                Decimal("1") + margin_value / Decimal("100")
            )
        else:
            sell = cost_usd + margin_value

        return sell.quantize(Decimal("0.0001"), rounding=ROUND_UP)

    @staticmethod
    async def calculate_sell_price(
        session,
        service: str,
        country_code: str,
        provider: ProviderName,
        cost_usd: Decimal,
    ) -> Decimal:
        """
        دالة مساعدة تجمع get_margin و apply_margin في خطوة واحدة.
        """
        margin_type, margin_value = await PricingService.get_margin(
            session, service, country_code, provider
        )
        return PricingService.apply_margin(
            cost_usd, margin_type, margin_value
        )

    @staticmethod
    async def set_custom_margin(
        session,
        service: str,
        margin_type: str,
        margin_value: Decimal,
        country_code: str | None = None,
        provider: ProviderName | None = None,
    ) -> ServicePricing:
        """
        يضيف أو يعدل نسبة ربح مخصصة لخدمة/دولة/مزود معين.
        """
        result = await session.execute(
            select(ServicePricing).where(
                ServicePricing.service == service,
                ServicePricing.country_code == country_code,
                ServicePricing.provider == provider,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.margin_type = margin_type
            existing.margin_value = margin_value
            await session.commit()
            await session.refresh(existing)
            return existing

        pricing = ServicePricing(
            service=service,
            country_code=country_code,
            provider=provider,
            margin_type=margin_type,
            margin_value=margin_value,
        )
        session.add(pricing)
        await session.commit()
        await session.refresh(pricing)
        return pricing

    @staticmethod
    async def delete_custom_margin(
        session, pricing_id: int
    ) -> bool:
        pricing = await session.get(ServicePricing, pricing_id)
        if pricing is None:
            return False
        await session.delete(pricing)
        await session.commit()
        return True

    @staticmethod
    async def get_all_custom_margins(
        session,
    ) -> list[ServicePricing]:
        result = await session.execute(select(ServicePricing))
        return list(result.scalars().all())
```

### `services/product_service.py`

```python
"""
خدمة إدارة المنتجات.

المسؤوليات:
1) إنشاء منتج من خدمة مزود
2) حساب سعر البيع (ثابت / نسبة ربح)
3) عرض السعر للمستخدم بطرق مختلفة
4) تحديث المنتجات
5) إحصائيات المبيعات
"""
import logging
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload

from database.engine import async_session_maker
from database.models import (
    Product,
    ProductStatus,
    ProductPricingType,
    ProductDisplayType,
    ProviderService,
    ProviderServiceStatus,
    ApiProvider,
    SubCategory,
    Category,
    UnifiedOrder,
    UnifiedOrderStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class PriceCalculation:
    """نتيجة حساب السعر."""
    cost_price_usd: Decimal
    sell_price_usd: Decimal
    profit_usd: Decimal
    profit_percent: Decimal
    display_text: str


class ProductService:
    """خدمة إدارة المنتجات."""

    # ══════════════════════════════════════════
    # ══════════════ حساب الأسعار ══════════════
    # ══════════════════════════════════════════

    @staticmethod
    def calculate_sell_price(
        cost_price_usd: Decimal,
        pricing_type: ProductPricingType,
        fixed_price: Decimal | None = None,
        margin_percent: Decimal | None = None,
    ) -> Decimal:
        """
        يحسب سعر البيع النهائي.

        Args:
            cost_price_usd: سعر التكلفة من المزود
            pricing_type: نوع التسعير (ثابت / نسبة)
            fixed_price: السعر الثابت (إذا كان النوع FIXED)
            margin_percent: نسبة الربح (إذا كان النوع MARGIN_PERCENT)

        Returns:
            سعر البيع النهائي بالدولار
        """
        if pricing_type == ProductPricingType.FIXED:
            if fixed_price is None:
                raise ValueError(
                    "fixed_price مطلوب مع نوع FIXED"
                )
            return fixed_price.quantize(
                Decimal("0.0001"),
                rounding=ROUND_HALF_UP,
            )

        if pricing_type == ProductPricingType.MARGIN_PERCENT:
            if margin_percent is None:
                raise ValueError(
                    "margin_percent مطلوب مع نوع MARGIN_PERCENT"
                )
            multiplier = (
                Decimal("1") + margin_percent / Decimal("100")
            )
            sell = cost_price_usd * multiplier
            return sell.quantize(
                Decimal("0.0001"),
                rounding=ROUND_HALF_UP,
            )

        raise ValueError(f"نوع تسعير غير معروف: {pricing_type}")

    @staticmethod
    def calculate_profit(
        cost_price_usd: Decimal,
        sell_price_usd: Decimal,
    ) -> tuple[Decimal, Decimal]:
        """
        يحسب الربح والنسبة المئوية.

        Returns:
            (profit_usd, profit_percent)
        """
        profit = sell_price_usd - cost_price_usd
        percent = Decimal("0")

        if cost_price_usd > 0:
            percent = (
                profit / cost_price_usd * Decimal("100")
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

        return (
            profit.quantize(
                Decimal("0.0001"),
                rounding=ROUND_HALF_UP,
            ),
            percent,
        )

    # ══════════════════════════════════════════
    # ══════════════ عرض السعر للمستخدم ══════════════
    # ══════════════════════════════════════════

    @staticmethod
    def format_price_display(
        price_usd: Decimal,
        display_type: ProductDisplayType,
        min_quantity: int = 1,
    ) -> str:
        """
        يحول السعر لنص قابل للعرض للمستخدم.

        Args:
            price_usd: السعر بالدولار
            display_type: طريقة العرض
            min_quantity: الحد الأدنى (يُستخدم مع per_min_quantity)

        Returns:
            نص السعر للعرض
        """
        if display_type == ProductDisplayType.PER_1000:
            return f"{price_usd}$ / 1000"

        if display_type == ProductDisplayType.PER_MIN_QUANTITY:
            return f"{price_usd}$ / {min_quantity}"

        if display_type == ProductDisplayType.FIXED_TOTAL:
            return f"{price_usd}$ للطلب"

        return f"{price_usd}$"

    @staticmethod
    def calculate_order_total(
        product: Product,
        quantity: int,
    ) -> Decimal:
        """
        يحسب السعر الإجمالي للطلب بناءً على الكمية ونوع العرض.

        Args:
            product: المنتج
            quantity: الكمية المطلوبة

        Returns:
            السعر الإجمالي بالدولار
        """
        if (
            product.display_type
            == ProductDisplayType.PER_1000
        ):
            total = (
                product.price_usd
                * Decimal(str(quantity))
                / Decimal("1000")
            )

        elif (
            product.display_type
            == ProductDisplayType.PER_MIN_QUANTITY
        ):
            if product.min_quantity <= 0:
                return product.price_usd
            multiplier = (
                Decimal(str(quantity))
                / Decimal(str(product.min_quantity))
            )
            total = product.price_usd * multiplier

        else:
            total = product.price_usd

        return total.quantize(
            Decimal("0.0001"),
            rounding=ROUND_HALF_UP,
        )

    # ══════════════════════════════════════════
    # ══════════════ CRUD المنتجات ══════════════
    # ══════════════════════════════════════════

    @staticmethod
    async def create_from_provider_service(
        session,
        sub_category_id: int,
        provider_service_id: int,
        name_ar: str,
        pricing_type: ProductPricingType,
        fixed_price: Decimal | None = None,
        margin_percent: Decimal | None = None,
        display_type: ProductDisplayType = ProductDisplayType.PER_1000,
        description: str | None = None,
        image_file_id: str | None = None,
        image_url: str | None = None,
        min_quantity_override: int | None = None,
        max_quantity_override: int | None = None,
        sort_order: int = 0,
    ) -> Product:
        """
        ينشئ منتج جديد من خدمة مزود موجودة.

        هذه الدالة الرئيسية لـ Wizard إنشاء المنتج.
        """
        provider_service = await session.get(
            ProviderService, provider_service_id
        )
        if not provider_service:
            raise ValueError(
                f"خدمة المزود {provider_service_id} غير موجودة"
            )

        sub_category = await session.get(
            SubCategory, sub_category_id
        )
        if not sub_category:
            raise ValueError(
                f"القسم الفرعي {sub_category_id} غير موجود"
            )

        cost_price = provider_service.rate_usd

        sell_price = ProductService.calculate_sell_price(
            cost_price_usd=cost_price,
            pricing_type=pricing_type,
            fixed_price=fixed_price,
            margin_percent=margin_percent,
        )

        min_qty = (
            min_quantity_override
            if min_quantity_override is not None
            else provider_service.min_quantity
        )
        max_qty = (
            max_quantity_override
            if max_quantity_override is not None
            else provider_service.max_quantity
        )

        product = Product(
            sub_category_id=sub_category_id,
            api_provider_id=provider_service.api_provider_id,
            provider_service_ref_id=provider_service.id,
            provider_service_id=(
                provider_service.external_service_id
            ),
            name_ar=name_ar,
            description=description,
            image_url=image_url,
            image_file_id=image_file_id,
            price_usd=sell_price,
            cost_price_usd=cost_price,
            pricing_type=pricing_type,
            profit_margin_percent=margin_percent,
            display_type=display_type,
            min_quantity=min_qty,
            max_quantity=max_qty,
            requires_link=provider_service.requires_link,
            requires_quantity=(
                provider_service.requires_quantity
            ),
            requires_player_id=(
                provider_service.requires_player_id
            ),
            status=ProductStatus.ACTIVE,
            sort_order=sort_order,
        )

        session.add(product)
        await session.commit()
        await session.refresh(product)

        logger.info(
            f"تم إنشاء منتج جديد #{product.id}: "
            f"{product.name_ar} - {product.price_usd}$"
        )

        return product

    @staticmethod
    async def create_manual(
        session,
        sub_category_id: int,
        name_ar: str,
        price_usd: Decimal,
        description: str | None = None,
        image_file_id: str | None = None,
        image_url: str | None = None,
        min_quantity: int = 1,
        max_quantity: int = 1,
        requires_link: bool = False,
        requires_quantity: bool = False,
        requires_player_id: bool = False,
        display_type: ProductDisplayType = ProductDisplayType.FIXED_TOTAL,
        sort_order: int = 0,
    ) -> Product:
        """ينشئ منتج يدوي (بدون ربط بخدمة مزود)."""
        product = Product(
            sub_category_id=sub_category_id,
            name_ar=name_ar,
            description=description,
            image_url=image_url,
            image_file_id=image_file_id,
            price_usd=price_usd,
            cost_price_usd=Decimal("0"),
            pricing_type=ProductPricingType.FIXED,
            display_type=display_type,
            min_quantity=min_quantity,
            max_quantity=max_quantity,
            requires_link=requires_link,
            requires_quantity=requires_quantity,
            requires_player_id=requires_player_id,
            status=ProductStatus.ACTIVE,
            sort_order=sort_order,
        )

        session.add(product)
        await session.commit()
        await session.refresh(product)

        logger.info(
            f"تم إنشاء منتج يدوي #{product.id}: "
            f"{product.name_ar}"
        )
        return product

    @staticmethod
    async def get_product(
        session, product_id: int
    ) -> Product | None:
        """يجلب منتج مع كل علاقاته."""
        result = await session.execute(
            select(Product)
            .options(
                selectinload(Product.sub_category)
                .selectinload(SubCategory.category),
                selectinload(Product.api_provider),
                selectinload(Product.provider_service),
            )
            .where(Product.id == product_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_products_by_sub_category(
        session,
        sub_category_id: int,
        active_only: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Product]:
        """يجلب كل منتجات قسم فرعي."""
        query = (
            select(Product)
            .options(selectinload(Product.api_provider))
            .where(Product.sub_category_id == sub_category_id)
        )

        if active_only:
            query = query.where(
                Product.status == ProductStatus.ACTIVE
            )

        query = query.order_by(
            Product.sort_order, Product.id
        )

        if limit:
            query = query.limit(limit).offset(offset)

        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def count_products_by_sub_category(
        session,
        sub_category_id: int,
        active_only: bool = False,
    ) -> int:
        """يحصي عدد منتجات قسم فرعي."""
        query = select(
            func.count(Product.id)
        ).where(
            Product.sub_category_id == sub_category_id
        )

        if active_only:
            query = query.where(
                Product.status == ProductStatus.ACTIVE
            )

        result = await session.execute(query)
        return result.scalar_one()

    @staticmethod
    async def update_product(
        session,
        product_id: int,
        **fields: Any,
    ) -> Product | None:
        """
        يحدّث حقول منتج.

        الحقول المدعومة:
        - name_ar, description, image_file_id, image_url
        - price_usd, pricing_type, profit_margin_percent
        - display_type, min_quantity, max_quantity
        - sort_order, status, is_featured, is_bestseller
        - requires_link, requires_quantity, requires_player_id
        """
        product = await session.get(Product, product_id)
        if not product:
            return None

        allowed_fields = {
            "name_ar", "description",
            "image_file_id", "image_url",
            "price_usd", "cost_price_usd",
            "pricing_type", "profit_margin_percent",
            "display_type",
            "min_quantity", "max_quantity",
            "sort_order", "status",
            "is_featured", "is_bestseller",
            "requires_link", "requires_quantity",
            "requires_player_id",
        }

        for key, value in fields.items():
            if key in allowed_fields:
                setattr(product, key, value)

        await session.commit()
        await session.refresh(product)
        return product

    @staticmethod
    async def toggle_status(
        session, product_id: int
    ) -> Product | None:
        """يبدل حالة منتج (نشط/معطّل)."""
        product = await session.get(Product, product_id)
        if not product:
            return None

        product.status = (
            ProductStatus.INACTIVE
            if product.status == ProductStatus.ACTIVE
            else ProductStatus.ACTIVE
        )

        await session.commit()
        await session.refresh(product)
        return product

    @staticmethod
    async def toggle_featured(
        session, product_id: int
    ) -> Product | None:
        """يبدل حالة "مميز" لمنتج."""
        product = await session.get(Product, product_id)
        if not product:
            return None

        product.is_featured = not product.is_featured
        await session.commit()
        await session.refresh(product)
        return product

    @staticmethod
    async def toggle_bestseller(
        session, product_id: int
    ) -> Product | None:
        """يبدل حالة "الأكثر مبيعاً" لمنتج."""
        product = await session.get(Product, product_id)
        if not product:
            return None

        product.is_bestseller = not product.is_bestseller
        await session.commit()
        await session.refresh(product)
        return product

    @staticmethod
    async def delete_product(
        session, product_id: int
    ) -> bool:
        """يحذف منتج."""
        product = await session.get(Product, product_id)
        if not product:
            return False

        await session.delete(product)
        await session.commit()
        return True

    # ══════════════════════════════════════════
    # ══════════════ إحصائيات ══════════════
    # ══════════════════════════════════════════

    @staticmethod
    async def get_product_stats(
        session, product_id: int
    ) -> dict:
        """يجلب إحصائيات منتج."""
        product = await session.get(Product, product_id)
        if not product:
            return {}

        total_orders = await session.execute(
            select(func.count(UnifiedOrder.id))
            .where(UnifiedOrder.product_id == product_id)
        )
        total_orders_count = total_orders.scalar_one()

        completed = await session.execute(
            select(func.count(UnifiedOrder.id))
            .where(
                and_(
                    UnifiedOrder.product_id == product_id,
                    UnifiedOrder.status
                    == UnifiedOrderStatus.COMPLETED,
                )
            )
        )
        completed_count = completed.scalar_one()

        total_revenue = await session.execute(
            select(
                func.coalesce(
                    func.sum(UnifiedOrder.price_usd),
                    Decimal("0"),
                )
            )
            .where(
                and_(
                    UnifiedOrder.product_id == product_id,
                    UnifiedOrder.status
                    == UnifiedOrderStatus.COMPLETED,
                )
            )
        )
        revenue = total_revenue.scalar_one()

        total_cost = await session.execute(
            select(
                func.coalesce(
                    func.sum(UnifiedOrder.cost_price_usd),
                    Decimal("0"),
                )
            )
            .where(
                and_(
                    UnifiedOrder.product_id == product_id,
                    UnifiedOrder.status
                    == UnifiedOrderStatus.COMPLETED,
                )
            )
        )
        cost = total_cost.scalar_one()

        return {
            "total_orders": total_orders_count,
            "completed_orders": completed_count,
            "total_revenue_usd": revenue,
            "total_cost_usd": cost,
            "total_profit_usd": revenue - cost,
            "views": product.view_count,
            "sold": product.total_sold,
        }

    @staticmethod
    async def get_bestsellers(
        session,
        limit: int = 10,
        active_only: bool = True,
    ) -> list[Product]:
        """يجلب أكثر المنتجات مبيعاً."""
        query = (
            select(Product)
            .options(selectinload(Product.sub_category))
        )

        if active_only:
            query = query.where(
                Product.status == ProductStatus.ACTIVE
            )

        query = query.order_by(
            desc(Product.total_sold)
        ).limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_featured(
        session,
        limit: int = 10,
        active_only: bool = True,
    ) -> list[Product]:
        """يجلب المنتجات المميزة."""
        query = (
            select(Product)
            .options(selectinload(Product.sub_category))
            .where(Product.is_featured == True)
        )

        if active_only:
            query = query.where(
                Product.status == ProductStatus.ACTIVE
            )

        query = query.order_by(
            Product.sort_order, Product.id
        ).limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def increment_views(
        session, product_id: int
    ) -> None:
        """يزيد عداد مشاهدات المنتج."""
        product = await session.get(Product, product_id)
        if product:
            product.view_count = (product.view_count or 0) + 1
            await session.commit()

    @staticmethod
    async def increment_sold(
        session, product_id: int, quantity: int = 1
    ) -> None:
        """يزيد عداد مبيعات المنتج."""
        product = await session.get(Product, product_id)
        if product:
            product.total_sold = (
                (product.total_sold or 0) + quantity
            )
            await session.commit()

    @staticmethod
    async def search_products(
        session,
        query_text: str,
        limit: int = 20,
        active_only: bool = True,
    ) -> list[Product]:
        """يبحث في المنتجات بالاسم أو الوصف."""
        if not query_text or not query_text.strip():
            return []

        search_pattern = f"%{query_text.strip()}%"

        query = (
            select(Product)
            .options(selectinload(Product.sub_category))
            .where(
                or_(
                    Product.name_ar.ilike(search_pattern),
                    Product.description.ilike(search_pattern),
                )
            )
        )

        if active_only:
            query = query.where(
                Product.status == ProductStatus.ACTIVE
            )

        query = query.limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())
```

### `services/provider_sync_service.py`

```python
"""
خدمة تزامن ومزامنة الخدمات من المزودين.

المهام الرئيسية:
1) سحب كل خدمات المزود وحفظها في قاعدة البيانات
2) تحديث الخدمات الموجودة إذا تغيرت
3) تعطيل الخدمات المحذوفة من المزود
4) تحويل الأسعار من عملة المزود إلى دولار
5) فحص رصيد المزود
6) البحث في خدمات مزود معين
"""
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, and_, or_, func
from sqlalchemy.exc import IntegrityError

from database.engine import async_session_maker
from database.models import (
    ApiProvider,
    ProviderService,
    ProviderServiceStatus,
    ProviderPriceType,
    Product,
    ProductStatus,
)
from protocols.base import ProtocolError
from protocols.factory import ProtocolFactory
from services.currency_service import CurrencyService

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """نتيجة عملية التزامن."""
    provider_id: int
    provider_name: str
    total_fetched: int = 0
    new_services: int = 0
    updated_services: int = 0
    deactivated_services: int = 0
    reactivated_services: int = 0
    failed_services: int = 0
    products_affected: int = 0
    success: bool = True
    error_message: str | None = None
    duration_seconds: float = 0

    def summary(self) -> str:
        """ملخص نصي للنتيجة."""
        if not self.success:
            return (
                f"❌ فشل تزامن {self.provider_name}\n"
                f"السبب: {self.error_message}"
            )

        return (
            f"✅ اكتمل تزامن {self.provider_name}\n\n"
            f"📊 <b>النتائج:</b>\n"
            f"• تم سحب: {self.total_fetched} خدمة\n"
            f"• جديدة: {self.new_services}\n"
            f"• محدّثة: {self.updated_services}\n"
            f"• معطّلة (محذوفة من المزود): "
            f"{self.deactivated_services}\n"
            f"• أعيد تفعيلها: {self.reactivated_services}\n"
            f"• فشلت: {self.failed_services}\n"
            f"• منتجات متأثرة: {self.products_affected}\n"
            f"⏱ الوقت: {self.duration_seconds:.1f} ثانية"
        )


class ProviderSyncService:
    """خدمة تزامن الخدمات من المزودين."""

    @staticmethod
    async def test_provider_connection(
        provider: ApiProvider,
    ) -> tuple[bool, str, Decimal | None, str | None]:
        """
        يختبر الاتصال بمزود ويجلب رصيده.

        Returns:
            (success, message, balance, currency)
        """
        try:
            protocol = ProtocolFactory.create_from_provider(
                provider
            )
        except ProtocolError as e:
            return False, f"خطأ في البروتوكول: {e}", None, None

        try:
            balance_obj = await protocol.get_balance()
            return (
                True,
                "اتصال ناجح",
                balance_obj.amount,
                balance_obj.currency,
            )
        except ProtocolError as e:
            return False, str(e), None, None
        except Exception as e:
            logger.error(
                f"خطأ غير متوقع اختبار مزود "
                f"{provider.id}: {e}"
            )
            return False, f"خطأ غير متوقع: {e}", None, None

    @staticmethod
    async def update_provider_balance(
        provider_id: int,
    ) -> tuple[bool, str]:
        """يحدّث رصيد المزود في قاعدة البيانات."""
        async with async_session_maker() as session:
            provider = await session.get(
                ApiProvider, provider_id
            )
            if not provider:
                return False, "المزود غير موجود"

            success, message, balance, currency = (
                await ProviderSyncService.test_provider_connection(
                    provider
                )
            )

            provider.last_checked_at = datetime.utcnow()

            if not success:
                provider.last_error = message[:500]
                await session.commit()
                return False, message

            provider.balance = balance
            if currency:
                provider.currency = currency
            provider.last_error = None
            await session.commit()

            return True, (
                f"الرصيد الحالي: {balance} {currency}"
            )

    @staticmethod
    async def sync_provider_services(
        provider_id: int,
    ) -> SyncResult:
        """
        يسحب كل خدمات المزود ويحفظها/يحدّثها.

        هذه الدالة الرئيسية للتزامن.
        """
        start_time = datetime.utcnow()

        async with async_session_maker() as session:
            provider = await session.get(
                ApiProvider, provider_id
            )
            if not provider:
                return SyncResult(
                    provider_id=provider_id,
                    provider_name="Unknown",
                    success=False,
                    error_message="المزود غير موجود",
                )

            result = SyncResult(
                provider_id=provider_id,
                provider_name=provider.name,
            )

            try:
                protocol = ProtocolFactory.create_from_provider(
                    provider
                )
            except ProtocolError as e:
                result.success = False
                result.error_message = (
                    f"خطأ في البروتوكول: {e}"
                )
                return result

            try:
                services = await protocol.get_services()
                result.total_fetched = len(services)
            except ProtocolError as e:
                result.success = False
                result.error_message = str(e)
                provider.last_error = str(e)[:500]
                await session.commit()
                return result
            except Exception as e:
                logger.error(
                    f"خطأ غير متوقع سحب خدمات "
                    f"{provider.id}: {e}"
                )
                result.success = False
                result.error_message = f"خطأ غير متوقع: {e}"
                return result

            existing_result = await session.execute(
                select(ProviderService).where(
                    ProviderService.api_provider_id == provider_id
                )
            )
            existing_services = {
                s.external_service_id: s
                for s in existing_result.scalars().all()
            }

            rate_to_usd = provider.rate_to_usd or Decimal("1")
            if provider.currency and provider.currency != "USD":
                if rate_to_usd == Decimal("1"):
                    rate_to_usd = (
                        await CurrencyService.get_rate_to_usd(
                            provider.currency
                        )
                    )
                    provider.rate_to_usd = rate_to_usd

            fetched_ids = set()

            for service in services:
                try:
                    fetched_ids.add(service.external_id)

                    rate_usd = (
                        service.rate * rate_to_usd
                    ).quantize(Decimal("0.0001"))

                    raw_json = json.dumps(
                        service.raw,
                        ensure_ascii=False,
                    )[:5000]

                    existing = existing_services.get(
                        service.external_id
                    )

                    if existing:
                        was_deleted = (
                            existing.status
                            == ProviderServiceStatus.DELETED_FROM_PROVIDER
                        )

                        existing.name = service.name
                        existing.category = service.category
                        existing.service_type = (
                            service.service_type
                        )
                        existing.rate = service.rate
                        existing.rate_usd = rate_usd
                        existing.min_quantity = (
                            service.min_quantity
                        )
                        existing.max_quantity = (
                            service.max_quantity
                        )
                        existing.description = (
                            service.description
                        )
                        existing.requires_link = (
                            service.requires_link
                        )
                        existing.requires_quantity = (
                            service.requires_quantity
                        )
                        existing.requires_player_id = (
                            service.requires_player_id
                        )
                        existing.supports_refill = (
                            service.supports_refill
                        )
                        existing.supports_cancel = (
                            service.supports_cancel
                        )
                        existing.raw_data = raw_json
                        existing.last_updated = (
                            datetime.utcnow()
                        )

                        if was_deleted:
                            existing.status = (
                                ProviderServiceStatus.ACTIVE
                            )
                            result.reactivated_services += 1
                        else:
                            result.updated_services += 1
                    else:
                        new_service = ProviderService(
                            api_provider_id=provider_id,
                            external_service_id=(
                                service.external_id
                            ),
                            name=service.name,
                            category=service.category,
                            service_type=service.service_type,
                            rate=service.rate,
                            rate_usd=rate_usd,
                            price_type=(
                                ProviderPriceType.PER_1000
                            ),
                            min_quantity=service.min_quantity,
                            max_quantity=service.max_quantity,
                            description=service.description,
                            requires_link=service.requires_link,
                            requires_quantity=(
                                service.requires_quantity
                            ),
                            requires_player_id=(
                                service.requires_player_id
                            ),
                            supports_refill=(
                                service.supports_refill
                            ),
                            supports_cancel=(
                                service.supports_cancel
                            ),
                            status=(
                                ProviderServiceStatus.ACTIVE
                            ),
                            raw_data=raw_json,
                        )
                        session.add(new_service)
                        result.new_services += 1

                except Exception as e:
                    logger.warning(
                        f"فشل حفظ خدمة "
                        f"{service.external_id}: {e}"
                    )
                    result.failed_services += 1
                    continue

            deleted_ids = (
                set(existing_services.keys()) - fetched_ids
            )
            for deleted_id in deleted_ids:
                existing = existing_services[deleted_id]
                if (
                    existing.status
                    != ProviderServiceStatus.DELETED_FROM_PROVIDER
                ):
                    existing.status = (
                        ProviderServiceStatus.DELETED_FROM_PROVIDER
                    )
                    result.deactivated_services += 1

                    products_result = await session.execute(
                        select(Product).where(
                            Product.provider_service_ref_id
                            == existing.id
                        )
                    )
                    affected_products = (
                        products_result.scalars().all()
                    )
                    for product in affected_products:
                        product.status = (
                            ProductStatus.INACTIVE
                        )
                        result.products_affected += 1

            provider.last_sync_at = datetime.utcnow()
            provider.total_services = (
                result.total_fetched
                - result.deactivated_services
                + result.new_services
            )
            provider.last_error = None

            try:
                await session.commit()
            except IntegrityError as e:
                await session.rollback()
                logger.error(
                    f"خطأ integrity في تزامن "
                    f"{provider.id}: {e}"
                )
                result.success = False
                result.error_message = str(e)[:200]
                return result

            duration = (
                datetime.utcnow() - start_time
            ).total_seconds()
            result.duration_seconds = duration

            logger.info(
                f"تزامن {provider.name} انتهى: "
                f"{result.new_services} جديدة, "
                f"{result.updated_services} محدّثة, "
                f"{result.deactivated_services} معطّلة "
                f"في {duration:.1f}s"
            )

            return result

    @staticmethod
    async def get_provider_services_count(
        provider_id: int,
        active_only: bool = True,
    ) -> int:
        """يجلب عدد خدمات مزود معين."""
        async with async_session_maker() as session:
            query = select(
                func.count(ProviderService.id)
            ).where(
                ProviderService.api_provider_id == provider_id
            )

            if active_only:
                query = query.where(
                    ProviderService.status
                    == ProviderServiceStatus.ACTIVE
                )

            result = await session.execute(query)
            return result.scalar_one()

    @staticmethod
    async def get_provider_services(
        provider_id: int,
        limit: int = 20,
        offset: int = 0,
        active_only: bool = True,
        search: str | None = None,
        category: str | None = None,
    ) -> list[ProviderService]:
        """
        يجلب خدمات مزود مع دعم البحث والـ Pagination.
        """
        async with async_session_maker() as session:
            query = select(ProviderService).where(
                ProviderService.api_provider_id == provider_id
            )

            if active_only:
                query = query.where(
                    ProviderService.status
                    == ProviderServiceStatus.ACTIVE
                )

            if search:
                search_lower = f"%{search.lower()}%"
                query = query.where(
                    or_(
                        func.lower(
                            ProviderService.name
                        ).like(search_lower),
                        func.lower(
                            ProviderService.category
                        ).like(search_lower),
                        ProviderService.external_service_id
                        == search,
                    )
                )

            if category:
                query = query.where(
                    ProviderService.category == category
                )

            query = query.order_by(
                ProviderService.category,
                ProviderService.name,
            )
            query = query.limit(limit).offset(offset)

            result = await session.execute(query)
            return list(result.scalars().all())

    @staticmethod
    async def get_provider_categories(
        provider_id: int,
    ) -> list[tuple[str, int]]:
        """
        يجلب كل التصنيفات لدى مزود معين مع عدد الخدمات في كل واحد.
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(
                    ProviderService.category,
                    func.count(ProviderService.id).label(
                        "count"
                    ),
                )
                .where(
                    and_(
                        ProviderService.api_provider_id
                        == provider_id,
                        ProviderService.status
                        == ProviderServiceStatus.ACTIVE,
                        ProviderService.category.isnot(
                            None
                        ),
                    )
                )
                .group_by(ProviderService.category)
                .order_by(ProviderService.category)
            )

            return [
                (row.category, row.count)
                for row in result.all()
            ]

    @staticmethod
    async def get_service_by_id(
        service_id: int,
    ) -> ProviderService | None:
        """يجلب خدمة مزود بواسطة الـ ID الداخلي."""
        async with async_session_maker() as session:
            return await session.get(
                ProviderService, service_id
            )
```

### `services/sam_api_service.py`

```python
"""
خدمة Sam API لدفع شام كاش التلقائي.
https://www.sam-api.pro/api

الخصائص:
1) إنشاء فاتورة صالحة لـ 15 دقيقة.
2) التحقق من الدفع عبر رقم العملية (بدون webhook).
3) جلب حالة الفاتورة.
4) جلب رصيد المحفظة.
"""
import logging
from decimal import Decimal

import aiohttp

from config import settings

logger = logging.getLogger(__name__)


class SamApiError(Exception):
    pass


class SamApiExpiredError(SamApiError):
    pass


class SamApiClient:
    """
    عميل Sam API.
    يستخدم API Key من config.SAM_API_KEY.
    """

    def __init__(self):
        self.api_key = settings.SAM_API_KEY
        self.base_url = settings.SAM_API_URL.rstrip("/")
        self.wallet_address = settings.SAM_API_WALLET_ADDRESS

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict | None = None,
        use_auth: bool = True,
    ) -> dict:
        url = self.base_url + path
        headers = self._get_headers() if use_auth else {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            async with aiohttp.ClientSession(
                headers=headers
            ) as session:
                async with session.request(
                    method,
                    url,
                    json=json_data,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    text = await resp.text()

                    if resp.status == 410:
                        raise SamApiExpiredError(
                            "انتهت صلاحية الفاتورة"
                        )

                    if resp.status not in (200, 201):
                        try:
                            error_data = await resp.json(
                                content_type=None
                            )
                            error_msg = error_data.get(
                                "message",
                                error_data.get(
                                    "error",
                                    text[:200],
                                ),
                            )
                        except Exception:
                            error_msg = text[:200]
                        raise SamApiError(
                            f"Sam API خطأ {resp.status}: "
                            f"{error_msg}"
                        )

                    try:
                        return await resp.json(
                            content_type=None
                        )
                    except Exception:
                        raise SamApiError(
                            f"استجابة غير صالحة: {text[:200]}"
                        )
        except aiohttp.ClientError as e:
            raise SamApiError(
                f"خطأ اتصال مع Sam API: {e}"
            )

    async def get_wallets(self) -> list[dict]:
        """يجلب كل المحافظ المربوطة بالحساب."""
        return await self._request("GET", "/v1/wallets")

    async def get_wallet_balance(
        self, wallet_address: str | None = None
    ) -> list[dict]:
        """
        يجلب رصيد المحفظة.
        يعيد قائمة بالعملات المختلفة.
        """
        address = wallet_address or self.wallet_address
        if not address:
            raise SamApiError(
                "لم يتم تحديد عنوان المحفظة"
            )
        return await self._request(
            "GET",
            f"/v1/wallets/shamcash/{address}/balance",
        )

    async def get_wallet_transactions(
        self,
        wallet_address: str | None = None,
        direction: str = "all",
    ) -> list[dict]:
        """
        يجلب معاملات المحفظة.
        direction: in | out | all
        """
        address = wallet_address or self.wallet_address
        if not address:
            raise SamApiError(
                "لم يتم تحديد عنوان المحفظة"
            )
        return await self._request(
            "GET",
            f"/v1/wallets/shamcash/{address}"
            f"/transactions?direction={direction}",
        )

    async def create_invoice(
        self,
        amount: Decimal,
        currency: str,
        webhook_url: str = "https://example.com/no-webhook",
    ) -> dict:
        """
        ينشئ فاتورة دفع جديدة.

        amount: المبلغ (Decimal)
        currency: USD أو SYP أو EUR
        webhook_url: رابط webhook (مطلوب في API لكن يمكن أن يكون وهمياً
                     لأننا نستخدم verify يدوياً)

        يرجع dict يحتوي:
        - invoiceId
        - paymentUrl
        - expiresAt
        """
        if not self.wallet_address:
            raise SamApiError(
                "لم يتم تحديد عنوان محفظة الاستلام في .env"
            )

        currency_upper = currency.upper()
        if currency_upper not in ("USD", "SYP", "EUR"):
            raise SamApiError(
                f"عملة غير مدعومة: {currency}"
            )

        return await self._request(
            "POST",
            "/v1/invoices",
            json_data={
                "method": "shamcash",
                "identifier": self.wallet_address,
                "amount": str(amount),
                "currency": currency_upper,
                "webhookUrl": webhook_url,
            },
        )

    async def get_invoice_status(
        self, invoice_id: str
    ) -> dict:
        """
        يجلب بيانات الفاتورة الكاملة.

        يرجع dict يحتوي:
        - id
        - method
        - identifier
        - amount
        - currency
        - status (pending / paid / expired)
        - expiresAt
        - createdAt
        - paidAt
        """
        return await self._request(
            "GET",
            f"/pay/{invoice_id}",
            use_auth=False,
        )

    async def verify_invoice(
        self,
        invoice_id: str,
        transaction_ref: str,
    ) -> dict:
        """
        يتحقق من الدفع عبر رقم العملية.

        يرجع dict يحتوي:
        - verified: True/False
        - message: رسالة توضيحية

        قد يرمي:
        - SamApiExpiredError: إذا انتهت الفاتورة
        - SamApiError: للأخطاء الأخرى
        """
        return await self._request(
            "POST",
            f"/pay/{invoice_id}/verify",
            json_data={
                "transactionRef": transaction_ref.strip(),
            },
            use_auth=False,
        )


sam_api_client = SamApiClient()
```

### `services/settings_service.py`

```python
"""
إدارة الإعدادات (key-value) مع كاش بالذاكرة لتقليل الاستعلامات.
كل تعديل عبر set() يحدّث الكاش فوراً حتى تنعكس التغييرات بدون إعادة تشغيل البوت.
"""
from decimal import Decimal

from sqlalchemy import select

from database.models import Setting
from database.engine import async_session_maker


class SettingsService:
    _cache: dict[str, str] = {}
    _loaded: bool = False

    @classmethod
    async def _ensure_loaded(cls) -> None:
        if not cls._loaded:
            await cls.reload()

    @classmethod
    async def reload(cls) -> None:
        async with async_session_maker() as session:
            result = await session.execute(select(Setting))
            rows = result.scalars().all()
            cls._cache = {r.key: r.value for r in rows}
            cls._loaded = True

    @classmethod
    async def get(cls, key: str, default: str | None = None) -> str | None:
        await cls._ensure_loaded()
        return cls._cache.get(key, default)

    @classmethod
    async def get_decimal(
        cls, key: str, default: Decimal = Decimal("0")
    ) -> Decimal:
        val = await cls.get(key)
        try:
            return Decimal(val) if val is not None else default
        except Exception:
            return default

    @classmethod
    async def get_bool(cls, key: str, default: bool = False) -> bool:
        val = await cls.get(key)
        if val is None:
            return default
        return val.lower() in ("true", "1", "yes")

    @classmethod
    async def get_int(cls, key: str, default: int = 0) -> int:
        val = await cls.get(key)
        try:
            return int(val) if val is not None else default
        except (ValueError, TypeError):
            return default

    @classmethod
    async def get_all(cls) -> dict[str, str]:
        await cls._ensure_loaded()
        return dict(cls._cache)

    @classmethod
    async def set(cls, session, key: str, value: str) -> None:
        setting = await session.get(Setting, key)
        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value)
            session.add(setting)
        await session.commit()
        cls._cache[key] = value

    @classmethod
    async def delete(cls, session, key: str) -> None:
        setting = await session.get(Setting, key)
        if setting:
            await session.delete(setting)
            await session.commit()
        cls._cache.pop(key, None)
```

### `services/stars_service.py`

```python
"""
خدمة نجوم تليجرام.
تنشئ فواتير الدفع بالنجوم وتعالج الدفع الناجح.
"""
import logging
from decimal import Decimal

from aiogram import Bot
from aiogram.types import LabeledPrice, Message, PreCheckoutQuery

from database.models import TransactionType
from services.balance_service import BalanceService
from services.dynamic_service import DynamicService
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class StarsService:

    @staticmethod
    async def send_stars_invoice(
        bot: Bot,
        chat_id: int,
        package_id: int,
        session,
    ) -> bool:
        """
        يرسل فاتورة دفع بالنجوم للمستخدم.
        يرجع True إذا نجح، False إذا فشل.
        """
        package = await DynamicService.get_stars_package(
            session, package_id
        )
        if package is None or not package.is_active:
            return False

        try:
            await bot.send_invoice(
                chat_id=chat_id,
                title=package.label,
                description=(
                    f"شحن رصيد بقيمة {package.usd_amount}$ "
                    f"مقابل {package.stars_amount} نجمة"
                ),
                payload=f"stars_pkg:{package.id}",
                currency="XTR",
                prices=[
                    LabeledPrice(
                        label=package.label,
                        amount=package.stars_amount,
                    )
                ],
            )
            return True
        except Exception as e:
            logger.error(f"فشل إرسال فاتورة النجوم: {e}")
            return False

    @staticmethod
    async def handle_pre_checkout(
        pre_checkout_query: PreCheckoutQuery,
    ) -> None:
        """
        يوافق على الدفع قبل اكتماله.
        يجب الرد خلال 10 ثوانٍ.
        """
        await pre_checkout_query.answer(ok=True)

    @staticmethod
    async def handle_successful_payment(
        message: Message,
        session,
        db_user,
        bot: Bot,
    ) -> Decimal:
        """
        يعالج الدفع الناجح بالنجوم.
        يضيف الرصيد للمستخدم ويرسل إشعارات.
        يرجع المبلغ المضاف بالدولار.
        """
        payment = message.successful_payment
        payload = payment.invoice_payload

        if not payload.startswith("stars_pkg:"):
            logger.error(f"payload غير معروف: {payload}")
            return Decimal("0")

        try:
            package_id = int(payload.split(":")[1])
        except (ValueError, IndexError):
            logger.error(f"payload غير صالح: {payload}")
            return Decimal("0")

        package = await DynamicService.get_stars_package(
            session, package_id
        )
        if package is None:
            logger.error(
                f"باقة النجوم {package_id} غير موجودة"
            )
            return Decimal("0")

        amount_usd = package.usd_amount

        await BalanceService.add_balance(
            session=session,
            user_id=db_user.id,
            amount=amount_usd,
            tx_type=TransactionType.STARS_DEPOSIT,
            description=(
                f"شحن بنجوم تليجرام - "
                f"{payment.total_amount} نجمة"
            ),
            related_table="stars_packages",
            related_id=package.id,
        )

        notifier = NotificationService(bot)

        await notifier.notify_user(
            telegram_id=db_user.telegram_id,
            text=(
                "✅ <b>تم شحن رصيدك بنجاح!</b>\n\n"
                f"⭐ النجوم المدفوعة: "
                f"{payment.total_amount}\n"
                f"💰 الرصيد المضاف: "
                f"<b>{amount_usd}$</b>\n\n"
                "يمكنك الآن استخدام رصيدك."
            ),
        )

        await notifier.notify_admin(
            text=(
                "⭐ <b>شحن بنجوم تليجرام</b>\n\n"
                f"👤 المستخدم: {db_user.telegram_id} "
                f"(@{db_user.username or '-'})\n"
                f"⭐ النجوم: {payment.total_amount}\n"
                f"💰 المبلغ: {amount_usd}$"
            ),
        )

        logger.info(
            f"دفع نجوم ناجح: المستخدم {db_user.telegram_id}, "
            f"{payment.total_amount} نجمة, {amount_usd}$"
        )

        return amount_usd
```

### `services/subscription_service.py`

```python
from sqlalchemy import select

from database.models import MandatoryChannel


class SubscriptionService:
    @staticmethod
    async def get_active_channels(session):
        result = await session.execute(select(MandatoryChannel).where(MandatoryChannel.is_active == True))
        return result.scalars().all()

    @staticmethod
    async def is_user_subscribed_all(bot, session, user_telegram_id: int) -> tuple[bool, list]:
        channels = await SubscriptionService.get_active_channels(session)
        not_subscribed = []
        for ch in channels:
            try:
                member = await bot.get_chat_member(ch.chat_id, user_telegram_id)
                if member.status in ("left", "kicked"):
                    not_subscribed.append(ch)
            except Exception:
                not_subscribed.append(ch)
        return len(not_subscribed) == 0, not_subscribed
```

### `states/__init__.py`

```python

```

### `states/states.py`

```python
"""
كل حالات FSM الخاصة بالبوت.
"""
from aiogram.fsm.state import State, StatesGroup


# ══════════════ المستخدم ══════════════

class DepositStates(StatesGroup):
    waiting_amount = State()
    waiting_proof_photo = State()
    waiting_tx_number = State()


# ══════════════ الشحن اليدوي - شام كاش ══════════════

class ShamCashManualStates(StatesGroup):
    waiting_amount = State()
    waiting_proof_photo = State()
    waiting_tx_number = State()


# ══════════════ الشحن اليدوي - USDT ══════════════

class UsdtManualStates(StatesGroup):
    waiting_network = State()
    waiting_amount = State()
    waiting_proof_photo = State()
    waiting_tx_hash = State()


# ══════════════ الشحن التلقائي - شام كاش ══════════════

class ShamCashAutoStates(StatesGroup):
    waiting_currency = State()
    waiting_amount = State()
    waiting_transaction_ref = State()


# ══════════════ الشحن التلقائي - USDT ══════════════

class UsdtAutoStates(StatesGroup):
    waiting_amount = State()


# ══════════════ التحويل بين المستخدمين ══════════════

class TransferStates(StatesGroup):
    waiting_recipient_id = State()
    waiting_amount = State()


class SMMOrderStates(StatesGroup):
    waiting_link = State()
    waiting_quantity = State()
    waiting_coupon = State()


class GamesOrderStates(StatesGroup):
    waiting_player_id = State()
    waiting_coupon = State()


class AppsOrderStates(StatesGroup):
    waiting_player_id = State()
    waiting_coupon = State()


# ══════════════ الأدمن - عام ══════════════

class AdminBroadcastStates(StatesGroup):
    waiting_content = State()


class AdminChannelStates(StatesGroup):
    waiting_channel_id = State()


class AdminUserSearchStates(StatesGroup):
    waiting_user_id = State()
    waiting_balance_amount = State()


class AdminPricingStates(StatesGroup):
    waiting_exchange_rate = State()
    waiting_margin_value = State()


class AdminSupportStates(StatesGroup):
    waiting_support_username = State()


class AdminPaymentStates(StatesGroup):
    waiting_payment_text = State()


class AdminLargeTxStates(StatesGroup):
    waiting_threshold = State()


class AdminOrderTimeoutStates(StatesGroup):
    waiting_minutes = State()


class AdminCountryStates(StatesGroup):
    waiting_code = State()
    waiting_name_ar = State()
    waiting_flag = State()
    waiting_fivesim_code = State()
    waiting_herosms_code = State()
    waiting_sms_activate_code = State()
    waiting_smshub_code = State()


# ══════════════ الأدمن - الأقسام الرئيسية ══════════════

class AdminCategoryStates(StatesGroup):
    waiting_name = State()
    waiting_emoji = State()
    waiting_type = State()
    waiting_sort_order = State()
    waiting_edit_field = State()
    waiting_edit_value = State()


# ══════════════ الأدمن - الأقسام الفرعية ══════════════

class AdminSubCategoryStates(StatesGroup):
    waiting_name = State()
    waiting_emoji = State()
    waiting_description = State()
    waiting_image = State()
    waiting_sort_order = State()
    waiting_edit_field = State()
    waiting_edit_value = State()


# ══════════════ الأدمن - المنتجات (Wizard) ══════════════

class AdminProductWizardStates(StatesGroup):
    """states للمعالج التفاعلي لإنشاء منتج جديد."""
    selecting_creation_mode = State()
    selecting_provider = State()
    selecting_category = State()
    browsing_services = State()
    searching_services = State()
    waiting_search_query = State()
    viewing_service = State()
    confirming_service = State()
    waiting_name = State()
    waiting_description = State()
    waiting_image_choice = State()
    waiting_image = State()
    selecting_pricing_type = State()
    waiting_fixed_price = State()
    waiting_margin_percent = State()
    selecting_display_type = State()
    waiting_min_quantity = State()
    waiting_max_quantity = State()
    confirming_creation = State()


# ══════════════ الأدمن - المنتجات (تعديل) ══════════════

class AdminProductStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    waiting_image = State()
    waiting_price = State()
    waiting_cost_price = State()
    waiting_provider_service_id = State()
    waiting_min_quantity = State()
    waiting_max_quantity = State()
    waiting_sort_order = State()
    waiting_pricing_type = State()
    waiting_profit_margin = State()
    waiting_search_query = State()
    waiting_edit_field = State()
    waiting_edit_value = State()
    confirming_price_change = State()
    confirming_delete = State()


# ══════════════ الأدمن - المزودين ══════════════

class AdminApiProviderStates(StatesGroup):
    waiting_protocol_type = State()
    waiting_name = State()
    waiting_type = State()
    waiting_api_url = State()
    waiting_api_key = State()
    waiting_currency = State()
    waiting_rate_to_usd = State()
    waiting_priority = State()
    waiting_low_balance_threshold = State()
    waiting_custom_config = State()
    waiting_edit_field = State()
    waiting_edit_value = State()
    confirming_sync = State()


class AdminProviderServicesStates(StatesGroup):
    """states للتعامل مع خدمات مزود محدد."""
    browsing_services = State()
    searching_services = State()
    waiting_search_query = State()
    viewing_service = State()
    selecting_for_product = State()


class AdminCouponStates(StatesGroup):
    waiting_code = State()
    waiting_discount_type = State()
    waiting_discount_value = State()
    waiting_max_uses = State()
    waiting_min_order = State()
    waiting_expires_days = State()


class AdminStarsStates(StatesGroup):
    waiting_stars_amount = State()
    waiting_usd_amount = State()
    waiting_label = State()
    waiting_edit_field = State()
    waiting_edit_value = State()


class AdminNumberServiceStates(StatesGroup):
    waiting_code = State()
    waiting_name = State()
    waiting_emoji = State()
    waiting_fivesim_code = State()
    waiting_herosms_code = State()
    waiting_sms_activate_code = State()
    waiting_smshub_code = State()
    waiting_edit_field = State()
    waiting_edit_value = State()


class AdminMaintenanceStates(StatesGroup):
    waiting_message = State()


class AdminWelcomeStates(StatesGroup):
    waiting_message = State()


class AdminSettingsStates(StatesGroup):
    waiting_value = State()


class AdminMultiAdminStates(StatesGroup):
    waiting_admin_id = State()


class AdminSendMessageStates(StatesGroup):
    waiting_user_id = State()
    waiting_message = State()


class AdminImportExportStates(StatesGroup):
    """states لاستيراد وتصدير البيانات."""
    waiting_import_file = State()
    confirming_import = State()
```

### `tasks/__init__.py`

```python

```

### `tasks/backup_job.py`

```python
"""
مهمة البكاب اليومي لقاعدة البيانات.
تُرسل نسخة من قاعدة البيانات لقناة البكاب الخاصة.
"""
import logging
import os
from datetime import datetime

from services.notification_service import NotificationService

logger = logging.getLogger(__name__)

DB_PATH = "bot_database.db"


async def daily_backup(bot):
    """
    يأخذ نسخة احتياطية من قاعدة البيانات
    ويرسلها لقناة البكاب.
    """
    notifier = NotificationService(bot)

    if not os.path.exists(DB_PATH):
        logger.warning(
            f"ملف قاعدة البيانات غير موجود: {DB_PATH}"
        )
        return

    try:
        with open(DB_PATH, "rb") as f:
            db_bytes = f.read()

        file_size_mb = len(db_bytes) / (1024 * 1024)
        now = datetime.utcnow()
        filename = (
            f"backup_{now.strftime('%Y%m%d_%H%M%S')}.db"
        )

        caption = (
            f"💾 <b>نسخة احتياطية تلقائية</b>\n\n"
            f"📅 التاريخ: {now.strftime('%Y-%m-%d %H:%M')} UTC\n"
            f"📦 الحجم: {file_size_mb:.2f} MB\n"
            f"📂 الملف: {filename}"
        )

        success = await notifier.notify_backup_channel(
            document_bytes=db_bytes,
            filename=filename,
            caption=caption,
        )

        if success:
            logger.info(
                f"✅ تم إرسال البكاب بنجاح: {filename} "
                f"({file_size_mb:.2f} MB)"
            )
        else:
            logger.warning(
                "⚠️ فشل إرسال البكاب. "
                "تحقق من backup_channel_id في الإعدادات."
            )

    except Exception as e:
        logger.error(f"خطأ في مهمة البكاب: {e}")
```

### `tasks/invoice_monitor.py`

```python
"""
مراقبة الفواتير التلقائية (Sam API + Plisio).

المهام:
1) فحص فواتير USDT عبر Plisio Polling كل 30 ثانية.
2) فحص فواتير شام كاش (Sam API) - تتم يدوياً من المستخدم.
3) تحديث حالة الفواتير المدفوعة/الفاشلة/المنتهية.
4) إضافة الرصيد تلقائياً عند نجاح الدفع.
5) تنظيف الفواتير المنتهية.
6) إشعار المستخدم والأدمن بالنتائج.
"""
import json
import logging
from datetime import datetime

from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select

from database.engine import async_session_maker
from database.models import (
    AutoInvoice, AutoInvoiceMethod, AutoInvoiceStatus,
    TransactionType, User,
)
from services.balance_service import BalanceService
from services.notification_service import NotificationService
from services.plisio_service import (
    plisio_client, PlisioError,
)
from keyboards.main_menu import back_to_main_kb

logger = logging.getLogger(__name__)


async def check_pending_invoices(bot):
    """
    مهمة رئيسية تُشغَّل كل 30 ثانية.
    تفحص كل الفواتير المعلّقة.
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(AutoInvoice).where(
                AutoInvoice.status == AutoInvoiceStatus.PENDING
            )
        )
        invoices = result.scalars().all()

        if not invoices:
            return

        logger.debug(
            f"فحص {len(invoices)} فاتورة معلّقة..."
        )

        for invoice in invoices:
            try:
                if datetime.utcnow() > invoice.expires_at:
                    await _expire_invoice(
                        session, invoice, bot
                    )
                    continue

                if invoice.method == AutoInvoiceMethod.USDT_AUTO:
                    await _check_usdt_invoice(
                        session, invoice, bot
                    )
                elif invoice.method == AutoInvoiceMethod.SHAMCASH_AUTO:
                    # شام كاش يعتمد على التحقق اليدوي
                    # من المستخدم (يرسل رقم العملية)
                    # لذلك لا نفحصها هنا
                    pass

            except Exception as e:
                logger.error(
                    f"خطأ فحص الفاتورة #{invoice.id}: {e}"
                )


async def _check_usdt_invoice(
    session, invoice: AutoInvoice, bot
):
    """يفحص فاتورة USDT عبر Plisio."""
    try:
        info = await plisio_client.get_payment_info(
            uuid=invoice.external_invoice_id
        )
    except PlisioError as e:
        logger.warning(
            f"فشل فحص فاتورة #{invoice.id}: {e}"
        )
        return

    status = info.get("status", "process")

    if plisio_client.is_paid_status(status):
        await _process_paid_usdt_invoice(
            session, invoice, info, bot
        )
    elif plisio_client.is_failed_status(status):
        await _process_failed_invoice(
            session, invoice, bot, "فشل الدفع"
        )


async def _process_paid_usdt_invoice(
    session, invoice: AutoInvoice, info: dict, bot
):
    """يعالج فاتورة USDT مدفوعة."""
    if invoice.status == AutoInvoiceStatus.PAID:
        return

    invoice.status = AutoInvoiceStatus.PAID
    invoice.paid_at = datetime.utcnow()
    invoice.raw_data = json.dumps(
        info, ensure_ascii=False, default=str
    )
    await session.commit()

    user = await BalanceService.add_balance(
        session,
        invoice.user_id,
        invoice.amount_usd,
        TransactionType.DEPOSIT,
        description=(
            f"شحن USDT تلقائي - "
            f"فاتورة #{invoice.id}"
        ),
        related_table="auto_invoices",
        related_id=invoice.id,
    )

    notifier = NotificationService(bot)

    await notifier.notify_user(
        user.telegram_id,
        f"✅ <b>تم شحن رصيدك بنجاح!</b>\n\n"
        f"₮ المبلغ المستلم: <b>{invoice.amount_original} USDT</b>\n"
        f"💰 المضاف للرصيد: <b>{invoice.amount_usd}$</b>\n\n"
        f"يمكنك الآن استخدام رصيدك."
    )

    await notifier.notify_admin(
        f"₮ <b>شحن USDT تلقائي (Plisio)</b>\n\n"
        f"👤 المستخدم: {user.telegram_id} "
        f"(@{user.username or '-'})\n"
        f"💵 المبلغ: <b>{invoice.amount_usd}$</b>\n"
        f"💰 USDT: {invoice.amount_original}\n"
        f"🌐 الشبكة: TRC20\n"
        f"🆔 فاتورة: #{invoice.id}"
    )

    if invoice.status_chat_id and invoice.status_message_id:
        try:
            await bot.edit_message_text(
                chat_id=invoice.status_chat_id,
                message_id=invoice.status_message_id,
                text=(
                    "✅ <b>تم استلام الدفع بنجاح!</b>\n\n"
                    f"💰 أُضيف <b>{invoice.amount_usd}$</b> "
                    f"إلى رصيدك."
                ),
                reply_markup=back_to_main_kb(),
            )
        except TelegramBadRequest:
            pass

    logger.info(
        f"فاتورة USDT #{invoice.id} مدفوعة "
        f"({invoice.amount_usd}$)"
    )


async def _process_failed_invoice(
    session, invoice: AutoInvoice, bot, reason: str
):
    """يعالج فاتورة فاشلة."""
    if invoice.status != AutoInvoiceStatus.PENDING:
        return

    invoice.status = AutoInvoiceStatus.FAILED
    await session.commit()

    user = await session.get(User, invoice.user_id)
    if not user:
        return

    notifier = NotificationService(bot)
    text = (
        f"❌ <b>فشلت الفاتورة</b>\n\n"
        f"السبب: {reason}\n"
        f"يمكنك إنشاء فاتورة جديدة."
    )

    if invoice.status_chat_id and invoice.status_message_id:
        try:
            await bot.edit_message_text(
                chat_id=invoice.status_chat_id,
                message_id=invoice.status_message_id,
                text=text,
                reply_markup=back_to_main_kb(),
            )
            return
        except TelegramBadRequest:
            pass

    await notifier.notify_user(user.telegram_id, text)


async def _expire_invoice(
    session, invoice: AutoInvoice, bot
):
    """يعالج فاتورة منتهية الصلاحية."""
    if invoice.status != AutoInvoiceStatus.PENDING:
        return

    # قبل تسجيلها كمنتهية، نفحصها مرة أخيرة
    # لعل الدفع تم في اللحظات الأخيرة
    if invoice.method == AutoInvoiceMethod.USDT_AUTO:
        try:
            info = await plisio_client.get_payment_info(
                uuid=invoice.external_invoice_id
            )
            status = info.get("status", "")
            if plisio_client.is_paid_status(status):
                await _process_paid_usdt_invoice(
                    session, invoice, info, bot
                )
                return
        except Exception:
            pass

    invoice.status = AutoInvoiceStatus.EXPIRED
    await session.commit()

    user = await session.get(User, invoice.user_id)
    if not user:
        return

    text = (
        f"⌛ <b>انتهت صلاحية الفاتورة</b>\n\n"
        f"يمكنك إنشاء فاتورة جديدة إذا رغبت."
    )

    if invoice.status_chat_id and invoice.status_message_id:
        try:
            await bot.edit_message_text(
                chat_id=invoice.status_chat_id,
                message_id=invoice.status_message_id,
                text=text,
                reply_markup=back_to_main_kb(),
            )
            return
        except TelegramBadRequest:
            pass

    notifier = NotificationService(bot)
    await notifier.notify_user(user.telegram_id, text)

    logger.info(
        f"فاتورة #{invoice.id} انتهت صلاحيتها."
    )
```

### `tasks/order_monitor.py`

```python
"""
مهام الخلفية (Background Jobs).
1) check_pending_orders: فحص طلبات الأرقام المعلّقة.
2) update_provider_status: تحديث رصيد وحالة المزودين.
3) cleanup_balance_locks: تنظيف أقفال الرصيد.
"""
import logging
from datetime import datetime
from decimal import Decimal

from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select

from database.engine import async_session_maker
from database.models import (
    NumberOrder, OrderStatus, TransactionType,
    User, ProviderStatus, ProviderName,
)
from providers.manager import provider_manager
from providers.countries import get_number_service_by_code
from services.balance_service import BalanceService
from services.notification_service import NotificationService
from services.settings_service import SettingsService
from services.cashback_service import CashbackService
from keyboards.numbers import code_received_kb

logger = logging.getLogger(__name__)


async def check_pending_orders(bot):
    notifier = NotificationService(bot)
    async with async_session_maker() as session:
        result = await session.execute(
            select(NumberOrder).where(
                NumberOrder.status == OrderStatus.PENDING
            )
        )
        orders = result.scalars().all()

        for order in orders:
            try:
                if (
                    order.expires_at
                    and datetime.utcnow() > order.expires_at
                ):
                    if order.awaiting_extra_code:
                        order.status = OrderStatus.COMPLETED
                        order.awaiting_extra_code = False
                        await session.commit()
                        continue
                    await _expire_and_refund(
                        session, order, notifier, bot
                    )
                    continue

                await _update_countdown(bot, order)

                status_result = await provider_manager.check_status(
                    order.provider,
                    order.provider_order_id,
                )

                if (
                    status_result.status == "code_received"
                    and status_result.sms_code
                ):
                    await _handle_code_received(
                        session, order, status_result,
                        notifier, bot,
                    )
                elif status_result.status == "cancelled":
                    await _expire_and_refund(
                        session, order, notifier, bot
                    )

            except Exception as e:
                logger.error(
                    f"خطأ فحص الطلب {order.id}: {e}"
                )


async def _handle_code_received(
    session, order, status_result, notifier, bot
):
    user = await session.get(User, order.user_id)

    if order.sms_code and order.awaiting_extra_code:
        existing = (
            order.extra_codes.split(",")
            if order.extra_codes
            else []
        )
        if status_result.sms_code not in existing:
            existing.append(status_result.sms_code)
            order.extra_codes = ",".join(existing)
            order.awaiting_extra_code = False
            order.status = OrderStatus.COMPLETED
            await session.commit()
            await notifier.notify_user(
                user.telegram_id,
                "✅ <b>وصل الكود الإضافي!</b>\n\n"
                f"📱 الرقم: <code>{order.phone_number}</code>\n"
                f"🔑 الكود: <code>{status_result.sms_code}</code>"
            )
        return

    order.status = OrderStatus.COMPLETED
    order.sms_code = status_result.sms_code
    order.full_sms_text = status_result.full_text
    order.completed_at = datetime.utcnow()
    await session.commit()

    try:
        await provider_manager.finish_order(
            order.provider, order.provider_order_id
        )
    except Exception as e:
        logger.warning(
            f"تعذّر إتمام الطلب {order.id} لدى المزود: {e}"
        )

    code_text = (
        "✅ <b>وصل الكود!</b>\n\n"
        f"📱 الرقم: <code>{order.phone_number}</code>\n"
        f"🔑 الكود: <code>{status_result.sms_code}</code>\n\n"
        f"📩 النص الكامل:\n{status_result.full_text or '—'}"
    )

    if order.status_chat_id and order.status_message_id:
        try:
            await bot.edit_message_text(
                chat_id=order.status_chat_id,
                message_id=order.status_message_id,
                text=code_text,
                reply_markup=code_received_kb(order.id),
            )
        except TelegramBadRequest:
            await notifier.notify_user(
                user.telegram_id, code_text
            )
    else:
        await notifier.notify_user(
            user.telegram_id, code_text
        )

    # ── كاشباك ──
    await CashbackService.apply_cashback(
        session, user.id,
        order.id, "number_orders",
        order.price_sell_usd,
    )

    # ── إشعار القناة العامة ──
    service = await get_number_service_by_code(
        session, order.service
    )
    service_name = (
        service.name_ar if service else order.service
    )
    await notifier.notify_successful_number_order(
        username=user.username,
        full_name=user.full_name,
        service_name=service_name,
        price_usd=str(order.price_sell_usd),
    )


async def _update_countdown(bot, order):
    if not (
        order.status_chat_id
        and order.status_message_id
        and order.expires_at
    ):
        return

    remaining = order.expires_at - datetime.utcnow()
    if remaining.total_seconds() <= 0:
        return

    minutes, seconds = divmod(
        int(remaining.total_seconds()), 60
    )
    try:
        await bot.edit_message_text(
            chat_id=order.status_chat_id,
            message_id=order.status_message_id,
            text=(
                "✅ <b>تم شراء الرقم بنجاح!</b>\n\n"
                f"📱 الرقم: <code>{order.phone_number}</code>\n"
                f"⏳ بانتظار الكود... "
                f"المتبقي: {minutes}:{seconds:02d}\n\n"
                "سيتم التحديث تلقائياً."
            ),
        )
    except TelegramBadRequest:
        pass


async def _expire_and_refund(
    session, order, notifier, bot
):
    order.status = OrderStatus.EXPIRED
    await session.commit()

    try:
        await provider_manager.cancel_order(
            order.provider, order.provider_order_id
        )
    except Exception as e:
        logger.warning(
            f"تعذّر إلغاء الطلب {order.id} لدى المزود: {e}"
        )

    user = await BalanceService.add_balance(
        session, order.user_id,
        order.price_sell_usd,
        TransactionType.REFUND,
        description=(
            f"استرجاع - انتهت صلاحية الطلب #{order.id}"
        ),
        related_table="number_orders",
        related_id=order.id,
    )
    order.status = OrderStatus.REFUNDED
    await session.commit()

    text = (
        f"⌛ <b>انتهت صلاحية الرقم</b> "
        f"<code>{order.phone_number}</code>\n"
        f"💰 تم استرجاع <b>{order.price_sell_usd}$</b> "
        f"إلى رصيدك تلقائياً."
    )

    if order.status_chat_id and order.status_message_id:
        try:
            await bot.edit_message_text(
                chat_id=order.status_chat_id,
                message_id=order.status_message_id,
                text=text,
            )
            return
        except TelegramBadRequest:
            pass
    await notifier.notify_user(user.telegram_id, text)


async def update_provider_status(bot):
    notifier = NotificationService(bot)
    threshold = await SettingsService.get_decimal(
        "provider_low_balance_threshold", Decimal("10")
    )

    async with async_session_maker() as session:
        for provider in ProviderName:
            status = await session.get(
                ProviderStatus, provider
            )
            if status is None:
                continue

            try:
                balance = await provider_manager.get_balance(
                    provider
                )
                was_offline = not status.is_online
                status.balance = balance
                status.is_online = True
                status.last_error = None

                if balance < threshold:
                    await notifier.notify_provider_low_balance(
                        provider_name=provider.value,
                        balance=str(balance),
                        threshold=str(threshold),
                    )

            except Exception as e:
                was_online = status.is_online
                status.is_online = False
                status.last_error = str(e)[:500]

                if was_online:
                    await notifier.notify_provider_offline(
                        provider_name=provider.value,
                        error=str(e)[:200],
                    )

            status.last_checked_at = datetime.utcnow()

        await session.commit()


async def cleanup_balance_locks():
    removed = BalanceService.cleanup_idle_locks()
    if removed:
        logger.debug(
            f"تم تنظيف {removed} قفل رصيد غير مستخدم."
        )
```

### `tasks/unified_order_monitor.py`

```python
"""
مراقبة طلبات الألعاب والتطبيقات والـ SMM (UnifiedOrder).
تُفحص كل دقيقتين لأن هذه الطلبات لا تحتاج سرعة
مثل طلبات الأرقام.
"""
import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.engine import async_session_maker
from database.models import (
    UnifiedOrder, UnifiedOrderStatus,
    TransactionType, User,
)
from providers.games_provider import (
    GamesProviderClient, GamesProviderError
)
from providers.smm_provider import (
    SMMProviderClient, SMMProviderError
)
from services.balance_service import BalanceService
from services.notification_service import NotificationService
from services.dynamic_service import DynamicService

logger = logging.getLogger(__name__)


async def check_unified_orders(bot):
    """
    يفحص كل الطلبات الموحدة المعلّقة أو قيد المعالجة.
    """
    notifier = NotificationService(bot)

    async with async_session_maker() as session:
        result = await session.execute(
            select(UnifiedOrder)
            .where(
                UnifiedOrder.status.in_([
                    UnifiedOrderStatus.PENDING,
                    UnifiedOrderStatus.PROCESSING,
                ])
            )
            .options(
                selectinload(UnifiedOrder.product),
                selectinload(UnifiedOrder.api_provider),
                selectinload(UnifiedOrder.user),
            )
        )
        orders = result.scalars().all()

        if not orders:
            return

        logger.debug(
            f"فحص {len(orders)} طلب موحد معلّق..."
        )

        for order in orders:
            try:
                await _process_unified_order(
                    session, order, notifier, bot
                )
            except Exception as e:
                logger.error(
                    f"خطأ فحص الطلب الموحد {order.id}: {e}"
                )


async def _process_unified_order(
    session, order: UnifiedOrder,
    notifier: NotificationService, bot
):
    """يعالج طلباً موحداً واحداً."""

    if not order.api_provider or not order.external_order_id:
        if order.status == UnifiedOrderStatus.PENDING:
            logger.warning(
                f"الطلب #{order.id} بدون مزود أو رقم خارجي، "
                f"يُعتبر مكتملاً يدوياً."
            )
        return

    provider = order.api_provider
    if not provider.is_active:
        return

    try:
        if provider.type.value == "smm":
            client = SMMProviderClient(provider)
        else:
            client = GamesProviderClient(provider)

        status_data = await client.check_order_status(
            order.external_order_id
        )
    except (GamesProviderError, SMMProviderError) as e:
        logger.warning(
            f"فشل فحص الطلب #{order.id} من المزود: {e}"
        )
        provider.last_error = str(e)[:500]
        await session.commit()
        return
    except Exception as e:
        logger.error(
            f"خطأ غير متوقع فحص الطلب #{order.id}: {e}"
        )
        return

    new_status = status_data.get("status", "pending")
    start_count = status_data.get("start_count")
    remains = status_data.get("remains")

    if start_count is not None:
        order.start_count = start_count
    if remains is not None:
        order.remains = remains

    order.result_data = json.dumps(
        status_data.get("raw", {}),
        ensure_ascii=False,
    )

    user = order.user
    product_name = (
        order.product.name_ar
        if order.product
        else "خدمة"
    )

    if new_status == "completed":
        await _handle_completed(
            session, order, user, product_name, notifier
        )

    elif new_status == "partial":
        await _handle_partial(
            session, order, user, product_name,
            notifier, remains,
        )

    elif new_status == "failed":
        await _handle_failed(
            session, order, user, product_name, notifier
        )

    elif new_status == "processing":
        if order.status != UnifiedOrderStatus.PROCESSING:
            order.status = UnifiedOrderStatus.PROCESSING
            order.status_message = "قيد التنفيذ"
            await session.commit()
            await notifier.notify_user(
                user.telegram_id,
                f"🔄 <b>طلبك قيد التنفيذ</b>\n\n"
                f"🛒 المنتج: {product_name}\n"
                f"🆔 رقم الطلب: #{order.id}\n"
                "سيصلك إشعار عند الاكتمال."
            )

    await session.commit()


async def _handle_completed(
    session, order, user, product_name, notifier
):
    """يعالج الطلب المكتمل."""
    order.status = UnifiedOrderStatus.COMPLETED
    order.status_message = "مكتمل"
    order.completed_at = datetime.utcnow()
    await session.commit()

    if order.product:
        await DynamicService.increment_product_sold(
            session, order.product_id
        )

    await notifier.notify_order_completed(
        user_telegram_id=user.telegram_id,
        product_name=product_name,
        result_text=(
            f"✅ تم تنفيذ طلبك بنجاح!\n"
            f"🆔 رقم الطلب: #{order.id}"
        ),
    )

    await notifier.notify_successful_unified_order(
        username=user.username,
        full_name=user.full_name,
        product_name=product_name,
        price_usd=str(order.price_usd),
    )

    logger.info(
        f"الطلب الموحد #{order.id} اكتمل بنجاح."
    )


async def _handle_partial(
    session, order, user, product_name,
    notifier, remains
):
    """
    يعالج الطلب الجزئي.
    يسترجع الفرق بين ما طُلب وما نُفِّذ.
    """
    order.status = UnifiedOrderStatus.PARTIAL
    order.status_message = f"جزئي - متبقي: {remains}"
    order.completed_at = datetime.utcnow()

    if (
        remains
        and order.quantity > 0
        and order.price_usd > 0
    ):
        from decimal import Decimal
        price_per_unit = order.price_usd / Decimal(
            str(order.quantity)
        )
        refund_amount = price_per_unit * Decimal(
            str(remains)
        )

        if refund_amount > 0:
            await BalanceService.add_balance(
                session, user.id, refund_amount,
                TransactionType.REFUND,
                description=(
                    f"استرجاع جزئي - طلب #{order.id} "
                    f"({remains} متبقي)"
                ),
                related_table="unified_orders",
                related_id=order.id,
            )

            await notifier.notify_user(
                user.telegram_id,
                f"⚠️ <b>طلب منجز جزئياً</b>\n\n"
                f"🛒 المنتج: {product_name}\n"
                f"🆔 رقم الطلب: #{order.id}\n"
                f"📊 المتبقي غير منجز: {remains}\n"
                f"💰 تم استرجاع <b>{refund_amount:.4f}$</b> "
                f"لرصيدك."
            )
    else:
        await notifier.notify_user(
            user.telegram_id,
            f"⚠️ <b>طلب منجز جزئياً</b>\n\n"
            f"🛒 المنتج: {product_name}\n"
            f"🆔 رقم الطلب: #{order.id}\n"
            "تواصل مع الدعم الفني للمزيد من التفاصيل."
        )

    await session.commit()
    logger.info(
        f"الطلب الموحد #{order.id} منجز جزئياً."
    )


async def _handle_failed(
    session, order, user, product_name, notifier
):
    """يعالج الطلب الفاشل ويسترجع الرصيد."""
    order.status = UnifiedOrderStatus.FAILED
    order.status_message = "فشل التنفيذ"
    order.completed_at = datetime.utcnow()
    await session.commit()

    await BalanceService.add_balance(
        session, user.id, order.price_usd,
        TransactionType.REFUND,
        description=(
            f"استرجاع - فشل تنفيذ الطلب #{order.id}"
        ),
        related_table="unified_orders",
        related_id=order.id,
    )
    order.status = UnifiedOrderStatus.REFUNDED
    await session.commit()

    await notifier.notify_order_failed(
        user_telegram_id=user.telegram_id,
        product_name=product_name,
        amount_usd=str(order.price_usd),
    )

    logger.info(
        f"الطلب الموحد #{order.id} فشل وتم استرجاع "
        f"{order.price_usd}$."
    )
```

