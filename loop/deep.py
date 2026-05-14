import time
from models.signals import AngleStatus, StoppingSignal
from loop.scout import _extract_synthesis, _parse_review
from output.display import Display

def run_deep(session, planner, searcher, synthesizer, reviewer, orchestrator, store, config, display):
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

    for angle in session.angles:
        session.current_angle_id = angle.id
        store.save(session)

        # Budget check
        if total_rounds >= config.MAX_TOTAL_ROUNDS:
            display.budget_hit(total_rounds)
            break

        # Search (once per angle)
        display.agent_start("searcher", angle.id)
        sources = searcher.search(session, angle)
        angle.sources = sources
        store.save(session)
        display.agent_done("searcher", f"found {len(sources)} sources")
        time.sleep(config.REQUEST_DELAY_SECONDS)

        # Revision loop
        for round_num in range(config.MAX_ROUNDS_PER_ANGLE):
            angle.round = round_num
            total_rounds += 1

            if total_rounds > config.MAX_TOTAL_ROUNDS:
                display.budget_hit(total_rounds)
                return session

            # Synthesize
            angle.status = AngleStatus.SYNTHESIZING
            store.save(session)
            display.agent_start("synthesizer", angle.id)
            synthesis_raw = synthesizer.call(session, angle, round_num=round_num)
            angle.synthesis = _extract_synthesis(synthesis_raw)
            store.save(session)
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
            store.save(session)
            display.agent_done("reviewer", f"verdict: {verdict}")
            display.review(angle)
            time.sleep(config.REQUEST_DELAY_SECONDS)

            # Orchestrator decides
            display.agent_start("orchestrator", angle.id)
            decision = orchestrator.decide(session, angle, total_rounds)
            signal = decision.get("signal", "revise").lower()
            store.save(session)
            display.agent_done("orchestrator", f"signal: {signal}")

            if signal == "accept":
                angle.status = AngleStatus.ACCEPTED
                break
            elif signal == "abandon":
                angle.status = AngleStatus.ABANDONED
                break
            elif signal == "revise":
                angle.directive = decision.get("directive_for_synthesizer", "")
                # loop continues
            elif signal in ("done", "budget"):
                angle.status = AngleStatus.ACCEPTED
                break
            time.sleep(config.REQUEST_DELAY_SECONDS)

        else:
            # exhausted rounds without accept/abandon
            angle.status = AngleStatus.ABANDONED

    # Assemble final report
    display.agent_start("orchestrator", "final-report")
    session.final_report = orchestrator.assemble_report(session)
    store.save(session)
    display.agent_done("orchestrator", "final report assembled")
    display.final_report(session)

    return session
