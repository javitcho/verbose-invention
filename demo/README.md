# Demo Scripts

## parallel_coordinator.py

Shows the coordinator-subagent pattern using the Anthropic Task tool.
Run to see latency comparison between sequential and parallel execution.

    python demo/parallel_coordinator.py

This is a standalone demo — it does not use the main session loop.
It illustrates the pattern tested in Anthropic's multi-agent certification exam (Exercise 4, steps 1–2).

### When to use each pattern

| Pattern | Use when | Example |
|---|---|---|
| Sequential pipeline (this workshop) | Agents depend on each other's output | Synthesizer must run before Reviewer |
| Parallel coordinator (Task tool) | Tasks are truly independent | Research two topics simultaneously |

The Task tool pattern requires each subagent to receive ALL context explicitly in its prompt —
subagents have no shared memory and cannot inherit context from the coordinator automatically.
