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

    def _validate_output(self, raw: str) -> tuple:
        # TODO: validate that raw contains SYNTHESIS and END SYNTHESIS markers.
        #
        # The Reviewer receives whatever you return here. If you return garbage,
        # the Reviewer breaks, the Orchestrator breaks, and the loop dies silently.
        # Validate your own output before handing off.
        #
        # Check:
        # 1. "SYNTHESIS" appears in raw
        # 2. "END SYNTHESIS" appears in raw
        # 3. "MEMORY NOTE:" appears in raw
        # Return (False, "missing SYNTHESIS block") if any marker is absent.
        #
        return True, "ok"  # stub: always valid — replace with real checks

    def _fallback_output(self) -> str:
        # TODO: return a safe empty synthesis that won't break downstream parsing.
        # Must contain valid SYNTHESIS...END SYNTHESIS markers so the Reviewer
        # receives parseable input instead of garbage.
        return "error — output validation failed"  # stub: replace with marked-up fallback
