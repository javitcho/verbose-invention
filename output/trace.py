"""
BLANK-TODO: implement the handoff trace log.

A trace log records every agent handoff in the session as a structured entry:
{
    "ts": ISO timestamp,
    "session_id": str,
    "angle_id": str,
    "round": int,
    "from_agent": str,
    "to_agent": str,
    "signal": str or None,
    "token_estimate": int,   # rough: len(output) // 4
    "output_valid": bool,
    "note": str              # one line: what passed between agents
}

Implement:
    def log_handoff(session_id, angle_id, round, from_agent, to_agent,
                    signal, output, output_valid) -> None
        Appends one entry to sessions/{session_id}/trace.jsonl

    def print_trace(session_id) -> None
        Pretty-prints the trace for a session using rich.
        Show: round | from → to | signal | tokens | valid
        Highlight: invalid outputs in red, ABANDON signals in yellow,
                   ACCEPT signals in green.

    def trace_summary(session_id) -> dict
        Returns: total_rounds, total_tokens_est, handoffs_by_agent,
                 validation_failures, signals_issued

This is your observability layer. Without it, debugging why the loop
stopped where it did requires reading raw session JSON. With it,
you can see the whole session in 10 lines.
"""


def log_handoff(session_id, angle_id, round, from_agent, to_agent,
                signal, output, output_valid) -> None:
    # TODO: implement — see module docstring
    pass


def print_trace(session_id) -> None:
    # TODO: implement — see module docstring
    print("trace not yet implemented — complete output/trace.py first")


def trace_summary(session_id) -> dict:
    # TODO: implement — see module docstring
    return {}
