"""
Web Research Agent
Uses Gemini with Google Search grounding to collect up-to-date findings and their source URLs.
"""
from typing import List

from core.citation_tracker import CitationTracker
from core.gemini_client import GeminiError, ask_gemini
from core.models import WebSearchResult

MAX_SOURCES = 5


class WebResearchAgent:
    def __init__(self):
        self.name = "Web Research Agent"
        self.unavailable_reason = ""

    def research(self, topic: str, citation_tracker: CitationTracker) -> List[WebSearchResult]:
        self.unavailable_reason = ""
        try:
            summary, sources = ask_gemini(
                # Gemini decides on its own whether to search; mentions of "my uploaded files"
                # make it skip searching, so tell it explicitly to search and ignore those
                "Use Google Search to find current, reputable sources about the topic of the request below. "
                "Ignore any mention of uploaded files (they are handled separately). "
                f"Summarise the key facts, figures and trends in 8-12 bullet points.\n\nREQUEST: {topic}",
                use_web_search=True,
            )
        except GeminiError as e:
            # Search grounding has its own quota (free keys often have none). Generation can still
            # run from the knowledge base, so report it instead of failing the whole request.
            self.unavailable_reason = str(e)
            return []

        results = []
        for source in sources[:MAX_SOURCES]:
            citation_id = citation_tracker.add_citation(
                source_type="web",
                title=source["title"],
                reference=source["url"],
                snippet=summary[:240],
            )
            results.append(WebSearchResult(id=citation_id, title=source["title"], url=source["url"], summary=summary))

        # Grounding can return no sources; the summary is still useful for the writer
        if not results:
            results.append(WebSearchResult(id="", title="Web research summary", url="", summary=summary))
        return results
