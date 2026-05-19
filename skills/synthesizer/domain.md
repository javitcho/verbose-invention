## Competitive Analysis Vocabulary

**Capability claim**: a specific assertion about what a product or technology can do,
at what scale, with what limitations. Always quantify if sources allow.

**Load-bearing source**: a source that the VERDICT depends on. Flag these — if they are
wrong, the verdict changes.

**Recency matters**: a 2021 benchmark may be superseded. Flag sources older than 18 months.

## Finding Format

Every claim requires a FINDING block. Do not make unsourced assertions.

Good example (established finding):
  FINDING
  claim: The model supports 128k context tokens in production as of Q1 2025.
  evidence: "128k context is available on all paid tiers" — vendor technical docs, March 2025.
  source_url: https://docs.example.com/context-limits
  publication_date: 2025-03-01
  confidence: established
  END FINDING

Good example (contested finding):
  FINDING
  claim: The model achieves 94% recall at 100k tokens on standard benchmarks.
  evidence: "94% recall observed at 100k token inputs" — MLBench 2025 independent evaluation.
  source_url: https://mlbench.io/2025/results
  publication_date: 2025-02-15
  confidence: contested
  conflicting_claim: The model achieves 87% recall at 100k tokens under production load.
  conflicting_source: https://productionai.blog/context-benchmarks
  END FINDING

Weak example (do not do this):
  FINDING
  claim: The model handles long contexts well.
  evidence: Several sources suggest good performance.
  source_url: various
  publication_date: unknown
  confidence: established
  END FINDING
  [Problem: vague claim, no direct evidence, wrong confidence level]
