from dataclasses import dataclass, field
from typing import List
from enum import Enum
import re
from models.signals import AngleStatus, AgentError

@dataclass
class Source:
    url: str
    title: str
    snippet: str       # 2-4 sentence extract
    relevance: str     # one sentence: why relevant


class Confidence(Enum):
    ESTABLISHED = "established"   # multiple independent sources agree
    CONTESTED   = "contested"     # credible sources disagree
    UNCLEAR     = "unclear"       # insufficient evidence to judge


@dataclass
class Finding:
    claim:             str
    evidence:          str
    source_url:        str
    publication_date:  str
    confidence:        Confidence
    conflicting_claim:  str = ""
    conflicting_source: str = ""


def parse_findings(synthesis_text: str) -> "List[Finding]":
    """Parse FINDING...END FINDING blocks from synthesis text. Returns [] if none found."""
    findings = []
    blocks = re.findall(r'FINDING\n(.*?)END FINDING', synthesis_text, re.DOTALL)
    for block in blocks:
        def get_field(name: str) -> str:
            m = re.search(rf'^{name}:\s*(.+?)(?=\n\w[\w_]*:|$)', block, re.MULTILINE | re.DOTALL)
            return m.group(1).strip() if m else ""

        conf_str = get_field("confidence").lower()
        confidence = {
            "established": Confidence.ESTABLISHED,
            "contested":   Confidence.CONTESTED,
        }.get(conf_str, Confidence.UNCLEAR)

        claim      = get_field("claim")
        evidence   = get_field("evidence")
        source_url = get_field("source_url")
        if not (claim and evidence and source_url):
            continue
        findings.append(Finding(
            claim=claim,
            evidence=evidence,
            source_url=source_url,
            publication_date=get_field("publication_date") or "unknown",
            confidence=confidence,
            conflicting_claim=get_field("conflicting_claim"),
            conflicting_source=get_field("conflicting_source"),
        ))
    return findings


@dataclass
class ResearchAngle:
    id: str
    question: str
    sources: List[Source] = field(default_factory=list)
    synthesis: str = ""
    status: AngleStatus = AngleStatus.PENDING
    reviewer_flags: List[str] = field(default_factory=list)
    reviewer_verdict: str = ""
    reviewer_verdict_reason: str = ""
    round: int = 0
    directive: str = ""   # Orchestrator's directive to Synthesizer for next round
    findings: List[Finding] = field(default_factory=list)


@dataclass
class ReportInput:
    main_question:    str
    scope:            "SessionScope"       # models.state.SessionScope
    accepted_angles:  List[ResearchAngle]  # status == ACCEPTED
    abandoned_angles: List[ResearchAngle]  # status == ABANDONED
    session_errors:   List[AgentError]
