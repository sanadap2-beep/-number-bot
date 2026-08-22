"""Checkout core shared by HTTP clients and future storefronts."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.models import (
    Product,
    ProductFulfillmentType,
    ProductStatus,
    TransactionType,
    UnifiedOrder,
    UnifiedOrderStatus,
)
from protocols.base import ProtocolError
from protocols.factory import ProtocolFactory
from services.balance_service import BalanceService, InsufficientBalanceError
from services.cashback_service import CashbackService
from services.dynamic_service import DynamicService
from services.inventory_service import InventoryError, InventoryService
from services.loyalty_service import LoyaltyService
from services.promotion_service import PromotionService


class CheckoutError(Exception):
    pass


@dataclass
class CheckoutResult:
    order: UnifiedOrder
    discount: Decimal = Decimal("0")
    delivery_value: str | None = None


class CheckoutService:
    @staticmethod
    def calculate_total(product: Product, quantity: int) -> Decimal:
        if quantity < 1:
            raise CheckoutError("الكمية يجب أن تكون أكبر من صفر.")
        if not product.requires_quantity and quantity != 1:
            raise CheckoutError("هذا المنتج لا يقبل كمية متعددة.")
        if product.requires_quantity:
            if quantity < product.min_quantity or quantity > product.max_quantity:
                raise CheckoutError(
                    f"الكمية يجب أن تكون بين {product.min_quantity} و{product.max_quantity}."
                )
            total = (
                product.price_usd
                * Decimal(str(quantity))
                / Decimal(str(product.min_quantity))
            )
        else:
            total = product.price_usd
        return total.quantize(Decimal("0.0001"))

    @staticmethod
    async def _get_product(session, product_id: int) -> Product:
        result = await session.execute(
            select(Product)
            .options(selectinload(Product.api_provider), selectinload(Product.sub_category))
            .where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        if product is None or product.status != ProductStatus.ACTIVE:
            raise CheckoutError("المنتج غير موجود أو غير متاح.")
        return product

    @staticmethod
    async def purchase(
        session,
        user_id: int,
        product_id: int,
        target: str = "",
        quantity: int = 1,
    ) -> CheckoutResult:
        product = await CheckoutService._get_product(session, product_id)
        fulfillment = getattr(product.fulfillment_type, "value", product.fulfillment_type)
        total = CheckoutService.calculate_total(product, quantity)
        promotion, discount = await PromotionService.get_best_promotion(
            session, product.id, total
        )
        price = total - discount

        if fulfillment == ProductFulfillmentType.INVENTORY.value:
            if target:
                raise CheckoutError("منتج المخزون لا يحتاج هدفاً.")
            try:
                order, delivery, _metadata = await InventoryService.purchase(
                    session,
                    user_id=user_id,
                    product_id=product.id,
                    price_usd=price,
                    quantity=quantity,
                    promotion_id=promotion.id if promotion else None,
                )
            except (InventoryError, InsufficientBalanceError) as exc:
                raise CheckoutError(str(exc)) from exc
            if promotion:
                await PromotionService.mark_used(session, promotion.id)
            await DynamicService.increment_product_sold(session, product.id, quantity)
            await CashbackService.apply_cashback(
                session, user_id, order.id, "unified_orders", price
            )
            await LoyaltyService.award_purchase_points(
                session, user_id, "unified_orders", order.id, price
            )
            return CheckoutResult(order, discount, delivery)

        if fulfillment != ProductFulfillmentType.API.value:
            raise CheckoutError("المنتج غير قابل للشراء التلقائي.")
        if (product.requires_link or product.requires_player_id) and not target:
            raise CheckoutError("هذا المنتج يحتاج رابطاً أو معرفاً لإتمام الطلب.")
        if not product.api_provider_id or not product.provider_service_id:
            raise CheckoutError("مزود المنتج غير مضبوط.")
        provider = product.api_provider
        if provider is None or not provider.is_active:
            raise CheckoutError("مزود المنتج غير متاح حالياً.")

        try:
            await BalanceService.deduct_balance(
                session,
                user_id,
                price,
                TransactionType.PURCHASE,
                description=f"شراء {product.name_ar}",
                is_purchase=True,
            )
        except InsufficientBalanceError as exc:
            raise CheckoutError(str(exc)) from exc

        try:
            protocol = ProtocolFactory.create_from_provider(provider)
            external = await protocol.place_order(
                service_id=product.provider_service_id,
                target=target,
                quantity=quantity,
            )
        except ProtocolError as exc:
            await BalanceService.add_balance(
                session,
                user_id,
                price,
                TransactionType.REFUND,
                description="استرجاع - فشل مزود المنتج",
            )
            raise CheckoutError("فشل إرسال الطلب للمزود وتم استرجاع الرصيد.") from exc

        order = UnifiedOrder(
            user_id=user_id,
            product_id=product.id,
            api_provider_id=product.api_provider_id,
            promotion_id=promotion.id if promotion else None,
            external_order_id=external.external_order_id,
            target=target,
            quantity=quantity,
            price_usd=price,
            cost_price_usd=product.cost_price_usd,
            status=UnifiedOrderStatus.PROCESSING,
            status_message="تم إرسال الطلب للمزود",
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)
        if promotion:
            await PromotionService.mark_used(session, promotion.id)
        return CheckoutResult(order, discount)
