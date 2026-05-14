import json
from agents.base import BaseAgent
from models.document import ResearchAngle
from models.state import ResearchSession
from models.signals import AngleStatus, StoppingSignal

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

    def decide(self, session: ResearchSession, angle: ResearchAngle, total_rounds: int) -> dict:
        try:
            messages = [{"role": "user", "content": self._build_orchestrator_message(session, angle, total_rounds)}]
            result = self.call_api(messages, self.config.MAX_TOKENS_ORCHESTRATOR)
            cleaned = result.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                cleaned = "\n".join(lines)
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(cleaned[start:end])
        except Exception as e:
            pass
        # fallback: REVISE
        return {
            "signal": "revise",
            "signal_reason": "orchestrator parsing failed, defaulting to revise",
            "directive_for_synthesizer": "Please revise the synthesis addressing any reviewer flags.",
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
