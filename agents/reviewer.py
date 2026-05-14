from agents.base import BaseAgent


class Reviewer(BaseAgent):
    """
    TODO: implement _build_system_prompt().

    Your system prompt should tell the agent:
    1. TASK: what it is reviewing and from what perspective
    2. REVIEW CRITERIA: what quality dimensions to check (from your skill file)
       These should reflect how peer review or expert evaluation works in your domain.
       Examples: are claims supported by sources? are counterarguments addressed?
       is the synthesis clear and actionable? are important perspectives missing?
    3. FLAG FORMAT: [location or claim] → [issue type] → [brief note]
    4. VERDICT LOGIC: when to issue REVISE vs ACCEPT vs ABANDON
    5. CONSTRAINTS: 200 tokens max output; terse flags only

    See skills/reviewer/criteria.md — your review criteria go there.

    The output MUST follow this format EXACTLY (the loop parses these lines):
        FLAGS:
        [one line per issue, or "none"]

        VERDICT: REVISE
        (or VERDICT: ACCEPT or VERDICT: ABANDON — case sensitive, no extra text on this line)
        VERDICT REASON: [one sentence]

        MEMORY NOTE:
        [one bullet]

    Interface: receives synthesis + sources. Outputs FLAGS: block + VERDICT: line.
    """

    agent_name = "reviewer"
    skill_file = "reviewer/criteria.md"

    def _build_user_message(self, session, angle, round_num=0):
        sources_text = ""
        for i, src in enumerate(angle.sources, 1):
            sources_text += f"\n[Source {i}]\nTitle: {src.title}\nURL: {src.url}\nSnippet: {src.snippet}\nRelevance: {src.relevance}\n"

        memory_text = session.memory.format_for_agent(self.agent_name)

        return (
            f"RESEARCH ANGLE: {angle.question}\n\n"
            f"SYNTHESIS DRAFT:\n{angle.synthesis}\n\n"
            f"SOURCES AVAILABLE (for reference):\n{sources_text or 'none'}\n\n"
            f"SCOPE: {session.scope.serialize()}\n"
            f"YOUR MEMORY:\n{memory_text}"
        )

    def _build_system_prompt(self) -> str:
        # TODO: return your system prompt string
        raise NotImplementedError
