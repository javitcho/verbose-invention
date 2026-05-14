# Research Agent Skeleton — Design Reference

## 1. Architecture Overview

Five agents, two loop modes, one shared session state.

```
User question
    │
    ▼
Planner ──► [angle_1, angle_2, ..., angle_N]
                        │
            ┌───────────┘
            │  for each angle:
            ▼
        Searcher ──► [Source, Source, ...]
            │
            ▼
        Synthesizer ──► synthesis draft
            │
            ▼
        Reviewer ──► FLAGS + VERDICT
            │
            ▼
        Orchestrator ──► signal: revise | accept | abandon | done | budget
            │
            └──► if REVISE: directive → Synthesizer (next round)
            └──► if DONE: assemble final report
```

**Scout mode**: one angle, one pass, no revision. Fast feedback loop.
**Deep mode**: all angles, revision loop per angle until ACCEPT/ABANDON or budget hit.

## 2. Data Models

### Source
A single web source retrieved by the Searcher.
- `url`, `title`: identity
- `snippet`: 2-4 sentence extract — what the page says
- `relevance`: one sentence — why it addresses this angle

### ResearchAngle
One focused sub-question derived from the main research question.
- `id`, `question`: identity
- `sources`: list of Source objects from Searcher
- `synthesis`: current draft text from Synthesizer
- `status`: AngleStatus enum (PENDING → SEARCHING → SYNTHESIZING → REVIEWING → ACCEPTED/ABANDONED)
- `reviewer_flags`: list of flag strings from Reviewer
- `reviewer_verdict`: REVISE | ACCEPT | ABANDON
- `round`: current revision round number
- `directive`: Orchestrator's specific instruction to Synthesizer for next round

### ResearchSession
Top-level container for a research run.
- `session_id`, `main_question`, `created_at`: identity
- `scope`: SessionScope (purpose, audience, rigor, stopping_preference, tone_notes, user_focus)
- `angles`: list of ResearchAngle
- `current_angle_id`: which angle is active
- `final_report`: assembled report (filled by Orchestrator when signal=done)
- `mode`: SessionMode (SCOUT | DEEP)
- `memory`: AgentMemory — cross-round notes from agents

### SessionScope
Controls how agents calibrate their output.
- `purpose`: paper | report | briefing | fun | exploration
- `audience`: research | graduate | professional | general
- `rigor`: full | sketch | summary
- `stopping_preference`: push_through | stop_when_hard | natural

### StoppingSignal
Enum values the Orchestrator can issue:
- CONTINUE, REVISE, ACCEPT, DONE, BUDGET, USER_STOP, SCOUT_DONE

## 3. Agent Interfaces

### Planner
**Input**: `main_question` + `scope`
**Output**: JSON list of angles `[{id, question}]`
**Contract**: always returns at least one angle (fallback to single angle on parse failure)

### Searcher
**Input**: `angle.question` + `main_question` + `scope`
**Output**: JSON list of sources `[{url, title, snippet, relevance}]`
**Contract**: uses web_search_20250305 tool; returns empty list on failure

### Synthesizer (YOU IMPLEMENT THIS)
**Input** (from `_build_user_message` in base.py):
- `RESEARCH ANGLE`: the sub-question
- `MAIN QUESTION`: the top-level question
- `SOURCES`: list of Source objects
- `PREVIOUS SYNTHESIS`: prior draft if revising, else "none"
- `REVIEWER FLAGS`: flags from last review if revising, else "none"
- `DIRECTIVE FROM ORCHESTRATOR`: specific revision instruction, else "none"
- `SCOPE`: serialized SessionScope
- `YOUR MEMORY`: agent's recent memory entries

**Output format** (parsed by `loop/scout.py` and `loop/deep.py`):
```
SYNTHESIS
[full synthesis text]
END SYNTHESIS

MEMORY NOTE:
[one bullet: what you did, what you struggled with]
```

**Skill file**: `skills/synthesizer/domain.md` — appended to system prompt automatically.

### Reviewer (YOU IMPLEMENT THIS)
**Input** (from `_build_user_message` override in `reviewer.py`):
- `RESEARCH ANGLE`: the sub-question
- `SYNTHESIS DRAFT`: the Synthesizer's output
- `SOURCES AVAILABLE`: original sources for reference
- `SCOPE`: serialized SessionScope
- `YOUR MEMORY`: agent's recent memory entries

**Output format** (parsed by `_parse_review` in `loop/scout.py`):
```
FLAGS:
[one line per issue, or "none"]

VERDICT: REVISE
VERDICT REASON: [one sentence]

MEMORY NOTE:
[one bullet]
```
VERDICT must be exactly: REVISE | ACCEPT | ABANDON (case-sensitive, parsed literally).

**Skill file**: `skills/reviewer/criteria.md` — appended to system prompt automatically.

### Orchestrator
**Input**: full session state (all angles + statuses), current angle details, round counts
**Output**: JSON `{signal, signal_reason, directive_for_synthesizer, final_report}`
**Contract**: fallback to REVISE on parse failure

## 4. Loop Logic

### Scout Mode (`loop/scout.py`)
1. Plan → take only first angle
2. Search that angle
3. Synthesize (round 0)
4. Review (round 0)
5. Write `final_report` with verdict + flags
6. Return (no Orchestrator, no revision)

