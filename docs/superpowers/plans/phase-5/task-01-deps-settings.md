# Phase 5 · Task 1 — Agent dependencies, model settings, price table, spend-cap setting, test isolation

**Skills:** `plan-execution`, `langgraph`, `langsmith-trace`, `security-checks` (secrets), `project-documentation`.

## Owner decisions (recorded 2026-11-13 — do not re-open)
1. **Model: `gpt-6-luna` for both roles.** `OPENAI_MODEL_FAST=gpt-6-luna` and
   `OPENAI_MODEL_REASONING=gpt-6-luna`. The roles differ only in reasoning effort, fixed in the
   adapter (Task 5): `fast` → `"low"`, `reasoning` → `"medium"`.
   Facts checked 2026-11-13 on `https://developers.openai.com/api/docs/models/gpt-6-luna` and
   `https://developers.openai.com/api/docs/pricing` (Standard tier, prompts ≤ 272 K tokens):
   input **$0.10**, cached input **$0.01**, output **$0.50** per 1 M tokens; cache writes $0.125;
   function calling and structured outputs supported; reasoning model (`reasoning.effort`:
   `none`, `low`, `medium` (default), `high`, `xhigh`, `max`); 1,050,000 context, 128,000 max output.
   **Chat Completions supports function calling only with reasoning effort `none`** → the adapter
   uses the **Responses API** (Task 5).
2. **Spend cap: $4.00 in total** for every paid OpenAI call this project makes (smoke test, manual
   live runs, evaluations, trace recording, any later live run). Enforced in code from a ledger in
   Supabase (`plumetrace.llm_calls`, Task 8; guard in Task 10). The cap is the setting
   `PLUMETRACE_SPEND_CAP_USD` (default `4.00`); only the owner changes it, in the root `.env`.
   Also ask the owner to set a $4 project budget in the OpenAI dashboard as a second guard (owner
   action; never do it yourself).
