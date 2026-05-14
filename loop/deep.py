import time
from models.signals import AngleStatus, StoppingSignal
from loop.scout import _extract_synthesis, _parse_review
from output.display import Display


class BudgetExceeded(Exception):
    """Raised when total_rounds reaches MAX_TOTAL_ROUNDS."""
    pass


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

        if total_rounds >= config.MAX_TOTAL_ROUNDS:
            display.budget_hit(total_rounds)
            break

        # Search (once per angle — sources don't change between revision rounds)
        display.agent_start("searcher", angle.id)
        sources = searcher.search(session, angle)
        angle.sources = sources
        store.save(session)
        display.agent_done("searcher", f"found {len(sources)} sources")
        time.sleep(config.REQUEST_DELAY_SECONDS)

        try:
            for round_num in range(config.MAX_ROUNDS_PER_ANGLE):
                angle.round = round_num
                total_rounds += 1

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
                store.save(session)
                display.agent_done("orchestrator", f"signal: {decision.get('signal', '?')}")

                # TODO (session-1): implement signal routing, circuit breaker, and budget guard.
                #
                # This is where the system decides what happens next. The orchestrator told you
                # what it wants — you decide whether to trust it. The circuit breaker here is
                # not optional: without it, a stuck angle runs forever.
                #
                # Implement four things, in this order:
                #
                # 1. BUDGET GUARD — enforce both iteration and cost limits independently.
                #    Add at session start: session_tokens = 0
                #    After each agent call: session_tokens += agent.last_tokens_used
                #    Two independent checks:
                #      if total_rounds >= config.MAX_TOTAL_ROUNDS:
                #          raise BudgetExceeded("round limit reached")
                #      if session_tokens >= config.MAX_SESSION_TOKENS:
                #          raise BudgetExceeded(f"token limit reached: {session_tokens}")
                #    The surrounding try/except catches BudgetExceeded and stops the session cleanly.
                #
                # 2. AGENT BUDGET EXCEEDED — catch AgentBudgetExceeded from individual agent calls.
                #    Treat as a failed call: use agent._fallback_output(), do not crash the round.
                #    Import: from models.signals import AgentBudgetExceeded
                #
                # 3. CIRCUIT BREAKER — override the orchestrator when rounds are exhausted:
                #       if round_num >= config.MAX_ROUNDS_PER_ANGLE - 1:
                #           signal = "abandon"  # override regardless of orchestrator output
                #    Without this, a REVISE signal on the last round loops past the limit.
                #
                # 4. SIGNAL ROUTING — act on the (possibly overridden) signal:
                #    - "revise"  → set angle.directive = decision.get("directive_for_synthesizer", "")
                #                  leave status as-is, continue the loop
                #    - "accept"  → angle.status = AngleStatus.ACCEPTED, break
                #    - "abandon" → angle.status = AngleStatus.ABANDONED, break
                #    - "done"    → angle.status = AngleStatus.ACCEPTED, break
                #
                raise NotImplementedError(
                    "TODO: implement signal routing — read the comment above and replace this raise"
                )

            else:
                # exhausted rounds without accept/abandon
                angle.status = AngleStatus.ABANDONED

        except BudgetExceeded:
            display.budget_hit(total_rounds)
            break

    # Assemble final report
    display.agent_start("orchestrator", "final-report")
    session.final_report = orchestrator.assemble_report(session)
    store.save(session)
    display.agent_done("orchestrator", "final report assembled")
    display.final_report(session)

    return session
