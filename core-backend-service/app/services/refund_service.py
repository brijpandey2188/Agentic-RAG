import uuid
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db import Order, Refund
from app.schemas import RefundCreate


class RefundService:
    @staticmethod
    async def create_refund(db: AsyncSession, refund_in: RefundCreate) -> Refund:
        # 1. Asynchronously fetch the target order
        statement = select(Order).where(Order.order_id == refund_in.order_id)
        result = await db.execute(statement)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail=f"Order {refund_in.order_id} not found.")

        if refund_in.amount > order.total_amount:
            raise HTTPException(
                status_code=400,
                detail=f"Refund amount (${refund_in.amount}) exceeds total order amount (${order.total_amount}).",
            )

        # 2. Build refund record
        refund_record = Refund(
            refund_id=f"RFD-{uuid.uuid4().hex[:8].upper()}",
            order_id=refund_in.order_id,
            amount=refund_in.amount,
            reason=refund_in.reason,
        )

        order.status = "refunded" if refund_in.amount == order.total_amount else "partially_refunded"

        # 3. Asynchronous commit and refresh
        db.add(refund_record)
        await db.commit()
        await db.refresh(refund_record)
        return refund_record


refund_service = RefundService()