### Deep Mode (`loop/deep.py`)
1. Plan → all angles
2. For each angle:
   a. Search (once)
   b. For each round (0 to MAX_ROUNDS_PER_ANGLE - 1):
      - Synthesize
      - Review
      - Orchestrator decides: REVISE (set directive, continue) | ACCEPT (break) | ABANDON (break) | DONE/BUDGET (break)
   c. If loop exhausts rounds without ACCEPT/ABANDON → mark ABANDONED
3. Assemble final report via `orchestrator.assemble_report()`

**Budget**: MAX_TOTAL_ROUNDS across all angles. Checked before each angle and each round.

## 5. Session Storage

Sessions are saved as JSON in `sessions/{session_id}.json` after every agent call.
`session_store.py` handles serialization/deserialization of all dataclasses.
`memory_store.py` provides `compress_memory()` to trim long memory lists.

## 6. Skill Files

Skill files are plain markdown files under `skills/`.
`BaseAgent._load_skill()` reads the file and appends it to the system prompt as `## SKILL FILE`.
If the file is empty or starts with `<!--`, it is silently ignored.

This lets you add domain vocabulary, format examples, and evaluation criteria without
touching the agent's Python code.

## 7. Configuration (config.py)

Three blocks you fill in for your domain:
- `DOMAIN_NAME`: one-phrase description of the field
- `SYNTHESIS_FORMAT_HINT`: one sentence on synthesis structure
- `CONVERGENCE_MEANING`: one sentence on what ACCEPT means in your domain

Token budgets, loop limits, and model are set at the top of `config.py`.

## 8. Claude Code Prompts for Each TODO

### config.py (3 TODO blocks)

```
Fill in the three domain configuration constants in config.py:
1. DOMAIN_NAME — one phrase describing the field this agent works in
2. SYNTHESIS_FORMAT_HINT — one sentence describing how a good synthesis
   should be structured (e.g., "claim → evidence → assessment → verdict")
3. CONVERGENCE_MEANING — one sentence describing what it means for a synthesis
   to be "good enough" in your domain (this is the ACCEPT condition)

Look at the existing examples in the comments for guidance.
```

### agents/synthesizer.py

```
Implement Synthesizer._build_system_prompt() in agents/synthesizer.py.

The method must return a string. The string should tell the agent:
1. TASK: what it is synthesizing and for whom (use config.DOMAIN_NAME)
2. OUTPUT FORMAT: the structure of a synthesis in your domain
   (use config.SYNTHESIS_FORMAT_HINT as the basis)
3. SCOPE CALIBRATION: how to adjust for purpose/audience/rigor
4. REVISION BEHAVIOR: when REVIEWER FLAGS are present, how to address them
5. CONSTRAINTS: length (use config.MAX_TOKENS_SYNTHESIZER as a guide), terminology

The output MUST include:
    SYNTHESIS
    [synthesis text]
    END SYNTHESIS
    MEMORY NOTE:
    [one bullet]

See base.py for what the user message contains — you do not need to override _build_user_message.
```

### skills/synthesizer/domain.md

```
Add domain-specific synthesis guidance to skills/synthesizer/domain.md.
This file is appended to the Synthesizer's system prompt automatically.

Include:
- Key vocabulary for your domain (terms the agent should use consistently)
- The chunk structure with a concrete example of a GOOD synthesis
- A counter-example showing what a WEAK synthesis looks like and why

Keep it under 300 words. Plain markdown, no code blocks.
```

### agents/reviewer.py

```
Implement Reviewer._build_system_prompt() in agents/reviewer.py.

The method must return a string. The string should tell the agent:
1. TASK: what it is reviewing (a synthesis in your domain) and from what perspective
2. REVIEW CRITERIA: the quality dimensions to check (list 4-6 specific criteria)
3. FLAG FORMAT: [location] → [issue type] → [brief note]
4. VERDICT LOGIC: exactly when to issue REVISE vs ACCEPT vs ABANDON
5. CONSTRAINTS: 200 tokens max; terse flags only

The output MUST follow this format EXACTLY (the loop parses these lines):
    FLAGS:
    [one line per flag or "none"]

    VERDICT: REVISE
    VERDICT REASON: [one sentence]
    MEMORY NOTE: [one bullet]

VERDICT must be one of: REVISE, ACCEPT, ABANDON — case-sensitive.
```

### skills/reviewer/criteria.md

```
Add domain-specific review criteria to skills/reviewer/criteria.md.
This file is appended to the Reviewer's system prompt automatically.

Include:
- 4-6 numbered review dimensions with concrete pass/fail examples for each
- A verdict guide: what evidence pattern → ACCEPT vs REVISE vs ABANDON

Keep it under 250 words. Use the same vocabulary as skills/synthesizer/domain.md.
```

## 9. Branch States

| Branch | synthesizer.py | reviewer.py | domain.md | criteria.md |
|---|---|---|---|---|
| main | complete (reference) | complete (reference) | complete | complete |
| session-1 | BLANK-TODO | stub (placeholder) | empty | empty |
| session-2 | complete (reference) | BLANK-TODO | complete | empty |

**session-1** is the starting state for attendees in Session 1.
**session-2** is the starting state for attendees in Session 2.
**main** is the complete reference implementation.
