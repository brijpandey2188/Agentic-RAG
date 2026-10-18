from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db import Order


class OrderService:
    @staticmethod
    async def get_order_by_id(db: AsyncSession, order_id: str) -> Order:
        statement = select(Order).where(Order.order_id == order_id)
        result = await db.execute(statement)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found.")
        return order


order_service = OrderService()