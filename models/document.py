from dataclasses import dataclass, field
from typing import List
from models.signals import AngleStatus

@dataclass
class Source:
    url: str
    title: str
    snippet: str       # 2-4 sentence extract
    relevance: str     # one sentence: why relevant

@dataclass
class ResearchAngle:
    id: str
    question: str
    sources: List[Source] = field(default_factory=list)
    synthesis: str = ""
    status: AngleStatus = AngleStatus.PENDING
    reviewer_flags: List[str] = field(default_factory=list)
    reviewer_verdict: str = ""
    round: int = 0
    directive: str = ""   # Orchestrator's directive to Synthesizer for next round