3. **Per-run budget (replaces the design's $0.30):** soft **$0.05**, hard stop **$0.10** →
   `aborted_budget`. Time budget unchanged: soft 90 s, hard 180 s.
4. **Every paid run is traced to LangSmith** (Task 11 `require_tracing` refuses a paid run when
   tracing is off). Unit tests stay untraced (fake LLM, no network — rule 7).
5. **Everything is stored in local Supabase:** runs, steps (tool inputs/outputs), every LLM call
   (`llm_calls`), backend logs (`app_logs`), eval results (`eval_results`), and LangGraph
   checkpoints (schema `langgraph`) for live, eval and record runs alike (Tasks 8, 10, 11).

**Cost estimate per graph run (planning number):** fast role ≈ 30 k input + 7 k output
(incl. low-effort reasoning), reasoning role ≈ 15 k input + 9 k output (incl. medium reasoning).
Priced conservatively (uncached input at the $0.125 cache-write rate, see `model_prices.py`):
45 k × $0.125 / 1 M + 16 k × $0.50 / 1 M ≈ $0.014 → **use $0.02 per run** for every estimate
until Task 11's pilot measures the real mean.

Record these five decisions in `STATUS.md` (decisions log) if they are not there yet.

## Files
| Action | Path |
|---|---|
| Modify | `app/agents/pyproject.toml` → dependencies: `"pydantic==2.14.3"`, `"langgraph==1.2.18"`, `"langgraph-checkpoint==4.3.1"`, `"langchain-core==1.7.3"`, `"langsmith==0.14.16"` |
| Modify | `app/backend/pyproject.toml` → add `"langgraph-checkpoint-postgres==3.2.0"`, `"langchain-openai==1.7.3"`, `"openai==3.41.0"`, `"langsmith==0.14.16"` |
| Modify | `app/backend/plumetrace/config.py` (three settings), `app/backend/tests/test_config.py` (3 tests) |
| Modify | root `.env.example` (three names, empty values: `OPENAI_MODEL_FAST=`, `OPENAI_MODEL_REASONING=`, `PLUMETRACE_SPEND_CAP_USD=`); root `.env`: already holds `OPENAI_MODEL_FAST=gpt-6-luna`, `OPENAI_MODEL_REASONING=gpt-6-luna`, `PLUMETRACE_SPEND_CAP_USD=4.00` (owner, 2026-11-13). Never open that file; a missing model name is added with `python -I .claude/skills/security-checks/scripts/env_set.py set OPENAI_MODEL_FAST gpt-6-luna` (same for `OPENAI_MODEL_REASONING`). The spend cap is owner-only: if it is missing, ask the owner |
| Modify | `.claude/skills/security-checks/scripts/check_env.py` → `NON_SECRET_NAMES` gains `OPENAI_MODEL_FAST`, `OPENAI_MODEL_REASONING`, `PLUMETRACE_SPEND_CAP_USD` (not secrets); `.claude/skills/security-checks/scripts/secret_scan.py` → same names in its `NON_SECRET_NAMES` (`env_set.py` already lists the two model names in `NON_SECRET_SETTINGS`; leave it) |
| Create | `app/backend/plumetrace/api/model_prices.py`, `app/backend/tests/api/test_model_prices.py` |
| Create | `app/agents/tests/conftest.py`; modify `app/backend/tests/conftest.py` (create it if missing) |
| Modify | `.claude/skills/langgraph/SKILL.md` → the injection line becomes `build_graph(tools: ToolProvider, llm: AgentLLM, checkpointer: BaseCheckpointSaver)`; add "the backend builds the `ChatOpenAI`-based `AgentLLM` and the Postgres saver; `plumetrace_agents` depends on neither `langchain-openai` nor `langgraph-checkpoint-postgres`" |

## Interfaces
`config.py` → `Settings` gains `openai_model_fast: str | None = None`, `openai_model_reasoning: str | None = None`, `plumetrace_spend_cap_usd: Decimal = Field(default=Decimal("4.00"), ge=0, le=Decimal("100"))` (env `PLUMETRACE_SPEND_CAP_USD`), and:
- `def require_models(settings: Settings) -> tuple[str, str]` → `(fast, reasoning)`; missing either → `ConfigurationError("OPENAI_MODEL_FAST and OPENAI_MODEL_REASONING must be set in the root .env (see docs/reference/AGENTS.md)")`.
- `def require_openai_key(settings: Settings) -> SecretStr` → the key; missing → `ConfigurationError("OPENAI_API_KEY is not set in the root .env")`. Never logs or formats the value.

`api/model_prices.py`:
- `@dataclass(frozen=True) class ModelPrice: input_usd_per_1m: Decimal; cached_input_usd_per_1m: Decimal; output_usd_per_1m: Decimal`
- `PRICES: Final[Mapping[str, ModelPrice]] = {"gpt-6-luna": ModelPrice(input_usd_per_1m=Decimal("0.125"), cached_input_usd_per_1m=Decimal("0.01"), output_usd_per_1m=Decimal("0.50"))}`. The module docstring says: the list price for input is $0.10; uncached input is charged here at the $0.125 cache-write rate because the usage report does not separate cache writes from plain input, so the ledger can only over-estimate (safe for the spend cap). Output tokens include reasoning tokens.
- `PRICE_SOURCE: Final = "https://developers.openai.com/api/docs/pricing"`; `PRICES_CHECKED: Final = "2026-11-13"`.
- `LONG_CONTEXT_TOKENS: Final = 272_000` — `cost_usd` raises `ValueError("long-context pricing is not modelled")` when `prompt_tokens > LONG_CONTEXT_TOKENS` (the bounded loop never gets near it; fail visibly if it does).
- `def cost_usd(model: str, prompt_tokens: int, cached_tokens: int, completion_tokens: int) -> Decimal` — `((prompt − cached)·in + cached·cached_in + completion·out) / 1_000_000`, quantised to `Decimal("0.000001")` with `ROUND_UP` (never rounds a billed call down to zero — the spend cap must not under-count; the ledger column is `numeric(12, 6)`; `Decimal("1.850000") == Decimal("1.8500")` so the tests below compare by value); unknown model → `KeyError(f"no price for model {model}")`; negative counts or `cached > prompt` → `ValueError`.

Test `test_model_prices.py` (full code, uses a local price so it does not depend on the owner's numbers):
```python
"""Tests for the model price table."""

from decimal import Decimal

import pytest

from plumetrace.api import model_prices
from plumetrace.api.model_prices import ModelPrice, cost_usd


def test_cost_formula(monkeypatch: pytest.MonkeyPatch) -> None:
    """1 M uncached in at $1, 0.5 M cached at $0.1, 0.2 M out at $4 -> 1 + 0.05 + 0.8."""
    monkeypatch.setattr(model_prices, "PRICES", {"m": ModelPrice(Decimal(1), Decimal("0.1"), Decimal(4))})
    assert cost_usd("m", 1_500_000, 500_000, 200_000) == Decimal("1.8500")


def test_unknown_model_and_bad_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unknown models and impossible token counts are errors."""
    monkeypatch.setattr(model_prices, "PRICES", {"m": ModelPrice(Decimal(1), Decimal(1), Decimal(1))})
    with pytest.raises(KeyError, match="no price for model x"):
        cost_usd("x", 1, 0, 1)
    with pytest.raises(ValueError):
        cost_usd("m", 10, 11, 0)


def test_every_priced_model_is_positive() -> None:
    """The owner-approved table has positive prices."""
    assert model_prices.PRICES
    for price in model_prices.PRICES.values():
        assert price.input_usd_per_1m > 0 and price.output_usd_per_1m > 0


def test_luna_price_and_long_context_guard() -> None:
    """gpt-6-luna: uncached in at $0.125 (cache-write upper bound), cached $0.01, out $0.50."""
    assert cost_usd("gpt-6-luna", 200_000, 100_000, 1_000_000) == Decimal("0.5135")
    with pytest.raises(ValueError, match="long-context"):
        cost_usd("gpt-6-luna", 272_001, 0, 0)
```
(Check: 100 k uncached × 0.125 + 100 k cached × 0.01 + 1 M out × 0.50 = 0.0125 + 0.001 + 0.5 = $0.5135.)
Tests added to `test_config.py`: `plumetrace_spend_cap_usd` is `Decimal("4.00")` with the variable unset (use `Settings(_env_file=None)` — the owner's `.env` also sets it) and `Decimal("0.50")` after `monkeypatch.setenv("PLUMETRACE_SPEND_CAP_USD", "0.50")`; `require_models` raises with neither set (`Settings(_env_file=None)` after `monkeypatch.delenv` of both) and returns the pair when both are set via `monkeypatch.setenv`; `require_openai_key` raises when unset and its message does not contain `sk-`.

`app/agents/tests/conftest.py` and `app/backend/tests/conftest.py` (same autouse fixture; keep any existing content of the backend file):
```python
"""Test isolation: tracing off, no API keys from the environment."""

from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _no_tracing_no_keys(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Unit tests never trace to LangSmith and never see a real API key."""
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    yield
```

## Steps
- [ ] Owner decisions (above) are in STATUS.md.
- [ ] Add the deps (exact) → `cd app && uv lock && uv sync --frozen`; confirm `uv.lock` pins match the README table.
- [ ] Tests → FAIL → implement → `uv run pytest app/backend app/agents -q` green; ruff + mypy clean.
- [ ] The three names are already in `.env.example` and `.env` (2026-11-13). Run `python -I .claude/skills/security-checks/scripts/env_set.py names` (names only) and `python -I .claude/skills/security-checks/scripts/check_env.py .` → `env OK`. A missing model name: add it with `env_set.py set` (see Files). A missing `PLUMETRACE_SPEND_CAP_USD`: ask the owner. Ask the owner to set the $4 project budget in the OpenAI dashboard and wait until they confirm.
- [ ] Repo checks (structure, secret scan).
- [ ] **Docs.** `docs/reference/AGENTS.md` (new; add to `docs/README.md`): purpose, the injection boundary (`plumetrace_agents` ← backend), the model (`gpt-6-luna`, two roles by reasoning effort) and why, the price table source and date and the cache-write upper bound, the per-run budget ($0.05 / $0.10, 90 s / 180 s), the $4 total spend cap and where it is enforced. SECURITY.md → "LLM keys" (where the key lives, never logged). Work-log; `STATUS.md` (last 5.1, next 5.2).
- [ ] **Commit** `build(agents): pin LangGraph stack and add model settings and price table`.
