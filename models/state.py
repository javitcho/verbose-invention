from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from models.signals import SessionMode
from models.document import ResearchAngle

@dataclass
class SessionScope:
    purpose: str = "exploration"       # "paper" | "report" | "briefing" | "fun" | "exploration"
    audience: str = "general"          # "research" | "graduate" | "professional" | "general"
    rigor: str = "sketch"              # "full" | "sketch" | "summary"
    stopping_preference: str = "natural"  # "push_through" | "stop_when_hard" | "natural"
    tone_notes: str = ""
    user_focus: str = ""

    def serialize(self) -> str:
        return (f"purpose={self.purpose}, audience={self.audience}, rigor={self.rigor}, "
                f"stopping_preference={self.stopping_preference}, "
                f"tone_notes={self.tone_notes or 'none'}, user_focus={self.user_focus or 'none'}")

@dataclass
class MemoryEntry:
    agent: str
    angle_id: str
    round: int
    note: str

@dataclass
class AgentMemory:
    entries: List[MemoryEntry] = field(default_factory=list)

    def add(self, agent: str, angle_id: str, round: int, note: str):
        self.entries.append(MemoryEntry(agent=agent, angle_id=angle_id, round=round, note=note))

    def get_for_agent(self, agent: str) -> List[MemoryEntry]:
        return [e for e in self.entries if e.agent == agent]

    def format_for_agent(self, agent: str) -> str:
        entries = self.get_for_agent(agent)
        if not entries:
            return "none"
        return "\n".join(f"- [{e.angle_id} r{e.round}] {e.note}" for e in entries[-5:])

@dataclass
class ResearchSession:
    session_id: str
    main_question: str
    scope: SessionScope
    angles: List[ResearchAngle] = field(default_factory=list)
    current_angle_id: str = ""
    final_report: str = ""
    mode: SessionMode = SessionMode.SCOUT
    memory: AgentMemory = field(default_factory=AgentMemory)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
