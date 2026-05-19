import json
import logging
from agents.base import BaseAgent

logger = logging.getLogger(__name__)

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

        findings_text = ""
        for i, f in enumerate(angle.findings, 1):
            findings_text += f"\nFINDING\nclaim: {f.claim}\nevidence: {f.evidence}\nsource_url: {f.source_url}\npublication_date: {f.publication_date}\nconfidence: {f.confidence.value}\n"
            if f.conflicting_claim:
                findings_text += f"conflicting_claim: {f.conflicting_claim}\nconflicting_source: {f.conflicting_source}\n"
            findings_text += "END FINDING\n"

        memory_text = session.memory.format_for_agent(self.agent_name)

        msg = (
            f"RESEARCH ANGLE: {angle.question}\n\n"
            f"SYNTHESIS DRAFT:\n{angle.synthesis}\n\n"
        )
        if findings_text:
            msg += f"STRUCTURED FINDINGS:\n{findings_text}\n"
        msg += (
            f"SOURCES AVAILABLE (for reference):\n{sources_text or 'none'}\n\n"
            f"SCOPE: {session.scope.serialize()}\n"
            f"YOUR MEMORY:\n{memory_text}"
        )
        return msg

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
- unsourced claim — FINDING block has no source_url from the SOURCES block
- overstated confidence — FINDING marked "established" with only one source
- missing conflict pair — confidence=contested but conflicting_claim/conflicting_source absent on one side
- evidence mismatch — FINDING evidence introduces information not present in the cited source

PROVENANCE REVIEW (check every FINDING block):
- Every claim must have a source_url from the SOURCES block. Flag unsourced claims.
- evidence: must quote or closely paraphrase the source. Flag if it introduces
  information not in the cited source.
- confidence: must match evidence weight. Flag "established" with only one source.
- conflicting_claim/conflicting_source: must appear on BOTH findings when
  confidence=contested. Flag if one side of a conflict is dropped.
- Do NOT flag contested findings as errors — they are correct. Flag only hidden conflicts.

VERDICT LOGIC (strictly followed — signal must match flags):
- If flags is empty → signal MUST be "accept". No exceptions.
- If flags contains unsupported/overstated/understated/vague issues → signal is "revise"
- If sources are entirely absent or insufficient for any defensible claim → signal is "abandon"
- "revise" with an empty flags list is a contradiction and is not allowed.

CONSTRAINTS:
- {max_tokens} tokens max
- One string per flag
- Call submit_review() with your assessment"""

    def _parse_response(self, response) -> str:
        _FALLBACK = json.dumps({
            "signal": "revise",
            "signal_reason": "parse fallback",
            "flags": [],
            "memory_note": "parsing failed",
        })
        try:
            for block in response.content:
                if block.type == "tool_use":
                    return json.dumps(block.input)
            logger.warning("reviewer: no tool_use block in response — using fallback")
            return _FALLBACK
        except Exception as exc:
            logger.warning(f"reviewer: failed to parse response — {exc}")
            return _FALLBACK

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
            from models.signals import AgentError
            self.last_error = AgentError(
                failure_type="api_error",
                agent_id=self.agent_name,
                angle_id="unknown",
                attempted_query="reviewer call",
                partial_results="",
                error_message=str(e),
                round=round_num,
            )
            logger.warning(f"reviewer failed: {e}")
            return json.dumps({"signal": "revise", "signal_reason": f"reviewer error: {e}", "flags": [], "memory_note": "error"})
