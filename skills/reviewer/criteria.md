## Review Dimensions

1. **Claim support**: every CAPABILITY and VERDICT must be traceable to a source in EVIDENCE.
   Bad: "the model is fast" with no benchmark. Good: "the model processes X tokens/sec per [source]."

2. **Proportionality**: VERDICT strength (strong/moderate/weak) must match evidence quantity and quality.
   Two sources from the vendor alone → at most moderate. Independent benchmark → can be strong.

3. **Competitor coverage**: if COMPARISON says "no competitor data" but a source covers competitors,
   flag it. If sources genuinely don't cover competitors, "no data" is acceptable.

4. **Recency**: for technology claims, sources older than 18 months need explicit flagging
   unless they are foundational (e.g., original paper for a method).

5. **Specificity**: vague language where sources provide specifics is always a flag.

## Verdict Guide

ACCEPT: specific claims, two or more independent sources, competitors addressed if data available.
REVISE: one or two specific issues that the Synthesizer can fix with the provided sources.
ABANDON: question is unanswerable with these sources — recommend a different search angle.
