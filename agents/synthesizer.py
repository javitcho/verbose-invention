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
        # TODO: return your system prompt string
        raise NotImplementedError
