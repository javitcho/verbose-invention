from agents.base import BaseAgent


class Synthesizer(BaseAgent):
    """
    TODO: implement _build_system_prompt().

    Your system prompt should tell the agent:
    1. TASK: what it is synthesizing and for whom
    2. OUTPUT FORMAT: what structure a synthesis should have in your domain
       (e.g., claim → evidence → assessment → verdict; or problem → approaches → tradeoffs)
    3. SCOPE CALIBRATION: how to adjust style for purpose/audience/rigor from SESSION SCOPE
    4. REVISION BEHAVIOR: when REVIEWER FLAGS are present, how to address them
    5. CONSTRAINTS: length expectations, terminology conventions

    See skills/synthesizer/domain.md — your skill file goes there and is appended to this prompt.

    Interface: receives sources + optional prior draft + flags. Outputs SYNTHESIS...END SYNTHESIS block.

    The output MUST follow this format:
        SYNTHESIS
        [full synthesis text]
        END SYNTHESIS

        MEMORY NOTE:
        [one bullet: what you did, what you struggled with]

    See base.py for _build_user_message() — you do not need to override it.
    """

    agent_name = "synthesizer"
    skill_file = "synthesizer/domain.md"

    def _build_system_prompt(self) -> str:
        return """TASK:
Synthesize web sources into a structured competitive analysis for one research angle.
You are producing one section of a competitive intelligence report.

OUTPUT FORMAT — write in this exact order:

1. SYNTHESIS section first (required):
SYNTHESIS
[One paragraph narrative connecting the evidence. Mark contested areas explicitly:
"Sources disagree on X: [source A] reports Y while [source B] reports Z."
End with a one-sentence VERDICT: strong / moderate / weak capability, with reason.]
END SYNTHESIS

2. FINDING blocks after (one per significant claim):
FINDING
claim: [one sentence — what this source asserts]
evidence: [direct quote or close paraphrase — max 2 sentences]
source_url: [URL or document name from the SOURCES block]
publication_date: [date if available in source, otherwise "unknown"]
confidence: established | contested | unclear
END FINDING

When two sources make conflicting claims about the same fact:
- Set confidence: contested on BOTH findings
- Add to each:
  conflicting_claim: [the other source's claim]
  conflicting_source: [the other source's URL]
Do not resolve conflicts. Do not choose a side. Preserve both with attribution.

3. Memory note last:
MEMORY NOTE:
[one bullet: what you did, what you struggled with]

REVISION BEHAVIOR:
When REVIEWER FLAGS are present, rewrite the SYNTHESIS section first, then update the
FINDING blocks. Do not write a preamble before the SYNTHESIS block.
Record what you changed in the MEMORY NOTE.

SCOPE CALIBRATION:
- audience=professional: use industry terminology freely
- audience=general: define acronyms on first use, avoid jargon
- rigor=full: cite specific numbers, dates, version numbers where available
- rigor=sketch: general characterization is sufficient

CONSTRAINTS:
- {max_tokens} tokens max
- Do not make claims not supported by the provided sources
- If sources are insufficient, say so in FINDING evidence and set confidence: unclear"""

    def _validate_output(self, raw: str) -> tuple:
        if "SYNTHESIS" not in raw:
            return False, "missing SYNTHESIS marker"
        if "END SYNTHESIS" not in raw:
            return False, "missing END SYNTHESIS marker"
        return True, "ok"

    def _fallback_output(self) -> str:
        # TODO (session-1): return a safe empty synthesis that won't break downstream parsing.
        # Must contain valid SYNTHESIS...END SYNTHESIS markers so the Reviewer
        # receives parseable input instead of garbage.
        return (
            "SYNTHESIS\n"
            "(synthesis unavailable — output validation failed)\n"
            "END SYNTHESIS\n\n"
            "MEMORY NOTE:\n"
            "- validation failed"
        )
