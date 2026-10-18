from pydantic import BaseModel, Field
from langchain_core.messages import (
    AIMessage, HumanMessage, SystemMessage, ToolMessage
)
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from app.core.config import settings
from app.graph.state import AgentState
from app.rag.retriever import search_store_policies
from app.tools import process_order_refund, query_database, web_search
from typing import Literal

MAX_RETRIES = 2


TOOLS = [
    query_database,
    process_order_refund,
    search_store_policies,
    web_search
]

# --- SYSTEM PROMPT GUARDRAILS ---
# Enforces tool priority hierarchy and prevents hallucinated web searches
SYSTEM_GUARDRAIL_PROMPT = SystemMessage(
    content=(
        "You are an internal E-Commerce Customer Support Assistant. "
        "Strictly adhere to the following routing rules when assisting users:\n\n"
        "1. INTERNAL POLICY QUERIES: For ANY question about this store's policies, rules, "
        "payments, offers, products or services (returns, warranty, shipping, cancellations, "
        "payment methods, gift cards, etc.), ALWAYS call `search_store_policies` FIRST. "
        "Never answer a store-specific question from your own knowledge without searching.\n"
        "2. ORDER & ACCOUNT QUERIES: For questions checking order status, details, or processing refunds, "
        "use `query_database` or `process_order_refund` with the provided `order_id`.\n"
        "3. FALLBACK RULE: `web_search` is enabled only by the system after internal "
        "search fails. Never decide to search the web on your own.\n"
        "4. GROUNDING: Never override internal company data with external web results. "
        "Base your responses strictly on the data retrieved from internal tools. "
        "State ONLY facts that appear in the retrieved text. Do NOT add details, "
        "names, numbers or conditions that are not in the retrieved documents. "
        "If a detail is not in the documents, say you don't have that information."
    )
)

# llm = ChatOpenAI(
#     model="gpt-4o-mini",
#     openai_api_key=settings.OPENAI_API_KEY,
#     temperature=0
# ).bind_tools(TOOLS)


# AFTER
base_llm = ChatOpenAI(
    model="gpt-4o-mini",
    openai_api_key=settings.OPENAI_API_KEY,
    temperature=0
)


INTERNAL_TOOLS = [query_database, process_order_refund, search_store_policies]
# default: web_search
llm = base_llm.bind_tools(INTERNAL_TOOLS)
# general fallback
llm_with_web = base_llm.bind_tools(TOOLS)
llm_no_tools = base_llm.bind_tools(TOOLS, tool_choice="none")


tool_node = ToolNode(TOOLS)

# --- GRADING ---
WEB_FALLBACK_HINT = SystemMessage(
    content=(
        "Internal policy search did not return relevant results. "
        "You may now use `web_search`. Clearly tell the user that this information "
        "comes from external sources and is NOT official store policy."
    )
)

HANDOFF_HINT = SystemMessage(
    content=(
        "Internal policy search found nothing relevant for this store-specific question. "
        "Tell the user you don't have official information on this and suggest "
        "contacting the support team. Do NOT guess or use general knowledge."
    )
)


class QueryScope(BaseModel):
    """Is the answer specific to this store, or the same for any store?"""
    scope: Literal["company_specific", "general"] = Field(
        description="company_specific if the answer depends on this store's own rules"
    )


scope_llm = ChatOpenAI(
    model="gpt-4o-mini",
    openai_api_key=settings.OPENAI_API_KEY,
    temperature=0
).with_structured_output(QueryScope)

SCOPE_PROMPT = """Classify a customer question sent to an e-commerce store's support assistant.

company_specific: the answer depends on THIS store's own rules, offers, products, payments,
orders or account. Signals: "you", "your", asks what the store allows, offers, accepts or charges.
general: the answer is the same no matter which store you ask (definitions, how something
works in general, public facts, laws).

Examples:
"Do you accept gift cards?" -> company_specific
"Do you ship to Canada?" -> company_specific
"What is your exchange policy?" -> company_specific
"What is a gift card?" -> general
"How does customs duty work on international orders?" -> general
"What is the difference between a warranty and a guarantee?" -> general

If unsure, choose company_specific.

Question: {question}"""


class GradeResult(BaseModel):
    """Binary relevance score for retrieved documents."""
    relevant: bool = Field(
        description="True if the documents help answer the question")


grader_llm = ChatOpenAI(
    model="gpt-4o-mini",
    openai_api_key=settings.OPENAI_API_KEY,
    temperature=0
).with_structured_output(GradeResult)


def _latest_user_question(messages) -> str:
    return next(m.content for m in reversed(messages) if isinstance(m, HumanMessage))


async def _irrelevant_result(state: AgentState) -> dict:
    """Retries बाकी हैं तो rewrite; खत्म हो गए तो question classify करके fallback चुनो."""
    if state.get("retry_count", 0) < MAX_RETRIES:
        print("-> Will rewrite query and retry")
        return {"grade": "irrelevant"}

    result = await scope_llm.ainvoke(
        SCOPE_PROMPT.format(question=_latest_user_question(state["messages"]))
    )
    print(f"-> Retries exhausted | Query scope: {result.scope}")

    if result.scope == "general":
        print("-> Fallback: WEB SEARCH")
        return {"grade": "exhausted", "needs_web_search": True}

    print("-> Fallback: SUPPORT HANDOFF (tools disabled)")
    return {"grade": "exhausted", "needs_handoff": True}


