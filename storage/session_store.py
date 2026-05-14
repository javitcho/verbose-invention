import json
import os
from pathlib import Path
from dataclasses import asdict
from models.state import ResearchSession, SessionScope, AgentMemory, MemoryEntry
from models.document import ResearchAngle, Source
from models.signals import AngleStatus, SessionMode

SESSIONS_DIR = Path(__file__).parent.parent / "sessions"

def save(session: ResearchSession):
    SESSIONS_DIR.mkdir(exist_ok=True)
    path = SESSIONS_DIR / f"{session.session_id}.json"
    data = _session_to_dict(session)
    path.write_text(json.dumps(data, indent=2))

def load(session_id: str) -> ResearchSession:
    path = SESSIONS_DIR / f"{session_id}.json"
    data = json.loads(path.read_text())
    return _dict_to_session(data)

def list_sessions() -> list:
    SESSIONS_DIR.mkdir(exist_ok=True)
    sessions = []
    for f in sorted(SESSIONS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            sessions.append({
                "id": data["session_id"],
                "question": data["main_question"],
                "mode": data["mode"],
                "created_at": data["created_at"],
                "angles": len(data.get("angles", [])),
            })
        except Exception:
            pass
    return sessions

def _session_to_dict(session: ResearchSession) -> dict:
    return {
        "session_id": session.session_id,
        "main_question": session.main_question,
        "scope": {
            "purpose": session.scope.purpose,
            "audience": session.scope.audience,
            "rigor": session.scope.rigor,
            "stopping_preference": session.scope.stopping_preference,
            "tone_notes": session.scope.tone_notes,
            "user_focus": session.scope.user_focus,
        },
        "angles": [
            {
                "id": a.id,
                "question": a.question,
                "sources": [{"url": s.url, "title": s.title, "snippet": s.snippet, "relevance": s.relevance} for s in a.sources],
                "synthesis": a.synthesis,
                "status": a.status.value,
                "reviewer_flags": a.reviewer_flags,
                "reviewer_verdict": a.reviewer_verdict,
                "round": a.round,
                "directive": a.directive,
            }
            for a in session.angles
        ],
        "current_angle_id": session.current_angle_id,
        "final_report": session.final_report,
        "mode": session.mode.value,
        "memory": {
            "entries": [
                {"agent": e.agent, "angle_id": e.angle_id, "round": e.round, "note": e.note}
                for e in session.memory.entries
            ]
        },
        "created_at": session.created_at,
    }

def _dict_to_session(data: dict) -> ResearchSession:
    scope = SessionScope(**data["scope"])
    angles = []
    for a in data.get("angles", []):
        sources = [Source(**s) for s in a.get("sources", [])]
        angles.append(ResearchAngle(
            id=a["id"],
            question=a["question"],
            sources=sources,
            synthesis=a.get("synthesis", ""),
            status=AngleStatus(a.get("status", "pending")),
            reviewer_flags=a.get("reviewer_flags", []),
            reviewer_verdict=a.get("reviewer_verdict", ""),
            round=a.get("round", 0),
            directive=a.get("directive", ""),
        ))
    memory = AgentMemory()
    for e in data.get("memory", {}).get("entries", []):
        memory.entries.append(MemoryEntry(**e))
    return ResearchSession(
        session_id=data["session_id"],
        main_question=data["main_question"],
        scope=scope,
        angles=angles,
        current_angle_id=data.get("current_angle_id", ""),
        final_report=data.get("final_report", ""),
        mode=SessionMode(data.get("mode", "scout")),
        memory=memory,
        created_at=data.get("created_at", ""),
    )
