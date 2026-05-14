import os
import json
import anthropic
from pathlib import Path
from typing import Optional
from models.document import ResearchAngle, Source
from models.state import ResearchSession, SessionScope

class BaseAgent:
    agent_name: str = "base"
    skill_file: Optional[str] = None  # relative path under skills/, e.g. "synthesizer/domain.md"

    def __init__(self, config):
        self.config = config
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    def _load_skill(self) -> str:
        if not self.skill_file:
            return ""
        path = Path(__file__).parent.parent / "skills" / self.skill_file
        if path.exists():
            content = path.read_text().strip()
            if content and not content.startswith("<!--"):
                return f"\n\n## SKILL FILE\n{content}"
        return ""

    def _build_system_prompt(self) -> str:
        raise NotImplementedError

    def _build_user_message(self, session: ResearchSession, angle: ResearchAngle, round_num: int = 0) -> str:
        sources_text = ""
        for i, src in enumerate(angle.sources, 1):
            sources_text += f"\n[Source {i}]\nTitle: {src.title}\nURL: {src.url}\nSnippet: {src.snippet}\nRelevance: {src.relevance}\n"

        prior_synthesis = angle.synthesis if angle.synthesis else "none"
        flags_text = "\n".join(angle.reviewer_flags) if angle.reviewer_flags else "none"
        memory_text = session.memory.format_for_agent(self.agent_name)

        return (
            f"RESEARCH ANGLE: {angle.question}\n"
            f"MAIN QUESTION: {session.main_question}\n\n"
            f"SOURCES:\n{sources_text or 'none'}\n\n"
            f"PREVIOUS SYNTHESIS (if revising):\n{prior_synthesis}\n\n"
            f"REVIEWER FLAGS (if revising):\n{flags_text}\n\n"
            f"DIRECTIVE FROM ORCHESTRATOR:\n{angle.directive or 'none'}\n\n"
            f"SCOPE: {session.scope.serialize()}\n"
            f"YOUR MEMORY:\n{memory_text}"
        )

    def _extract_memory_note(self, response_text: str) -> Optional[str]:
        if "MEMORY NOTE:" in response_text:
            idx = response_text.index("MEMORY NOTE:")
            note = response_text[idx + len("MEMORY NOTE:"):].strip()
            return note.split("\n")[0].strip()
        return None

    def call_api(self, messages: list, max_tokens: int, tools: Optional[list] = None) -> str:
        kwargs = {
            "model": self.config.MODEL,
            "max_tokens": max_tokens,
            "system": self._build_system_prompt() + self._load_skill(),
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        response = self.client.messages.create(**kwargs)
        # handle tool_use content blocks vs text blocks
        text_parts = []
        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "\n".join(text_parts)

    def call(self, session: ResearchSession, angle: ResearchAngle, round_num: int = 0) -> str:
        try:
            user_msg = self._build_user_message(session, angle, round_num)
            messages = [{"role": "user", "content": user_msg}]
            max_tokens = getattr(self.config, f"MAX_TOKENS_{self.agent_name.upper()}", 600)
            result = self.call_api(messages, max_tokens)
            note = self._extract_memory_note(result)
            if note:
                session.memory.add(self.agent_name, angle.id, round_num, note)
            return result
        except Exception as e:
            return f"error — skipped: {e}"
