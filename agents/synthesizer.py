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

OUTPUT FORMAT:
For each angle, produce exactly:
  CAPABILITY: [one sentence stating what the technology/product can or cannot do]
  EVIDENCE: [2-3 sentences citing specific sources — reference by title or URL]
  COMPARISON: [how competitors handle this — if sources don't cover it, say so explicitly]
  VERDICT: [one sentence: strong / moderate / weak capability, with reason]

REVISION BEHAVIOR:
When REVIEWER FLAGS are present, address each flag explicitly before rewriting.
State "Addressing [flag type]:" before each revision.

SCOPE CALIBRATION:
- audience=professional: use industry terminology freely
- audience=general: define acronyms on first use, avoid jargon
- rigor=full: cite specific numbers, dates, version numbers where available
- rigor=sketch: general characterization is sufficient

CONSTRAINTS:
- 400 tokens max per synthesis
- Do not make claims not supported by the provided sources
- If sources are insufficient, say so in EVIDENCE and issue a weak VERDICT

After the synthesis, include:
SYNTHESIS
[your CAPABILITY/EVIDENCE/COMPARISON/VERDICT output]
END SYNTHESIS

MEMORY NOTE:
[one bullet: what you did, what you struggled with]"""
