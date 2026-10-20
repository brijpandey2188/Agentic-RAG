from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool
from app.core.config import settings

@tool
async def web_search(query: str) -> str:
    """Performs an external web search using Tavily asynchronously.
    Use this as a fallback if internal policies or database queries do not contain the answer.
    """
    if not settings.TAVILY_API_KEY or settings.TAVILY_API_KEY.endswith("..."):
        return "Web search unavailable: TAVILY_API_KEY is not configured in .env."

    try:
        tavily = TavilySearchResults(tavily_api_key=settings.TAVILY_API_KEY, max_results=2)
        results = await tavily.ainvoke({"query": query})
        return str(results)
    except Exception as e:
        return f"Web search execution error: {str(e)}"