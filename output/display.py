from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint
from models.state import ResearchSession
from models.document import ResearchAngle

console = Console()

class Display:
    def session_start(self, session: ResearchSession):
        console.print(Panel(
            f"[bold]Question:[/bold] {session.main_question}\n"
            f"[bold]Mode:[/bold] {session.mode.value}\n"
            f"[bold]Session ID:[/bold] {session.session_id}",
            title="[bold blue]Research Session Started[/bold blue]",
            border_style="blue",
        ))

    def agent_start(self, agent: str, angle_id: str):
        console.print(f"  [dim]→ {agent.upper()} [{angle_id}] running...[/dim]")

    def agent_done(self, agent: str, note: str):
        console.print(f"  [green]✓ {agent.upper()}:[/green] {note}")

    def synthesis(self, angle: ResearchAngle):
        console.print(Panel(
            angle.synthesis[:600] + ("..." if len(angle.synthesis) > 600 else ""),
            title=f"[bold yellow]Synthesis — {angle.id}[/bold yellow]",
            border_style="yellow",
        ))

    def review(self, angle: ResearchAngle):
        flags_text = "\n".join(angle.reviewer_flags) if angle.reviewer_flags else "none"
        console.print(Panel(
            f"[bold]Flags:[/bold]\n{flags_text}\n\n[bold]Verdict:[/bold] {angle.reviewer_verdict}",
            title=f"[bold magenta]Review — {angle.id}[/bold magenta]",
            border_style="magenta",
        ))

    def final_report(self, session: ResearchSession):
        console.print(Panel(
            session.final_report[:1000] + ("..." if len(session.final_report) > 1000 else ""),
            title="[bold green]Final Report[/bold green]",
            border_style="green",
        ))

    def scout_done(self, session: ResearchSession):
        console.print(Panel(
            session.final_report,
            title="[bold green]Scout Complete[/bold green]",
            border_style="green",
        ))

    def budget_hit(self, total_rounds: int):
        console.print(f"[red]Budget limit hit at round {total_rounds}. Stopping.[/red]")

    def error(self, msg: str):
        console.print(f"[red]ERROR: {msg}[/red]")

    def session_list(self, sessions: list):
        if not sessions:
            console.print("[dim]No saved sessions.[/dim]")
            return
        for s in sessions:
            console.print(f"  [cyan]{s['id']}[/cyan]  {s['question'][:60]}  [{s['mode']}]  {s['created_at'][:10]}")

    def session_inspect(self, session: ResearchSession):
        import json
        from storage.session_store import _session_to_dict
        console.print_json(json.dumps(_session_to_dict(session), indent=2))
