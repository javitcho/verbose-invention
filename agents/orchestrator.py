import json
import logging
from agents.base import BaseAgent
from models.document import ResearchAngle
from models.state import ResearchSession
from models.signals import StoppingSignal

logger = logging.getLogger(__name__)


class Orchestrator(BaseAgent):
    agent_name = "orchestrator"

    def _build_system_prompt(self) -> str:
        return """TASK:
Read the reviewer output for the current angle and decide the next step.

INPUT:
- Main question and all angles with their status
- Current angle: question, synthesis, reviewer flags, verdict, round number
- Session scope

OUTPUT FORMAT (JSON, no markdown fences):
{
  "signal": "revise | accept | abandon | done | budget",
  "signal_reason": "one sentence",
  "directive_for_synthesizer": "specific instruction for next round, or empty string if not revise"
}

DECISION RULES:
- accept: reviewer verdict is ACCEPT for the current angle
- done: ALL angles in the session are now ACCEPTED or ABANDONED (check ALL ANGLES list)
- revise: reviewer verdict is REVISE and rounds remain
- abandon: reviewer verdict is ABANDON, or no rounds remain
- budget: total_rounds >= max_total_rounds

When signal=done: the Report Writer agent handles the brief. Your job ends here.

SCOPE CALIBRATION:
- purpose=report: formal tone
- purpose=briefing: executive summary tone
- purpose=exploration: conversational

WHEN AGENT FAILURES ARE PRESENT:
- AGENT ERROR blocks mean that agent produced no valid output this round.
- Issue REVISE if other agents still produced useful output.
- Issue ABANDON if failures mean the angle cannot be answered at all.
- In directive_for_synthesizer, note what data is missing.

CONSTRAINTS:
- {max_tokens} tokens max
- directive_for_synthesizer: 2 sentences max, specific not generic
- "Continue improving" is not a valid directive — say what specifically to fix"""

    def _build_orchestrator_message(self, session: ResearchSession, angle: ResearchAngle,
                                    total_rounds: int, round_errors=None) -> str:
        angles_summary = ""
        for a in session.angles:
            angles_summary += f"  - {a.id}: {a.status.value} (round {a.round})\n"

        msg = (
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

        if round_errors:
            msg += "\n\nAGENT FAILURES THIS ROUND:\n"
            for err in round_errors:
                msg += err.to_context_string() + "\n"
            msg += (
                "\nNote: the loop will continue with partial results. "
                "Your directive should acknowledge what data is missing "
                "and whether the angle is still worth pursuing."
            )

        return msg

    def _parse_decision(self, result: str) -> dict:
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
            }
        raise ValueError(f"no JSON object found in orchestrator output: {result[:100]}")

    def decide(self, session: ResearchSession, angle: ResearchAngle, total_rounds: int,
               round_errors=None) -> dict:
        messages = [{"role": "user", "content": self._build_orchestrator_message(session, angle, total_rounds, round_errors=round_errors)}]
        response = self.call_api(messages, self.config.MAX_TOKENS_ORCHESTRATOR)
        result = self._parse_response(response)
        try:
            return self._parse_decision(result)
        except Exception as e:
            logger.warning(f"orchestrator: parser failed ({e}), defaulting to REVISE")
            return {
                "signal": "revise",
                "signal_reason": "parsing failed, defaulting to revise",
                "directive_for_synthesizer": "",
            }

