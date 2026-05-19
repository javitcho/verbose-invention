import os
import uuid
import click
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import config
from models.state import ResearchSession, SessionScope
from models.signals import SessionMode
from agents.planner import Planner
from agents.searcher import Searcher
from agents.synthesizer import Synthesizer
from agents.reviewer import Reviewer
from agents.orchestrator import Orchestrator
from agents.report_writer import ReportWriter
from loop.scout import run_scout
from loop.deep import run_deep
from storage import session_store as store
from output.display import Display


def _make_agents():
    return (
        Planner(config),
        Searcher(config),
        Synthesizer(config),
        Reviewer(config),
        Orchestrator(config),
        ReportWriter(config),
    )


@click.command()
@click.option("--topic", default=None, help="Research question")
@click.option("--mode", default=None, help="scout or deep (default: config.DEFAULT_MODE)")
@click.option("--session", default=None, help="Resume or inspect a session by ID")
@click.option("--list", "list_sessions", is_flag=True, help="List all saved sessions")
@click.option("--inspect", is_flag=True, help="Dump session state (use with --session)")
@click.option("--export", is_flag=True, help="Export final report to markdown (use with --session)")
@click.option("--trace", default=None, help="Print handoff trace for a session ID")
@click.option("--source", default=None, type=click.Choice(["web", "arxiv"]), help="Search source: web (default) or arxiv (via MCP)")
def main(topic, mode, session, list_sessions, inspect, export, trace, source):
    display = Display()

    if source:
        config.SEARCH_SOURCE = source

    if trace:
        try:
            from output.trace import print_trace
            print_trace(trace)
        except (ImportError, NotImplementedError):
            click.echo("trace not yet implemented — complete output/trace.py first")
        return

    if list_sessions:
        sessions = store.list_sessions()
        display.session_list(sessions)
        return

    if session and inspect:
        sess = store.load(session)
        display.session_inspect(sess)
        return

    if session and export:
        sess = store.load(session)
        if not sess.final_report:
            click.echo("No final report in this session.")
            return
        out = Path(f"report_{sess.session_id[:8]}.md")
        out.write_text(f"# Research Report\n\n**Question:** {sess.main_question}\n\n{sess.final_report}\n")
        click.echo(f"Exported to {out}")
        return

    if session and not topic:
        # resume
        sess = store.load(session)
        click.echo(f"Resuming session {session}...")
    elif topic:
        sess = ResearchSession(
            session_id=str(uuid.uuid4())[:8],
            main_question=topic,
            scope=SessionScope(),
            mode=SessionMode(mode or config.DEFAULT_MODE),
        )
    else:
        click.echo("Provide --topic to start a new session or --session to resume. Use --help for options.")
        return

    run_mode = mode or sess.mode.value
    planner, searcher, synthesizer, reviewer, orchestrator, report_writer = _make_agents()

    # Check Synthesizer implemented
    try:
        synthesizer._build_system_prompt()
    except NotImplementedError:
        click.echo("[ERROR] Synthesizer._build_system_prompt() not implemented. See agents/synthesizer.py.")
        return

    if run_mode == "scout":
        run_scout(sess, planner, searcher, synthesizer, reviewer, orchestrator, store, config, display)
    else:
        run_deep(sess, planner, searcher, synthesizer, reviewer, orchestrator, report_writer, store, config, display)

    click.echo(f"\nSession saved: {sess.session_id}")


if __name__ == "__main__":
    main()
