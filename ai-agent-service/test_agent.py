import asyncio
import sys
from app.graph.workflow import agent_graph

QUESTIONS = [
    "Hi",
    "What is your return policy?",
    "What is the status of order ORD-1001?",
    "Do you accept gift cards?",
]


async def run(question: str):
    print("\n" + "=" * 70)
    print("USER:", question)
    result = await agent_graph.ainvoke({
        "messages": [("user", question)],
        "user_id": None,
        "needs_web_search": False,
        "needs_handoff": False,
        "retry_count": 0,
        "grade": "",
    })
    print("\nFINAL ANSWER:", result["messages"][-1].content)


async def main():
    # python test_agent.py "my question"  -> only taht question will run
    questions = [" ".join(sys.argv[1:])] if len(sys.argv) > 1 else QUESTIONS
    for q in questions:
        await run(q)


asyncio.run(main())
