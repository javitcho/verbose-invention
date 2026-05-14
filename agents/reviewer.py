import re
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
        return """TASK:
Review a competitive analysis synthesis as a senior analyst would.
Check whether the synthesis is accurate, specific, and defensible.

FLAGS FORMAT:
  [CAPABILITY|EVIDENCE|COMPARISON|VERDICT]: [issue type] — [brief note]
  "none" if no flags

ISSUE TYPES:
- unsupported claim — assertion not traceable to a provided source
- overstated — conclusion goes beyond what evidence supports
- understated — evidence supports a stronger conclusion than stated
- missing competitor — obvious competitor not addressed when sources cover them
- stale source — source older than 18 months used for a rapidly changing claim
- vague — claim lacks specificity that sources could provide

VERDICT LOGIC:
- ACCEPT: no flags, or only minor flags that don't change the verdict
- REVISE: one or more unsupported/overstated/understated flags
- ABANDON: sources are insufficient to make any defensible capability claim

CONSTRAINTS:
- 200 tokens max
- One line per flag
- VERDICT: line must appear exactly as written above

Output format:
FLAGS:
[one line per flag or "none"]

VERDICT: REVISE
(or VERDICT: ACCEPT or VERDICT: ABANDON)
VERDICT REASON: [one sentence]

MEMORY NOTE:
[one bullet]"""

    def _validate_output(self, raw: str) -> tuple:
        # TODO (session-2): validate that the VERDICT line is present and well-formed.
        #
        # The Orchestrator parses your VERDICT line with a string match. One wrong
        # character and the loop defaults. This is the most common failure point in
        # the system. Own it.
        #
        # Check that exactly one of these lines appears (case sensitive, stripped):
        #   "VERDICT: REVISE"
        #   "VERDICT: ACCEPT"
        #   "VERDICT: ABANDON"
        # Return (False, "missing or malformed VERDICT line") if not found.
        #
        if re.search(r'^VERDICT:\s*(REVISE|ACCEPT|ABANDON)\s*$', raw, re.MULTILINE):
            return True, "ok"
        return False, "missing or malformed VERDICT line"

    def _fallback_output(self) -> str:
        # Safe default that keeps the loop running when output validation fails.
        return "none\nVERDICT: REVISE\nVERDICT REASON: output validation failed, defaulting to revision"
