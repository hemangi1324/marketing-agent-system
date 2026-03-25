"""
tools/search_tool.py
FREE web search using DuckDuckGo. No API key required.
"""
from crewai.tools import BaseTool
from duckduckgo_search import DDGS
from pydantic import Field


class DuckDuckGoSearchTool(BaseTool):
    name: str = "Web Search"
    description: str = (
        "Search the web for current information, news, competitors, "
        "industry trends, and prospect research. Input: a search query string."
    )
    max_results: int = Field(default=4)

    def _run(self, query: str) -> str:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=self.max_results))
            if not results:
                return "No results found for that query."
            lines = []
            for i, r in enumerate(results, 1):
                lines.append(f"[{i}] {r['title']}\nURL: {r['href']}\n{r['body']}\n")
            return "\n".join(lines)
        except Exception as e:
            return f"Search error: {str(e)}. Try a simpler query."
