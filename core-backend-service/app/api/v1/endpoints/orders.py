from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import get_db
from app.schemas import OrderResponse
from app.services import order_service

router = APIRouter()


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)):
    return await order_service.get_order_by_id(db=db, order_id=order_id)