from enum import Enum


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
