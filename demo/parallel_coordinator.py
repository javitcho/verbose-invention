import time
import concurrent.futures
import anthropic

client = anthropic.Anthropic()


def run_subagent(prompt: str) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


TASK_TOOL = {
    "name": "Task",
    "description": "Delegate a research subtask to a subagent.",
    "input_schema": {
        "type": "object",
        "properties": {
            "subagent_prompt": {
                "type": "string",
                "description": "The complete prompt for the subagent. Must include all context explicitly — subagents have no shared memory."
            },
            "subagent_id": {
                "type": "string",
                "description": "Identifier for this task, e.g. 'vector_db', 'graph_db'"
            }
        },
        "required": ["subagent_prompt", "subagent_id"]
    }
}


def run_coordinator():
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        tools=[TASK_TOOL],
        tool_choice={"type": "auto"},
        messages=[{
            "role": "user",
            "content": (
                "Research two database types in parallel. "
                "Use two Task tool calls — one for vector databases, "
                "one for graph databases. Each subagent should answer: "
                "what is it, what is it used for, one key limitation. "
                "Pass all context explicitly in each subagent_prompt."
            )
        }]
    )
    return [
        b.input for b in response.content
        if b.type == "tool_use" and b.name == "Task"
    ]


def run_subagent_from_task(task: dict) -> dict:
    result = run_subagent(task["subagent_prompt"])
    return {"subagent_id": task["subagent_id"], "result": result}


if __name__ == "__main__":
    # Part 1 — Sequential
    print("=== SEQUENTIAL (our pipeline pattern) ===")
    t0 = time.time()
    result_a = run_subagent("In one sentence: what is a vector database?")
    result_b = run_subagent("In one sentence: what is a graph database?")
    print(f"Latency: {time.time() - t0:.2f}s")
    print(f"A: {result_a}")
    print(f"B: {result_b}")

    # Part 2 — Parallel via Task tool
    print("\n=== PARALLEL (Task tool coordinator pattern) ===")
    t0 = time.time()
    tasks = run_coordinator()
    print(f"Coordinator emitted {len(tasks)} Task calls in one response")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_subagent_from_task, t) for t in tasks]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    print(f"Latency: {time.time() - t0:.2f}s")
    for r in results:
        print(f"{r['subagent_id']}: {r['result']}")

    # Part 3 — Key differences
    print("\n=== KEY DIFFERENCES ===")
    print("Sequential: simple, predictable, no concurrency issues, easier to debug.")
    print("Parallel:   faster for independent tasks, requires explicit context in each prompt,")
    print("            concurrency adds complexity, API rate limits apply per-request.")
    print()
    print("Our workshop system uses sequential because:")
    print("  - API concurrency limits would fire with 4 agents in parallel")
    print("  - Sequential output is readable agent-by-agent in the trace")
    print("  - Agents are NOT independent: Reviewer needs Synthesizer's output")
    print()
    print("Use parallel when: tasks are truly independent, latency matters more than simplicity.")
    print("Use sequential when: agents depend on each other's output (our case).")
