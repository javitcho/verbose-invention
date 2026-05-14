import json
import logging
from agents.base import BaseAgent
from models.document import ResearchAngle
from models.state import ResearchSession
from models.signals import AngleStatus, StoppingSignal

logger = logging.getLogger(__name__)


class Orchestrator(BaseAgent):
    agent_name = "orchestrator"

    def _build_system_prompt(self) -> str:
        return """TASK:
Read the reviewer output for the current angle and decide the next step.
Then, if signal is DONE, assemble the final research report.

INPUT:
- Main question and all angles with their status
- Current angle: question, synthesis, reviewer flags, verdict, round number
- Session scope

OUTPUT FORMAT (JSON, no markdown fences):
{
  "signal": "revise | accept | abandon | done | budget",
  "signal_reason": "one sentence",
  "directive_for_synthesizer": "specific instruction for next round, or empty if not REVISE",
  "final_report": "assembled report if signal=done, otherwise empty string"
}

DECISION RULES:
- REVISE: reviewer verdict is REVISE and round < max_rounds_per_angle
- ACCEPT: reviewer verdict is ACCEPT
- ABANDON: reviewer verdict is ABANDON, or round >= max_rounds_per_angle with no ACCEPT
- DONE: all angles are ACCEPTED or ABANDONED
- BUDGET: total rounds across all angles >= max_total_rounds

FINAL REPORT (when signal=done):
- One paragraph introduction stating the main question
- One section per accepted angle: angle question as heading, synthesis as body
- One closing paragraph: gaps, limitations, suggested next questions
- Abandoned angles: mention briefly as "not sufficiently addressable with available sources"
- Plain prose, no bullet points, no markdown headers (let the display layer add formatting)

SCOPE CALIBRATION:
- purpose=report: formal, cited, structured
- purpose=briefing: executive summary tone, actionable
- purpose=exploration: conversational, open questions welcomed

CONSTRAINTS:
- 600 tokens max for final_report
- directive_for_synthesizer: 2 sentences max, specific not generic
- "Continue improving" is not a valid directive — say what specifically to fix"""

    def _build_orchestrator_message(self, session: ResearchSession, angle: ResearchAngle, total_rounds: int) -> str:
        angles_summary = ""
        for a in session.angles:
            angles_summary += f"  - {a.id}: {a.status.value} (round {a.round})\n"

        return (
            f"MAIN QUESTION: {session.main_question}\n\n"
            f"ALL ANGLES:\n{angles_summary}\n"
            f"CURRENT ANGLE: {angle.id}\n"
            f"  question: {angle.question}\n"
            f"  round: {angle.round}\n"
            f"  synthesis: {angle.synthesis[:300]}...\n"
            f"  reviewer_flags: {angle.reviewer_flags}\n"
            f"  reviewer_verdict: {angle.reviewer_verdict}\n\n"
            f"MAX_ROUNDS_PER_ANGLE: {self.config.MAX_ROUNDS_PER_ANGLE}\n"
            f"MAX_TOTAL_ROUNDS: {self.config.MAX_TOTAL_ROUNDS}\n"
            f"TOTAL_ROUNDS_SO_FAR: {total_rounds}\n\n"
            f"SCOPE: {session.scope.serialize()}"
        )

    def _parse_decision(self, result: str) -> dict:
        # TODO (session-1): parse the Reviewer's output and produce the orchestrator decision.
        #
        # The Reviewer's _parse_response() returns a JSON string containing:
        #   signal, signal_reason, flags, memory_note
        #
        # Parse this JSON. Then make the session-level decision:
        # - Read signal from the parsed dict
        # - Combine with round count and angle state to determine final action
        # - Produce the orchestrator's own output: directive_for_synthesizer, final_report
        #
        # The Reviewer's signal is advisory — your circuit breaker logic can override it.
        # If JSON parsing fails (it should not), default signal to "revise" and log a WARNING.
        #
        # You must return a dict with these four keys:
        #    - "signal": "revise" | "accept" | "abandon" | "done" | "budget"
        #    - "signal_reason": str
        #    - "directive_for_synthesizer": str (2 sentences max, specific)
        #    - "final_report": str (populated only when signal == "done")
        #
        # FALLBACK BEHAVIOR when parsing fails:
        #    - raise ValueError (the caller logs a WARNING and returns the REVISE fallback)
        #    - NEVER silently swallow errors here — surface them to the caller
        #
        cleaned = result.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [ln for ln in lines if not ln.startswith("```")]
            cleaned = "\n".join(lines)
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(cleaned[start:end])
            return {
                "signal": data.get("signal", "revise"),
                "signal_reason": data.get("signal_reason", ""),
                "directive_for_synthesizer": data.get("directive_for_synthesizer", ""),
                "final_report": data.get("final_report", ""),
            }
        raise ValueError(f"no JSON object found in orchestrator output: {result[:100]}")

    def decide(self, session: ResearchSession, angle: ResearchAngle, total_rounds: int) -> dict:
        messages = [{"role": "user", "content": self._build_orchestrator_message(session, angle, total_rounds)}]
        response = self.call_api(messages, self.config.MAX_TOKENS_ORCHESTRATOR)
        result = self._parse_response(response)
        try:
            return self._parse_decision(result)
        except Exception as e:
            logger.warning(f"orchestrator: parser failed ({e}), defaulting to REVISE")
            return {
                "signal": "revise",
                "signal_reason": "parsing failed, defaulting to revise",
                "directive_for_synthesizer": result,
                "final_report": "",
            }

    def assemble_report(self, session: ResearchSession) -> str:
        """Assemble final report from accepted angle syntheses."""
        try:
            accepted = [a for a in session.angles if a.status == AngleStatus.ACCEPTED]
            abandoned = [a for a in session.angles if a.status == AngleStatus.ABANDONED]

            parts = [f"Report on: {session.main_question}\n\n"]
            for angle in accepted:
                parts.append(f"## {angle.question}\n\n{angle.synthesis}\n\n")
            if abandoned:
                abandoned_list = "; ".join(a.question for a in abandoned)
                parts.append(f"The following angles were not sufficiently addressable with available sources: {abandoned_list}.\n")

            return "".join(parts)
        except Exception as e:
            return f"Report assembly failed: {e}"
