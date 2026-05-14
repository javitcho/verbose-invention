# Research Agent Workshop

Build a multi-agent research assistant for your domain in two one-hour sessions.

## What you'll build

A four-agent system that:
1. Breaks your research question into focused search angles
2. Searches the web for real sources on each angle
3. Synthesizes the sources into a structured draft in your domain's format
4. Reviews the draft like a peer reviewer and requests revisions
5. Iterates until the synthesis is good enough, then assembles a final report

## What you configure

Everything domain-specific: how to structure a synthesis, and what quality means.
Everything else (web search, revision loop, session storage, final report assembly) is pre-built.

## Prerequisites

- Python 3.11+
- An Anthropic API key (console.anthropic.com → API Keys → New Key, add $5 credit)
- Claude Code (desktop app or claude.ai) — your co-pilot for the implementation parts

## Quickstart

    git clone [REPO_URL]
    cd research-agent-skeleton
    pip install -r requirements.txt
    cp .env.example .env
    # paste your API key into .env

    # verify setup — you're ready if you see agent output
    python main.py --topic "test" --mode scout

## Session map

| Session | What you build | Deliverable |
|---|---|---|
| Session 1 | Synthesizer agent + domain skill file | scout mode runs end-to-end |
| Session 2 | Reviewer agent + criteria skill file | deep mode runs with revision loop |

## CLI

    python main.py --topic "your question" --mode scout
    python main.py --topic "your question" --mode deep
    python main.py --session [id]          # resume
    python main.py --list                  # list saved sessions
    python main.py --inspect --session [id]   # dump session state
    python main.py --export --session [id]    # export final report to markdown

## Reference implementation

`github.com/[org]/math-department-agent-chaos` — the full production version of this
architecture applied to mathematical research. Seven agents, dependency graph, LaTeX output.
Look at it to see how deep this pattern goes.
