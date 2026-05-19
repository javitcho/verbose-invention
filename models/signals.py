from enum import Enum
from dataclasses import dataclass


class AgentBudgetExceeded(Exception):
    """Raised when a single agent call exceeds its per-call token budget."""
    pass


class AngleStatus(Enum):
    PENDING      = "pending"
    SEARCHING    = "searching"
    SYNTHESIZING = "synthesizing"
    REVIEWING    = "reviewing"
    ACCEPTED     = "accepted"
    ABANDONED    = "abandoned"

class SessionMode(Enum):
    SCOUT = "scout"
    DEEP  = "deep"

class StoppingSignal(Enum):
    CONTINUE   = "continue"
    REVISE     = "revise"
    ACCEPT     = "accept"
    DONE       = "done"
    BUDGET     = "budget"
    USER_STOP  = "user_stop"
    SCOUT_DONE = "scout_done"


@dataclass
class AgentError:
    failure_type:     str   # "timeout" | "budget_exceeded" | "validation_failed" | "api_error" | "parse_error"
    agent_id:         str
    angle_id:         str
    attempted_query:  str
    partial_results:  str
    error_message:    str
    round:            int

    def to_context_string(self) -> str:
        return (
            f"AGENT ERROR\n"
            f"agent: {self.agent_id}\n"
            f"failure_type: {self.failure_type}\n"
            f"angle: {self.angle_id}\n"
            f"attempted: {self.attempted_query}\n"
            f"partial: {self.partial_results or 'none'}\n"
            f"END AGENT ERROR"
        )
