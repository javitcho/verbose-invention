import json
from agents.base import BaseAgent
from models.document import ResearchAngle, Source
from models.state import ResearchSession
from models.signals import AngleStatus

SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
}

class Searcher(BaseAgent):
    agent_name = "searcher"

    def _build_system_prompt(self) -> str:
        return """TASK:
Search the web for sources relevant to the research angle you receive.
Run 2-3 searches with different query formulations. From all results, select the
3-5 most relevant sources.

OUTPUT FORMAT (JSON, no markdown fences):
{
  "sources": [
    {
      "url": "...",
      "title": "...",
      "snippet": "2-4 sentence extract capturing the most relevant content",
      "relevance": "one sentence: why this source addresses the angle"
    }
  ]
}

SEARCH STRATEGY:
1. First search: the angle question almost verbatim
2. Second search: rephrase to target a different type of source (e.g., add "review" or
   "comparison" or "critique" or the main question's domain)
3. Third search (if first two insufficient): search for the opposing or critical view

CONSTRAINTS:
- {max_tokens} tokens max output
- Prefer recent sources (last 3 years) unless older sources are foundational
- If search returns no useful results, output sources: [] and note why"""

    def _build_user_message_for_search(self, session: ResearchSession, angle: ResearchAngle) -> str:
        return (
            f"RESEARCH ANGLE: {angle.question}\n"
            f"MAIN QUESTION: {session.main_question}\n"
            f"SCOPE: {session.scope.serialize()}\n\n"
            "Search for sources relevant to this angle, then return them in the specified JSON format."
        )

    def search(self, session: ResearchSession, angle: ResearchAngle) -> list:
        source = getattr(self.config, "SEARCH_SOURCE", "web")
        if source == "arxiv":
            return self._search_via_mcp(session, angle)
        return self._search_web(session, angle)

    def _search_web(self, session: ResearchSession, angle: ResearchAngle) -> list:
        try:
            angle.status = AngleStatus.SEARCHING
            messages = [{"role": "user", "content": self._build_user_message_for_search(session, angle)}]
            response = self.call_api(messages, self.config.MAX_TOKENS_SEARCHER, tools=[SEARCH_TOOL], betas=["web-search-2025-03-05"])
            self.last_tokens_used = getattr(response.usage, "output_tokens", 0) + getattr(response.usage, "input_tokens", 0)
            result = self._parse_response(response)
            # extract JSON from result
            cleaned = result.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                cleaned = "\n".join(lines)
            # find JSON object in result
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(cleaned[start:end])
                sources = []
                for s in data.get("sources", []):
                    sources.append(Source(
                        url=s.get("url", ""),
                        title=s.get("title", ""),
                        snippet=s.get("snippet", ""),
                        relevance=s.get("relevance", ""),
                    ))
                return sources
            return []
        except Exception:
            return []

    def _search_via_mcp(self, session: ResearchSession, angle: ResearchAngle) -> list:
        """
        Search ArXiv via MCP server using the search_papers tool.

        The ArXiv MCP server exposes a tool with this schema:
          name: "search_papers"
          input_schema:
            query: str       — search terms
            max_results: int — papers to return (default 5)

        Each result has: paper_id, title, authors, abstract, published, url.

        To call it, pass it as a tool and force tool_choice just like REVIEWER_TOOL.
        Store downloaded PDFs in config.ARXIV_STORAGE_PATH.

        The MCP server runs as a separate process — it is NOT a Python import.
        Connection details are provided at runtime via the MCP client configured
        in the calling environment. If the server is unavailable, return [] and
        log a WARNING.

        Returns a list of Source objects mapped from paper metadata:
          url   → paper URL or arxiv.org/abs/{paper_id}
          title → paper title
          snippet → abstract (truncated to 300 chars)
          relevance → "arxiv paper: {title}"
        """
        # TODO: implement ArXiv MCP search
        raise NotImplementedError
