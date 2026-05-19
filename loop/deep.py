import time
import threading
import concurrent.futures
import logging
from typing import List
from models.signals import AngleStatus, StoppingSignal, AgentError
from models.document import parse_findings, ReportInput
from loop.scout import _extract_synthesis, _parse_review
from output.display import Display

logger = logging.getLogger(__name__)


def _accum(session_tokens: int, *agents) -> int:
    return session_tokens + sum(a.last_tokens_used for a in agents)


class BudgetExceeded(Exception):
    """Raised when total_rounds reaches MAX_TOTAL_ROUNDS."""
    pass


# ── Parallel search helpers ──────────────────────────────────────────────────────

def _search_one(searcher, session, angle, semaphore):
    with semaphore:
        try:
            sources = searcher.search(session, angle)
            return angle.id, sources
        except Exception as e:
            logger.warning(f"search failed for angle {angle.id}: {e}")
            return angle.id, []


def _search_sequential(searcher, session, angles, delay=0.5):
    results = {}
    for i, angle in enumerate(angles):
        results[angle.id] = searcher.search(session, angle)
        if i < len(angles) - 1:
            time.sleep(delay)
    return results


def _search_parallel(searcher, session, angles, max_workers):
    # BLANK-TODO: implement concurrent search using ThreadPoolExecutor + _search_one
    # semaphore = threading.Semaphore(max_workers)
    # results = {}
    # with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    #     futures = {executor.submit(_search_one, searcher, session, a, semaphore): a for a in angles}
    #     for future in concurrent.futures.as_completed(futures):
    #         angle_id, sources = future.result()
    #         results[angle_id] = sources
    # return results
    raise NotImplementedError("parallel search not yet implemented")


def search_angles(searcher, session, angles, config) -> dict:
    """Dispatch to sequential or parallel search. Returns {angle_id: [sources]}."""
    strategy = getattr(config, "SEARCH_STRATEGY", "sequential")
    delay = getattr(config, "REQUEST_DELAY_SECONDS", 0.5)
    if strategy == "parallel":
        max_workers = getattr(config, "MAX_CONCURRENT_SEARCHES", 2)
        return _search_parallel(searcher, session, angles, max_workers)
    return _search_sequential(searcher, session, angles, delay=delay)


# ────────────────────────────────────────────────────────────────────────────────


def run_deep(session, planner, searcher, synthesizer, reviewer, orchestrator, report_writer, store, config, display):
    """Deep mode: full loop over all angles with revision."""
    display.session_start(session)

    # Plan
    display.agent_start("planner", "session")
    angles = planner.plan(session)
    if not angles:
        display.error("Planner returned no angles.")
        return session
    session.angles = angles
    store.save(session)
    display.agent_done("planner", f"planned {len(angles)} angles")

    total_rounds = 0
    session_tokens = 0
    session_errors: List[AgentError] = []
    session_done = False

    # Pre-fetch all sources (sequential or parallel depending on config.SEARCH_STRATEGY)
    all_sources = search_angles(searcher, session, session.angles, config)
    session_tokens = _accum(session_tokens, searcher)

    for angle in session.angles:
        session.current_angle_id = angle.id
        store.save(session)

        if total_rounds >= config.MAX_TOTAL_ROUNDS:
            display.budget_hit(total_rounds)
            break

        # Attach pre-fetched sources for this angle
        angle.sources = all_sources.get(angle.id, [])
        store.save(session)
        display.agent_start("searcher", angle.id)
        display.agent_done("searcher", f"found {len(angle.sources)} sources")
        display.sources(angle)
        time.sleep(config.REQUEST_DELAY_SECONDS)

        try:
            for round_num in range(config.MAX_ROUNDS_PER_ANGLE):
                angle.round = round_num
                total_rounds += 1
                round_errors: List[AgentError] = []

                # Synthesize
                angle.status = AngleStatus.SYNTHESIZING
                store.save(session)
                display.agent_start("synthesizer", angle.id)
                synthesis_raw = synthesizer.call(session, angle, round_num=round_num)
                angle.synthesis = _extract_synthesis(synthesis_raw)
                angle.findings = parse_findings(synthesis_raw)
                store.save(session)
                if synthesizer.last_error:
                    session_errors.append(synthesizer.last_error)
                    round_errors.append(synthesizer.last_error)
                    synthesizer.last_error = None
                display.agent_done("synthesizer", f"round {round_num}")
                display.synthesis(angle)
                time.sleep(config.REQUEST_DELAY_SECONDS)

                # Review
                angle.status = AngleStatus.REVIEWING
                store.save(session)
                display.agent_start("reviewer", angle.id)
                review_raw = reviewer.call(session, angle, round_num=round_num)
                flags, verdict, verdict_reason = _parse_review(review_raw)
                angle.reviewer_flags = flags
                angle.reviewer_verdict = verdict
                angle.reviewer_verdict_reason = verdict_reason
                store.save(session)
                if reviewer.last_error:
                    session_errors.append(reviewer.last_error)
                    round_errors.append(reviewer.last_error)
                    reviewer.last_error = None
                display.agent_done("reviewer", f"verdict: {verdict}")
                display.review(angle)
                time.sleep(config.REQUEST_DELAY_SECONDS)

                session_tokens = _accum(session_tokens, synthesizer, reviewer)

                # Orchestrator decides
                display.agent_start("orchestrator", angle.id)
                decision = orchestrator.decide(session, angle, total_rounds, round_errors=round_errors)
                session_tokens = _accum(session_tokens, orchestrator)
                store.save(session)
                display.agent_done("orchestrator", f"signal: {decision.get('signal', '?')}")

                # Session-level budget guards (independent of per-round limit)
                if total_rounds >= config.MAX_TOTAL_ROUNDS:
                    raise BudgetExceeded(f"reached MAX_TOTAL_ROUNDS={config.MAX_TOTAL_ROUNDS}")
                if session_tokens >= config.MAX_SESSION_TOKENS:
                    raise BudgetExceeded(f"token budget exhausted: {session_tokens} >= {config.MAX_SESSION_TOKENS}")

                # Circuit breaker: force abandon on the last round regardless of orchestrator signal
                signal = decision.get("signal", "revise").lower()
                if round_num >= config.MAX_ROUNDS_PER_ANGLE - 1:
                    signal = "abandon"

                if signal == "done":
                    angle.status = AngleStatus.ACCEPTED
                    session_done = True
                    break
                elif signal == "accept":
                    angle.status = AngleStatus.ACCEPTED
                    break
                elif signal == "abandon":
                    angle.status = AngleStatus.ABANDONED
                    break
                elif signal == "revise":
                    angle.directive = decision.get("directive_for_synthesizer", "")

                time.sleep(config.REQUEST_DELAY_SECONDS)

            else:
                # exhausted rounds without accept/abandon
                angle.status = AngleStatus.ABANDONED

        except BudgetExceeded:
            display.budget_hit(total_rounds)
            break

        if session_done:
            break

    # Report Writer assembles the brief
    display.agent_start("report_writer", "final")
    report_input = ReportInput(
        main_question=session.main_question,
        scope=session.scope,
        accepted_angles=[a for a in session.angles if a.status == AngleStatus.ACCEPTED],
        abandoned_angles=[a for a in session.angles if a.status == AngleStatus.ABANDONED],
        session_errors=session_errors,
    )
    session.final_report = report_writer.write(report_input)
    store.save(session)
    display.agent_done("report_writer", "brief written")
    display.final_report(session)

    return session
