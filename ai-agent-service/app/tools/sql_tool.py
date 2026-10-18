import httpx
from langchain_core.tools import tool
from app.core.config import settings


@tool
async def query_database(order_id: str) -> str:
    """
    Asynchronously queries order and status details from core-backend-service.
    Use this tool to look up customer order details or check order status by order_id.
    """
    print("\n--- [TOOL: CORE BACKEND ORDER LOOKUP] ---")
    print(f"-> Fetching Order ID: '{order_id}' asynchronously...")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.CORE_BACKEND_URL}/orders/{order_id}", timeout=5.0
            )
            if response.status_code == 200:
                print("-> Core Backend Search Complete. Returning data to Agent.")
                return str(response.json())
            return f"Order '{order_id}' not found in backend."
        except Exception as e:
            return f"Backend Service Communication Error: {str(e)}"