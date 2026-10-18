from fastapi import APIRouter
from app.api.v1.endpoints import orders, refunds

api_router = APIRouter()
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(refunds.router, prefix="/refunds", tags=["Refunds"])