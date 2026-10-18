from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    State dictionary tracking conversation history and internal context.
    The `add_messages` reducer automatically appends new messages to the history list.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str | None
    needs_web_search: bool
    grade: str          # NEW: "relevant" | "irrelevant" | "skip"
    retry_count: int
    needs_handoff: bool   # NEW
