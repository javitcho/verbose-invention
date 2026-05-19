import json
import time
from models.signals import AngleStatus, StoppingSignal, SessionMode
from models.document import parse_findings
from output.display import Display

def run_scout(session, planner, searcher, synthesizer, reviewer, orchestrator, store, config, display):
    """Scout mode: one angle, one pass. No revision loop."""
    display.session_start(session)

    # Plan
    display.agent_start("planner", "session")
    angles = planner.plan(session)
    if not angles:
        display.error("Planner returned no angles.")
        return session
    session.angles = angles[:1]  # scout: one angle only
    session.current_angle_id = session.angles[0].id
    store.save(session)
    display.agent_done("planner", f"planned {len(angles)} angles, using first")

    angle = session.angles[0]

    # Search
    display.agent_start("searcher", angle.id)
    sources = searcher.search(session, angle)
    angle.sources = sources
    angle.status = AngleStatus.SYNTHESIZING
    store.save(session)
    display.agent_done("searcher", f"found {len(sources)} sources")
    display.sources(angle)
    time.sleep(config.REQUEST_DELAY_SECONDS)

    # Synthesize
    display.agent_start("synthesizer", angle.id)
    synthesis_raw = synthesizer.call(session, angle, round_num=0)
    angle.synthesis = _extract_synthesis(synthesis_raw)
    angle.findings = parse_findings(synthesis_raw)
    angle.status = AngleStatus.REVIEWING
    store.save(session)
    display.agent_done("synthesizer", "synthesis complete")
    display.synthesis(angle)
    time.sleep(config.REQUEST_DELAY_SECONDS)

    # Review
    display.agent_start("reviewer", angle.id)
    review_raw = reviewer.call(session, angle, round_num=0)
    flags, verdict, verdict_reason = _parse_review(review_raw)
    angle.reviewer_flags = flags
    angle.reviewer_verdict = verdict
    angle.reviewer_verdict_reason = verdict_reason
    store.save(session)
    display.agent_done("reviewer", f"verdict: {verdict}")
    display.review(angle)

    session.final_report = f"SCOUT MODE RESULT\n\nAngle: {angle.question}\n\nSynthesis:\n{angle.synthesis}\n\nReviewer verdict: {verdict}\nVerdict reason: {verdict_reason}\n\nFlags:\n" + ("\n".join(flags) if flags else "none")
    store.save(session)

    display.scout_done(session)
    return session


def _extract_synthesis(raw: str) -> str:
    if "SYNTHESIS" in raw and "END SYNTHESIS" in raw:
        start = raw.index("SYNTHESIS") + len("SYNTHESIS")
        end = raw.index("END SYNTHESIS")
        return raw[start:end].strip()
    return raw.strip()


def _parse_review(raw: str) -> tuple:
    # Reviewer emits JSON via submit_review tool
    try:
        data = json.loads(raw)
        flags = data.get("flags", [])
        signal = data.get("signal", "revise").upper()
        if signal not in ("REVISE", "ACCEPT", "ABANDON"):
            signal = "REVISE"
        # Enforce: empty flags must produce ACCEPT, not REVISE
        if not flags and signal == "REVISE":
            signal = "ACCEPT"
        return flags, signal, data.get("signal_reason", "")
    except (json.JSONDecodeError, Exception):
        pass

    # Fallback: legacy text parsing
    flags = []
    verdict = "REVISE"
    verdict_reason = ""
    lines = raw.strip().split("\n")
    in_flags = False
    for line in lines:
        line = line.strip()
        if line.upper().startswith("FLAGS:"):
            in_flags = True
            rest = line[len("FLAGS:"):].strip()
            if rest and rest.lower() != "none":
                flags.append(rest)
        elif in_flags and line and not line.upper().startswith("VERDICT"):
            if line.lower() != "none":
                flags.append(line)
        elif line.upper().startswith("VERDICT:"):
            in_flags = False
            verdict_text = line[len("VERDICT:"):].strip().upper()
            if verdict_text in ("REVISE", "ACCEPT", "ABANDON"):
                verdict = verdict_text
        elif line.upper().startswith("VERDICT REASON:"):
            verdict_reason = line[len("VERDICT REASON:"):].strip()
    return flags, verdict, verdict_reason
