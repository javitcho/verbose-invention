# ── Model ──────────────────────────────────────────────────────────────────────
MODEL = "claude-sonnet-4-6"

# ── Token budgets ───────────────────────────────────────────────────────────────
MAX_TOKENS_PLANNER       = 200
MAX_TOKENS_SEARCHER      = 400
MAX_TOKENS_SYNTHESIZER   = 600
MAX_TOKENS_REVIEWER      = 200
MAX_TOKENS_ORCHESTRATOR  = 600

# ── Loop limits ─────────────────────────────────────────────────────────────────
MAX_ROUNDS_PER_ANGLE  = 3
MAX_TOTAL_ROUNDS      = 12
MAX_ANGLES            = 4

# ── Mode ────────────────────────────────────────────────────────────────────────
DEFAULT_MODE = "scout"   # "scout" | "deep"

# ── Rate limiting ───────────────────────────────────────────────────────────────
REQUEST_DELAY_SECONDS = 0.5

# ── Domain configuration ────────────────────────────────────────────────────────
#
# DOMAIN_NAME: what field is this agent working in?
# Used in agent prompts to set context.
#
# Examples: "machine learning research", "competitive intelligence",
#           "legal analysis", "policy review", "medical literature"
#
DOMAIN_NAME = "competitive technology analysis"

#
# SYNTHESIS_FORMAT_HINT: one sentence describing how a good synthesis
# should be structured in your domain.
#
# Examples: "claim → evidence → assessment → verdict"
#           "problem statement → current approaches → gaps → recommendation"
#           "finding → supporting sources → confidence level"
#
SYNTHESIS_FORMAT_HINT = "capability claim → evidence → competitor comparison → verdict"

#
# CONVERGENCE_MEANING: one sentence describing what ACCEPT means in your domain.
#
# Examples: "all major claims are supported by at least one cited source and
#            no critical counterarguments are unaddressed"
#           "the synthesis clearly states a position, supports it with evidence,
#            and acknowledges its limitations"
#
CONVERGENCE_MEANING = ("synthesis states a clear capability verdict backed by at least "
                       "two sources and addresses the strongest counter-evidence")
