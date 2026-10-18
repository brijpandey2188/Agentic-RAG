from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class OrderBase(BaseModel):
    status: str = Field(..., example="processing")
    total_amount: Decimal = Field(..., gt=0, example=199.99)


class OrderCreate(OrderBase):
    order_id: str = Field(..., example="ORD-1001")


class OrderResponse(OrderBase):
    order_id: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)