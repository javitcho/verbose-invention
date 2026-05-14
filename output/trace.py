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
    "tokens": int,           # actual from response.usage, passed from BaseAgent.last_tokens_used
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
        Column header: "tokens" (not "tokens (est)")

    def trace_summary(session_id) -> dict
        Returns: total_rounds, total_tokens, handoffs_by_agent,
                 validation_failures, signals_issued, total_cost_estimate
        total_cost_estimate = total_tokens * 0.000003
        Add summary row: Estimated cost: $X.XXXXX

This is your observability layer. Without it, debugging why the loop
stopped where it did requires reading raw session JSON. With it,
you can see the whole session in 10 lines.
"""
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path(__file__).parent.parent / "sessions"


def log_handoff(session_id, angle_id, round, from_agent, to_agent,
                signal, output, output_valid) -> None:
    entry = {
        "ts": datetime.utcnow().isoformat(),
        "session_id": session_id,
        "angle_id": angle_id,
        "round": round,
        "from_agent": from_agent,
        "to_agent": to_agent,
        "signal": signal,
        "token_estimate": len(output) // 4,
        "output_valid": output_valid,
        "note": f"{from_agent} → {to_agent}" + (f" [{signal}]" if signal else ""),
    }
    trace_dir = SESSIONS_DIR / session_id
    trace_dir.mkdir(parents=True, exist_ok=True)
    trace_file = trace_dir / "trace.jsonl"
    with open(trace_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def print_trace(session_id) -> None:
    from rich.console import Console
    from rich.table import Table

    console = Console()
    trace_file = SESSIONS_DIR / session_id / "trace.jsonl"
    if not trace_file.exists():
        console.print(f"[dim]No trace file for session {session_id}[/dim]")
        return

    table = Table(title=f"Trace — {session_id}")
    table.add_column("round", style="dim")
    table.add_column("from → to")
    table.add_column("signal")
    table.add_column("tokens", justify="right")
    table.add_column("valid")

    with open(trace_file) as f:
        for line in f:
            entry = json.loads(line.strip())
            signal = entry.get("signal") or ""
            valid = entry.get("output_valid", True)
            tokens = str(entry.get("token_estimate", 0))
            from_to = f"{entry['from_agent']} → {entry['to_agent']}"
            valid_str = "[green]✓[/green]" if valid else "[red]✗[/red]"
            if signal == "ACCEPT":
                signal_display = f"[green]{signal}[/green]"
            elif signal == "ABANDON":
                signal_display = f"[yellow]{signal}[/yellow]"
            else:
                signal_display = signal
            table.add_row(str(entry.get("round", 0)), from_to, signal_display, tokens, valid_str)

    console.print(table)


def trace_summary(session_id) -> dict:
    trace_file = SESSIONS_DIR / session_id / "trace.jsonl"
    if not trace_file.exists():
        return {}

    entries = []
    with open(trace_file) as f:
        for line in f:
            try:
                entries.append(json.loads(line.strip()))
            except Exception:
                pass

    handoffs_by_agent: dict = {}
    signals_issued: dict = {}
    validation_failures = 0
    total_tokens = 0

    for e in entries:
        agent = e.get("from_agent", "unknown")
        handoffs_by_agent[agent] = handoffs_by_agent.get(agent, 0) + 1
        sig = e.get("signal")
        if sig:
            signals_issued[sig] = signals_issued.get(sig, 0) + 1
        if not e.get("output_valid", True):
            validation_failures += 1
        total_tokens += e.get("token_estimate", 0)

    return {
        "total_rounds": len(entries),
        "total_tokens_est": total_tokens,
        "handoffs_by_agent": handoffs_by_agent,
        "validation_failures": validation_failures,
        "signals_issued": signals_issued,
    }
