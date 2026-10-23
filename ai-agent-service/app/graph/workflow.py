from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import tools_condition
from app.graph.state import AgentState
from app.graph.nodes import (
    agent_node, tool_node, grade_documents_node,
    rewrite_query_node, route_after_grading,
)


def create_agent_workflow():
    workflow = StateGraph(AgentState)
    workflow.add_node("rewrite_query", rewrite_query_node)   # NEW
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("grade_documents", grade_documents_node)

    workflow.add_edge(START, "agent")

    workflow.add_conditional_edges(
        "agent",
        tools_condition,
        {
            "tools": "tools",
            END: END
        }
    )

    workflow.add_edge("tools", "grade_documents")

    workflow.add_conditional_edges(
        "grade_documents",
        route_after_grading,
        {"agent": "agent", "rewrite_query": "rewrite_query"},
    )

    workflow.add_edge("rewrite_query", "agent")

    return workflow.compile()


agent_graph = create_agent_workflow()
