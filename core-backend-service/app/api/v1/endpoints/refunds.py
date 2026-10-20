from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import get_db
from app.schemas import RefundCreate, RefundResponse
from app.services import refund_service

router = APIRouter()


@router.post("/", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
async def process_refund(refund_in: RefundCreate, db: AsyncSession = Depends(get_db)):
    return await refund_service.create_refund(db=db, refund_in=refund_in)