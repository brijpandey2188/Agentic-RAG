from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class RefundCreate(BaseModel):
    order_id: str = Field(..., example="ORD-1001")
    amount: Decimal = Field(..., gt=0, example=49.99)
    reason: str = Field(..., example="Defective item received")


class RefundResponse(BaseModel):
    refund_id: str
    order_id: str
    amount: Decimal
    reason: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)