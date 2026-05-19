## Research Brief Format

### Purpose

A research brief answers one question clearly, honestly, and usefully.
It tells the reader what is established, where sources disagree, and what
to do about it. It does not pretend to more certainty than the sources support.

### Section by Section

**Executive Summary**
Three to four sentences maximum. Written after everything else.
Sentence 1: what the question is.
Sentence 2: the single most important finding.
Sentence 3: the key area of disagreement or uncertainty.
Sentence 4: the recommendation in one clause.

**Thematic Sections**
Each accepted angle becomes one section. The title is descriptive — not the
search query, not "Angle 1." Name it after the insight: "The Cost-Performance
Tradeoff at Scale," not "Scalability, cost, and latency."

Use the synthesis prose. Do not re-bullet it. If the synthesis has a paragraph
that makes an argument, use that paragraph. Add a transition sentence between
sections so the brief reads as one document, not two separate reports.

Cite specific numbers inline: (Source: [url]). Do not list sources at the end
of each section — weave them into the prose.

**Areas of Disagreement**
Only write this section if genuine conflicts exist in the findings.
Do not manufacture disagreement where sources are merely incomplete.
The format is declarative prose: "Sources disagree on whether pgvector is
production-viable past 5M vectors: [Source A] reports it is a full production
solution, while [Source B] identifies a latency breakpoint at exactly that scale."
Both claims, both sources, no resolution.

**Recommendation**
This section exists in every brief. It is the "so what."
Bad: "Teams should evaluate their specific needs and choose accordingly."
Good: "For teams building their first production RAG system on an existing
Postgres stack, start with pgvector. Migrate to Qdrant when filtered-query
latency becomes a bottleneck — the data consistently shows this happens
around 2-5M vectors, not before."
The recommendation is calibrated to the audience and purpose in scope.

**Coverage Gaps**
Only present when an angle was abandoned or an agent failed.
One sentence per gap. Be specific: "The comparison of Milvus and OpenSearch
could not be completed — insufficient sources were returned for this angle."
Do not apologize. Do not hedge. State the gap and move on.

**References**
Numbered list. One per line. Title and URL.

### Tone by Purpose

| purpose | voice | stance |
|---|---|---|
| report | formal, third-person | neutral, evidential |
| briefing | direct, second-person | prescriptive |
| exploration | conversational | speculative, open-ended |
| fun | relaxed | playful where appropriate |

### What Not to Do

- Do not repeat the question as a section heading
- Do not use bullet points in the thematic sections — prose only
- Do not write "In conclusion" or "To summarize" — use section headings instead
- Do not hedge the recommendation into uselessness
- Do not cite a source you were not given
