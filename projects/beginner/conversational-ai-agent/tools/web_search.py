"""Web Search tool — uses OpenAI's built-in web search via function calling."""

from typing import Annotated

from langchain_core.tools import tool


@tool
async def web_search(
    query: Annotated[str, "The search query to look up on the web"],
) -> str:
    """Search the web for current information using OpenAI's built-in web search.

    Use this when you need up-to-date facts, news, or information that may not be
    in your training data. The search is performed by OpenAI's model with web
    browsing capabilities.

    Note: This tool delegates to the LLM's native web search capability.
    The actual search is handled by OpenAI when the model has web search enabled.
    """
    # This is a placeholder — the actual web search is performed by OpenAI's
    # model when bound with web_search_preview tool. The LangGraph agent node
    # binds this via ChatOpenAI's native tool support.
    # If the model doesn't support native web search, return a helpful message.
    return (
        f"Web search for: '{query}'\n"
        "Note: Web search is handled natively by the OpenAI model. "
        "If you're seeing this message, the model's built-in web search "
        "was not available for this request."
    )
