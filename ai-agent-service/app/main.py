from fastapi import FastAPI
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from app.core.config import settings
from app.graph import agent_graph

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")


class ChatRequest(BaseModel):
    message: str
    user_id: str | None = None


@app.post("/api/v1/chat")
async def chat(request: ChatRequest):

    initial_state = {
        "messages": [HumanMessage(content=request.message)],
        "user_id": request.user_id,
        "needs_web_search": False,
        "needs_handoff": False,
        "retry_count": 0,
        "grade": "",
    }

    final_state = await agent_graph.ainvoke(initial_state)
    return {"response": final_state["messages"][-1].content}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
