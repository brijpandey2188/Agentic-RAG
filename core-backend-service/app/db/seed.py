import asyncio
import sys
from pathlib import Path

# Add project root directory to Python path if executed directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy.future import select

from app.db import AsyncSessionLocal, Order, Refund, engine, Base


async def seed_data():
    # Create tables if missing
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        try:
            # Check existing records
            result = await db.execute(select(Order))
            if result.scalars().first():
                print("Database already contains orders. Skipping seed.")
                return

            orders = [
                Order(order_id="ORD-1001", status="DELIVERED", total_amount=120.50),
                Order(order_id="ORD-1002", status="DELIVERED", total_amount=89.99),
                Order(order_id="ORD-1003", status="PROCESSING", total_amount=210.00),
                Order(order_id="ORD-1004", status="CANCELLED", total_amount=45.00),
                Order(order_id="ORD-1005", status="REFUNDED", total_amount=150.00),
            ]
            db.add_all(orders)

            refund = Refund(
                refund_id="RFD-5001",
                order_id="ORD-1005",
                amount=150.00,
                reason="Customer requested refund",
            )
            db.add(refund)

            await db.commit()
            print("Successfully seeded database asynchronously!")

        except Exception as e:
            await db.rollback()
            print(f"Error seeding database: {e}")
            raise e


if __name__ == "__main__":
    asyncio.run(seed_data())