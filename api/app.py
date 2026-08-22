"""HTTP API and Telegram Mini App application."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from api.admin import router as admin_router
from api.deps import get_current_user, get_session
from api.schemas import (
    CatalogOut,
    CategoryOut,
    GiftRedeemIn,
    MeOut,
    OrderOut,
    ProductOut,
    SubCategoryOut,
    WatchIn,
)
from config import settings
from database.models import (
    Category,
    NumberOrder,
    Product,
    SubCategory,
    ProductReview,
    ProductStatus,
    ProductWatch,
    UnifiedOrder,
    User,
)
from database.seed import init_db
from services.gift_service import GiftCodeError, GiftService
from services.loyalty_service import LoyaltyService
from services.promotion_service import PromotionService
from services.watch_service import WatchService


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Number Bot Marketplace API",
    version="2.0.0",
    lifespan=lifespan,
)
origins = [settings.WEBAPP_URL] if settings.WEBAPP_URL else []
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(admin_router)


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
async def ready(session=Depends(get_session)):
    try:
        await session.execute(select(1))
        return {"status": "ok", "database": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/app/")


async def _review_map(session, product_ids: list[int]) -> dict[int, tuple[Decimal, int]]:
    if not product_ids:
        return {}
    result = await session.execute(
        select(
            ProductReview.product_id,
            func.avg(ProductReview.rating),
            func.count(ProductReview.id),
        )
        .where(ProductReview.product_id.in_(product_ids))
        .group_by(ProductReview.product_id)
    )
    return {
        product_id: (Decimal(str(avg)).quantize(Decimal("0.1")), count)
        for product_id, avg, count in result.all()
    }


async def _promotion_map(session, products: list[Product]) -> dict[int, dict]:
    promotions = await PromotionService.get_active_promotions(session, limit=200)
    result = {}
    for promotion in promotions:
        product = promotion.product
        if not product:
            continue
        discount = PromotionService.calculate_discount(
            promotion, product.price_usd
        )
        current = result.get(product.id)
        if current is None or discount > current["discount"]:
            result[product.id] = {
                "id": promotion.id,
                "name": promotion.name,
                "discount": discount,
                "discounted_price": product.price_usd - discount,
                "ends_at": promotion.ends_at.isoformat(),
            }
    return result


@app.get("/api/v1/catalog", response_model=CatalogOut)
async def catalog(session=Depends(get_session)):
    result = await session.execute(
        select(Category)
        .options(
            selectinload(Category.sub_categories)
            .selectinload(SubCategory.products)
        )
        .where(Category.is_active.is_(True))
        .order_by(Category.sort_order, Category.id)
    )
    categories = list(result.scalars().unique().all())
    products = [
        product
        for category in categories
        for subcategory in category.sub_categories
        for product in subcategory.products
        if product.status == ProductStatus.ACTIVE
    ]
    ratings = await _review_map(session, [product.id for product in products])
    promotions = await _promotion_map(session, products)

    def product_out(product: Product) -> ProductOut:
        average, count = ratings.get(product.id, (None, 0))
        promotion = promotions.get(product.id)
        promotion_payload = None
        if promotion:
            promotion_payload = {
                key: str(value) if isinstance(value, Decimal) else value
                for key, value in promotion.items()
            }
        return ProductOut(
            id=product.id,
            name=product.name_ar,
            description=product.description,
            price_usd=product.price_usd,
            display_type=product.display_type.value,
            min_quantity=product.min_quantity,
            max_quantity=product.max_quantity,
            requires_link=product.requires_link,
            requires_quantity=product.requires_quantity,
            requires_player_id=product.requires_player_id,
            fulfillment_type=product.fulfillment_type.value,
            rating=average,
            reviews_count=count,
            promotion=promotion_payload,
        )

    output = []
    for category in categories:
        subcategories = []
        for subcategory in category.sub_categories:
            if not subcategory.is_active:
                continue
            active_products = [
                product_out(product)
                for product in subcategory.products
                if product.status == ProductStatus.ACTIVE
            ]
            if active_products:
                subcategories.append(
                    SubCategoryOut(
                        id=subcategory.id,
                        name=subcategory.name_ar,
                        emoji=subcategory.emoji,
                        products=active_products,
                    )
                )
        if subcategories:
            output.append(
                CategoryOut(
                    id=category.id,
                    name=category.name_ar,
                    emoji=category.emoji,
                    type=category.type.value,
                    sub_categories=subcategories,
                )
            )
    return CatalogOut(
        categories=output,
        generated_at=datetime.utcnow().isoformat(),
    )


@app.get("/api/v1/me", response_model=MeOut)
async def me(
    current_user: User = Depends(get_current_user),
):
    tier = LoyaltyService.tier_for_points(current_user.loyalty_points or 0)
    return MeOut(
        telegram_id=current_user.telegram_id,
        username=current_user.username,
        full_name=current_user.full_name,
        balance_usd=current_user.balance,
        loyalty_points=current_user.loyalty_points or 0,
        loyalty_streak=current_user.loyalty_streak or 0,
        loyalty_tier=f"{tier.emoji} {tier.name}",
    )


@app.get("/api/v1/orders", response_model=list[OrderOut])
async def orders(
    current_user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    result = await session.execute(
        select(UnifiedOrder)
        .options(selectinload(UnifiedOrder.product))
        .where(UnifiedOrder.user_id == current_user.id)
        .order_by(UnifiedOrder.created_at.desc())
        .limit(100)
    )
    unified = list(result.scalars().all())
    number_result = await session.execute(
        select(NumberOrder)
        .where(NumberOrder.user_id == current_user.id)
        .order_by(NumberOrder.purchased_at.desc())
        .limit(100)
    )
    numbers = list(number_result.scalars().all())
    output = [
        OrderOut(
            order_type="unified",
            id=order.id,
            product_id=order.product_id,
            product_name=order.product.name_ar if order.product else None,
            status=order.status.value,
            price_usd=order.price_usd,
            quantity=order.quantity,
            target=order.target,
            created_at=order.created_at.isoformat(),
            completed_at=order.completed_at.isoformat() if order.completed_at else None,
            status_message=order.status_message,
        )
        for order in unified
    ]
    output.extend(
        OrderOut(
            order_type="numbers",
            id=order.id,
            product_id=None,
            product_name=f"رقم {order.service}",
            status=order.status.value,
            price_usd=order.price_sell_usd,
            quantity=1,
            target=order.phone_number,
            created_at=order.purchased_at.isoformat(),
            completed_at=order.completed_at.isoformat() if order.completed_at else None,
            status_message=order.sms_code,
        )
        for order in numbers
    )
    return sorted(output, key=lambda item: item.created_at, reverse=True)[:100]


@app.get("/api/v1/watches")
async def watches(
    current_user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    rows = await WatchService.list_user_watches(session, current_user.id)
    return [
        {
            "product_id": row.product_id,
            "product_name": row.product.name_ar if row.product else None,
            "price_usd": row.product.price_usd if row.product else None,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@app.post("/api/v1/watches")
async def add_watch(
    payload: WatchIn,
    current_user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    result = await session.execute(
        select(ProductWatch).where(
            ProductWatch.user_id == current_user.id,
            ProductWatch.product_id == payload.product_id,
        )
    )
    if result.scalar_one_or_none() is None:
        await WatchService.toggle(session, current_user.id, payload.product_id)
    return {"status": "watching", "product_id": payload.product_id}


@app.delete("/api/v1/watches/{product_id}")
async def remove_watch(
    product_id: int,
    current_user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    result = await session.execute(
        select(ProductWatch).where(
            ProductWatch.user_id == current_user.id,
            ProductWatch.product_id == product_id,
        )
    )
    watch = result.scalar_one_or_none()
    if watch:
        await session.delete(watch)
        await session.commit()
    return {"status": "not_watching", "product_id": product_id}


@app.post("/api/v1/gifts/redeem")
async def redeem_gift(
    payload: GiftRedeemIn,
    current_user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    try:
        amount = await GiftService.redeem(session, current_user.id, payload.code)
    except GiftCodeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "redeemed", "amount_usd": amount}


webapp_dir = Path(__file__).resolve().parent.parent / "webapp"
app.mount("/app", StaticFiles(directory=webapp_dir, html=True), name="webapp")
app.mount("/admin-assets", StaticFiles(directory=webapp_dir), name="admin-assets")


@app.get("/admin/", include_in_schema=False)
def admin_webapp():
    return FileResponse(webapp_dir / "admin.html")
