import json
from agents.base import BaseAgent
from models.document import ResearchAngle
from models.state import ResearchSession
from models.signals import AngleStatus

class Planner(BaseAgent):
    agent_name = "planner"

    def _build_system_prompt(self) -> str:
        return """TASK:
Break the research question into 2-4 focused search angles. Each angle should be:
- A specific sub-question, not a restatement of the main question
- Searchable: a real web search for this angle should return relevant sources
- Independent: answering one angle doesn't require answering another first

OUTPUT FORMAT (JSON, no markdown fences):
{
  "angles": [
    {
      "id": "angle_slug",
      "question": "specific sub-question"
    }
  ]
}

SCOPE CALIBRATION:
- rigor=full: 4 angles, each narrow and specific
- rigor=sketch: 2 angles, each broader
- rigor=summary: 2 angles maximum

CONSTRAINTS:
- {max_tokens} tokens max output
- No more than 4 angles regardless of rigor
- Each angle question must be under 15 words"""

    def plan(self, session: ResearchSession) -> list:
        try:
            messages = [{"role": "user", "content": (
                f"RESEARCH QUESTION: {session.main_question}\n"
                f"SCOPE: {session.scope.serialize()}"
            )}]
            response = self.call_api(messages, self.config.MAX_TOKENS_PLANNER)
            result = self._parse_response(response)
            # strip markdown fences
            cleaned = result.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                cleaned = "\n".join(lines)
            data = json.loads(cleaned)
            angles = []
            for a in data.get("angles", []):
                angles.append(ResearchAngle(
                    id=a["id"],
                    question=a["question"],
                    status=AngleStatus.PENDING,
                ))
            return angles[:self.config.MAX_ANGLES]
        except Exception as e:
            # fallback: one generic angle
            return [ResearchAngle(
                id="angle_main",
                question=session.main_question,
                status=AngleStatus.PENDING,
            )]
