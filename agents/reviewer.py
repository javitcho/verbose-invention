import json
from agents.base import BaseAgent

REVIEWER_TOOL = {
    "name": "submit_review",
    "description": "Submit a structured review of the synthesis",
    "input_schema": {
        "type": "object",
        "properties": {
            "flags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Issues found, one string per issue. Empty list if none."
            },
            "signal": {
                "type": "string",
                "enum": ["revise", "accept", "abandon"],
                "description": "revise: request changes. accept: quality met. abandon: sources insufficient."
            },
            "signal_reason": {
                "type": "string",
                "description": "One sentence explaining the verdict."
            },
            "memory_note": {
                "type": "string",
                "description": "One bullet summarizing this round."
            }
        },
        "required": ["flags", "signal", "signal_reason", "memory_note"]
    }
}


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
    4. VERDICT LOGIC: when to issue revise vs accept vs abandon
    5. CONSTRAINTS: 200 tokens max output; terse flags only

    See skills/reviewer/criteria.md — your review criteria go there.

    You do NOT need to specify output format — the tool schema enforces it.
    The model will call submit_review() with: flags (list), signal (enum),
    signal_reason (str), memory_note (str). No text parsing required.

    Interface: receives synthesis + sources. Calls submit_review() tool.
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
  empty list if no flags

ISSUE TYPES:
- unsupported claim — assertion not traceable to a provided source
- overstated — conclusion goes beyond what evidence supports
- understated — evidence supports a stronger conclusion than stated
- missing competitor — obvious competitor not addressed when sources cover them
- stale source — source older than 18 months used for a rapidly changing claim
- vague — claim lacks specificity that sources could provide

VERDICT LOGIC:
- accept: no flags, or only minor flags that don't change the verdict
- revise: one or more unsupported/overstated/understated flags
- abandon: sources are insufficient to make any defensible capability claim

CONSTRAINTS:
- 200 tokens max
- One string per flag
- Call submit_review() with your assessment"""

    def _parse_response(self, response) -> str:
        """
        TODO: extract the tool_use block from the API response and return
        its input as a JSON string.

        The API guarantees a tool_use block when tool_choice is forced.
        Handle the case where it is missing anyway — return a safe default
        JSON string that the loop can parse without crashing:
          {"signal": "revise", "signal_reason": "parse fallback",
           "flags": [], "memory_note": "parsing failed"}

        Log a WARNING if the fallback fires. It should not happen with
        tool_choice forced, but defensive handling is required.

        Return: json.dumps(tool_block.input) on success, safe default string on failure.

        Note: _validate_output() is NOT needed for this agent — the schema
        enforces required fields and the signal enum. The tool contract is
        the validator. Remove any VERDICT string check you may have written.
        """
        raise NotImplementedError

    # _validate_output() is not needed here.
    # The tool schema enforces required fields and the signal enum.
    # See _parse_response() above — the schema is the contract.

    def call(self, session, angle, round_num=0) -> str:
        try:
            user_msg = self._build_user_message(session, angle, round_num)
            messages = [{"role": "user", "content": user_msg}]
            response = self.call_api(
                messages,
                self.config.MAX_TOKENS_REVIEWER,
                tools=[REVIEWER_TOOL],
                tool_choice={"type": "tool", "name": "submit_review"},
            )
            raw = self._parse_response(response)
            try:
                from output.trace import log_handoff
                log_handoff(
                    session_id=session.session_id,
                    angle_id=angle.id,
                    round=round_num,
                    from_agent=self.agent_name,
                    to_agent="unknown",
                    signal=None,
                    output=raw,
                    output_valid=True,
                )
            except Exception:
                pass
            try:
                data = json.loads(raw)
                note = data.get("memory_note", "")
                if note:
                    session.memory.add(self.agent_name, angle.id, round_num, note)
            except Exception:
                pass
            return raw
        except Exception as e:
            return f"error — skipped: {e}"
