## Competitive Analysis Vocabulary

**Capability claim**: a specific assertion about what a product or technology can do,
at what scale, with what limitations. Always quantify if sources allow.

**Load-bearing source**: a source that the VERDICT depends on. Flag these — if they are
wrong, the verdict changes.

**Recency matters**: a 2021 benchmark may be superseded. Flag sources older than 18 months.

## Chunk Structure

CAPABILITY → EVIDENCE → COMPARISON → VERDICT

Each section is 1-3 sentences. Total under 300 words. No bullet points.

## Examples

Good synthesis chunk:
  CAPABILITY: The model processes 128k context tokens in production as of Q1 2025.
  EVIDENCE: Per the vendor's technical documentation (docs.example.com, March 2025),
  128k context is available on all paid tiers. An independent benchmark (MLBench 2025)
  confirmed this with 94% recall at 100k tokens.
  COMPARISON: Competitor A offers 32k, competitor B offers 200k but only in preview.
  VERDICT: Strong capability — production-ready at 128k with independent validation.

Weak synthesis chunk (what not to do):
  CAPABILITY: The model is very capable with long documents.
  EVIDENCE: Several sources suggest it handles long contexts well.
  COMPARISON: It seems better than competitors.
  VERDICT: Good capability.
  [Problem: no specific claims, no citations, no comparison evidence]
