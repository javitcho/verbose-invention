import logging
from agents.base import BaseAgent
from models.document import ReportInput, Confidence

logger = logging.getLogger(__name__)


class ReportWriter(BaseAgent):
    """
    Writes the final research brief from all accepted angle syntheses.

    Runs once after the Orchestrator signals DONE.
    Not part of the revision loop — no REVISE/ACCEPT cycle.
    Single API call. Single output.

    Input:  ReportInput (main question, scope, all angles, errors)
    Output: research brief as a plain string
    """

    agent_name = "report_writer"
    skill_file = "report_writer/brief_format.md"

    def write(self, report_input: ReportInput) -> str:
        """Primary interface. Called by the loop after DONE signal."""
        try:
            messages = [{"role": "user", "content": self._build_report_message(report_input)}]
            response = self.call_api(messages, self.config.MAX_TOKENS_REPORT_WRITER)
            self.last_tokens_used = (
                getattr(response.usage, "output_tokens", 0)
                + getattr(response.usage, "input_tokens", 0)
            )
            return self._parse_response(response)
        except Exception as e:
            logger.warning(f"report_writer failed: {e}")
            return f"Report assembly failed: {e}"

    def _build_system_prompt(self) -> str:
        return """TASK:
Write a research brief from the provided angle syntheses.
You are an analyst writing for a specific audience and purpose.

USE THE SYNTHESIS PROSE DIRECTLY.
Do not re-extract bullets. Do not re-summarize.
The Synthesizer wrote the paragraphs — weave them, do not flatten them.

OUTPUT STRUCTURE — write in this exact order:

EXECUTIVE SUMMARY
[3-4 sentences: what the question is; the single most important finding;
the key area of disagreement or uncertainty; the recommendation in one clause.]

[Thematic section — descriptive title you generate]
[Prose paragraphs from the angle synthesis. Inline citations: (Source: url).
One section per accepted angle. Title is descriptive, not the angle question.]

AREAS OF DISAGREEMENT
[Only if contested findings exist. Declarative prose only.
"Sources disagree on X: [Source A] reports Y while [Source B] reports Z."
Do not resolve. Do not choose. Preserve both with attribution.
Omit this section entirely if no genuine conflicts exist.]

RECOMMENDATION
[Always present. Concrete. Actionable. Calibrated to scope.
Not hedged into uselessness. See skill file for examples.]

COVERAGE GAPS
[Only if abandoned angles or errors exist. One sentence per gap.
Omit this section entirely if all angles were accepted cleanly.]

REFERENCES
[Numbered list. One per line. Title and URL.]

SECTION TITLE RULES:
- Descriptive titles only: "The Cost-Performance Tradeoff at Scale"
  NOT "What are the scalability, cost, and latency tradeoffs?"
- Never use the angle question verbatim as a section title

SCOPE CALIBRATION:
- purpose=report: formal prose, third-person
- purpose=briefing: direct, action-oriented, second-person where natural
- purpose=exploration: conversational, open questions welcomed
- audience=research: assume domain expertise, no definitions needed
- audience=professional: practical implications first, theory second
- audience=general: define acronyms on first use
- rigor=full: cite every specific number or statistic inline
- rigor=sketch: cite only the most critical claims
- tone_notes: follow literally

CONSTRAINTS:
- {max_tokens} tokens max
- Never invent claims not present in the provided syntheses
- Executive summary and recommendation are never cut
- Do not use bullet points in thematic sections — prose only
- Do not write "In conclusion" or "To summarize" — use section headings"""

    def _build_report_message(self, report_input: ReportInput) -> str:
        parts = [
            f"QUESTION: {report_input.main_question}\n",
            f"SCOPE:\n{report_input.scope.serialize()}\n",
        ]

        parts.append("\nACCEPTED ANGLES:")
        for angle in report_input.accepted_angles:
            synthesis = angle.synthesis
            if len(synthesis) > 600:
                synthesis = synthesis[:600] + "[truncated]"
            parts.append(f"\nANGLE: {angle.question}")
            parts.append(f"SYNTHESIS:\n{synthesis}")

            contested = [f for f in angle.findings if f.confidence == Confidence.CONTESTED]
            if contested:
                parts.append("CONTESTED FINDINGS:")
                for f in contested:
                    parts.append(
                        f"  - {f.source_url} reports: {f.claim}. "
                        f"{f.conflicting_source} reports: {f.conflicting_claim}."
                    )

            if angle.sources:
                parts.append("SOURCES:")
                for src in angle.sources:
                    parts.append(f"  {src.title}. {src.url}")

        if report_input.abandoned_angles:
            parts.append("\nABANDONED ANGLES:")
            for angle in report_input.abandoned_angles:
                reason = angle.reviewer_verdict_reason or "insufficient sources or synthesis failures"
                parts.append(f"  - {angle.question} (reason: {reason})")

        non_recoverable = [
            e for e in report_input.session_errors
            if e.failure_type != "validation_failed"
        ]
        if non_recoverable:
            parts.append("\nERRORS:")
            for err in non_recoverable:
                parts.append(err.to_context_string())

        return "\n".join(parts)
