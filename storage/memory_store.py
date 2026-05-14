# Per-agent memory persistence. Memory is stored in session.memory (AgentMemory).
# This module provides compression utilities for long memory lists.

from models.state import AgentMemory, MemoryEntry
from typing import List

MAX_MEMORY_ENTRIES = 10

def compress_memory(memory: AgentMemory, agent: str) -> AgentMemory:
    """Keep only the last MAX_MEMORY_ENTRIES entries per agent."""
    entries = memory.get_for_agent(agent)
    other_entries = [e for e in memory.entries if e.agent != agent]
    trimmed = entries[-MAX_MEMORY_ENTRIES:]
    memory.entries = other_entries + trimmed
    return memory