async def grade_documents_node(state: AgentState) -> dict:
    """Grades ONLY search_store_policies output. Baaki tools ke liye skip."""
    messages = list(state["messages"])
    last_ai_idx = max(i for i, m in enumerate(
        messages) if isinstance(m, AIMessage))
    policy_docs = [
        m.content for m in messages[last_ai_idx + 1:]
        if isinstance(m, ToolMessage) and m.name == "search_store_policies"
    ]

    print("\n--- [NODE: GRADE DOCUMENTS] ---")

    # Case 1: is step mein policy retrieval hui hi nahi
    if not policy_docs:
        print("-> No policy retrieval in this step. Skipping grading.")
        return {"grade": "skip"}

    # Case 2: retriever ne khud "nothing found" bola -> LLM call ki zaroorat nahi
    if any(d.startswith(("NO_INTERNAL_POLICY_FOUND", "Error searching")) for d in policy_docs):
        print("-> Retriever returned no usable docs. Grade: IRRELEVANT (LLM call skipped)")
        # return {"grade": "irrelevant", "needs_web_search": True}
        return await _irrelevant_result(state)

    # Case 3: docs mile hain -> LLM se relevance poocho
    result = await grader_llm.ainvoke(
        f"User question: {_latest_user_question(messages)}\n\n"
        f"Retrieved documents:\n{policy_docs}\n\n"
        "Do these documents contain information that answers the question?"
    )

    if result.relevant:
        print("-> Grade: RELEVANT")
        # return {"grade": "relevant"}
        return {"grade": "relevant", "needs_web_search": False, "needs_handoff": False, "retry_count": 0}

    # print("-> Grade: IRRELEVANT -> enabling web fallback")
    # return {"grade": "irrelevant", "needs_web_search": True}
    print("-> Grade: IRRELEVANT")
    return await _irrelevant_result(state)


# --- REWRITE ---
rewriter_llm = ChatOpenAI(
    model="gpt-4o-mini",
    openai_api_key=settings.OPENAI_API_KEY,
    temperature=0
)


def _last_policy_query(messages) -> str:
    """Agent ने पिछली बार search_store_policies में कौन सी query भेजी थी."""
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.tool_calls:
            for tc in m.tool_calls:
                if tc["name"] == "search_store_policies":
                    return tc["args"].get("query", "")
    return ""


async def rewrite_query_node(state: AgentState) -> dict:
    messages = state["messages"]
    response = await rewriter_llm.ainvoke(
        "A vector search over an English e-commerce store-policy knowledge base "
        "returned irrelevant results.\n"
        f"User question: {_latest_user_question(messages)}\n"
        f"Failed search query: {_last_policy_query(messages)}\n\n"
        "Write a better search query in English. Use different keywords or synonyms "
        "and policy terminology (refund, return, cancellation, shipping, warranty). "
        "Return ONLY the query."
    )
    new_query = response.content.strip()
    retry = state.get("retry_count", 0) + 1

    print("\n--- [NODE: REWRITE QUERY] ---")
    print(f"-> Retry #{retry} | New query: {new_query}")

    # SystemMessage इसलिए, ताकि "latest HumanMessage" हमेशा original user question रहे
    return {
        "messages": [SystemMessage(content=(
            "The previous policy search returned irrelevant results. "
            f"Call `search_store_policies` again with this query: {new_query}"
        ))],
        "retry_count": retry,
    }


def route_after_grading(state: AgentState) -> str:
    return "rewrite_query" if state["grade"] == "irrelevant" else "agent"


async def agent_node(state: AgentState) -> dict:
    """
    Primary Async Reasoning Node: Prepends System Guardrail Message to the conversation 
    history before passing to the LLM to govern tool decision-making.
    """
    messages = state["messages"]

    # Prepend the System Guardrail Prompt if it isn't already at the start of conversation history
    if not messages or not isinstance(messages[0], SystemMessage):
        formatted_messages = [SYSTEM_GUARDRAIL_PROMPT] + list(messages)
    else:
        formatted_messages = messages

    # NEW: grading fail होने पर ही web_search की permission दो
    # AFTER
    active_llm = llm
    if state.get("needs_handoff"):
        formatted_messages = list(formatted_messages) + [HANDOFF_HINT]
        active_llm = llm_no_tools
    elif state.get("needs_web_search"):
        formatted_messages = list(formatted_messages) + [WEB_FALLBACK_HINT]
        active_llm = llm_with_web

    print("\n--- [NODE: AGENT] ---")
    print(
        f"-> Conversation History Length: {len(formatted_messages)} message(s) (including System Guardrails)")

    # LLM receives system context + history to decide tool routing
    response = await active_llm.ainvoke(formatted_messages)

    if response.tool_calls:
        print(
            f"-> Agent Decision: CALL TOOL -> {response.tool_calls[0]['name']}")
        print(f"-> Tool Arguments: {response.tool_calls[0]['args']}")
    else:
        print("-> Agent Decision: RESPOND DIRECTLY TO USER (No Tool Needed)")

    return {"messages": [response]}
