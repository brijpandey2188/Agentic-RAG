import httpx
from langchain_core.tools import tool
from app.core.config import settings


@tool
async def process_order_refund(order_id: str, amount: float = 0.0, reason: str = "Requested by customer") -> str:
    """
    Asynchronously submits a refund request to core-backend-service.
    Executes a refund and updates order status to REFUNDED.
    """
    print("\n--- [TOOL: CORE BACKEND REFUND PROCESSOR] ---")
    print(f"-> Submitting refund for Order ID: '{order_id}' asynchronously...")

    async with httpx.AsyncClient() as client:
        try:
            payload = {
                "order_id": order_id,
                "amount": amount,
                "reason": reason
            }
            response = await client.post(
                f"{settings.CORE_BACKEND_URL}/refunds/",
                json=payload,
                timeout=5.0
            )
            if response.status_code == 201:
                print("-> Refund processed successfully. Returning confirmation to Agent.")
                return str(response.json())
            return f"Refund process failed: {response.text}"
        except Exception as e:
            return f"Backend Service Communication Error: {str(e)}"