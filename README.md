# Harness Experiments API

> **🔬 The science of AI agent productivity — measured, not guessed.**

[![Live](https://img.shields.io/badge/API-live-00E6D6?style=flat-square&labelColor=0a0a0f)](https://harness-experiments.casey-digennaro.workers.dev)
[![License: MIT](https://img.shields.io/badge/license-MIT-00E6D6?style=flat-square&labelColor=0a0a0f)](LICENSE)

## What This Is

The Harness Experiments API captures, indexes, and serves **experimental findings about how AI agent harnesses work most productively**. Every build wave, every subagent batch, every orchestration experiment gets recorded with measurable metrics — cost (γ), value (η), efficiency (η/γ), quality, and lessons learned.

**The problem it solves**: AI agent orchestration is full of folklore ("use small batches", "don't run too many concurrent agents") but short on data. This API turns folklore into measurements. When someone asks "what batch size should I use?", the answer comes from experiments, not vibes.

## Why It Matters

Conservation law γ + η = C says every task has a fixed budget. The question is: **what parameters maximize the exchange rate between γ (spending) and η (producing)?** This API answers that question with data.

Key findings from our corpus (updated continuously):

| Finding | Evidence | Confidence |
|---------|----------|------------|
| **Batch size 18 is optimal** for README generation | 18-repo batches: 100% success. 40-repo batches: 50% success (context overflow). | 95% |
| **Shell > agents for batch ops** | For-loop adds LICENSE to 300 repos in 30s. Agent takes 10+ min. | 99% |
| **E0433 is 37% of build errors** | Missing `mod X;` declarations. Pre-seed them. | 95% |
| **Specificity → success** | Concrete specs = 0% retry. Abstract specs = 50%+ retry. | 90% |
| **Kill builds at 10 minutes** | Bimodal: 78% finish <5min, rest never finish. | 92% |
| **5 concurrent agents max** | Beyond 5, rate limits kill throughput. | 80% |

## How It Works

### Architecture

```
Agent completes batch → POST /experiment (with all metrics)
                              │
                              ▼
                    D1 Database (harness-experiments)
                    ├── Raw experiment rows
                    ├── Generated columns: γ, η, efficiency, success_rate
                    └── Indexes on category, model, batch_size, provider
                              │
                              ▼
                    KV Cache (5min TTL for dashboard, 1hr for lessons)
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
              GET /lessons          GET /optimal
         (distilled findings)   (best parameters)
```

### Conservation Law Integration

Every experiment computes γ and η as **generated columns in D1**:

- **γ (cost)** = `tokens_in + tokens_out + (wall_clock_seconds × 10) + (api_calls × 50)`
- **η (value)** = `(items_completed × 100) + (quality_score × 500) + (lessons_extracted × 200)`
- **Efficiency** = `η / γ` (higher is better — more value per unit cost)

This means every query automatically has conservation-law context. You can't ask "what's the best model?" without also seeing what it cost.

### D1 Schema

```sql
CREATE TABLE experiments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  experiment_id TEXT UNIQUE,
  timestamp INTEGER NOT NULL,
  category TEXT NOT NULL,         -- readme_generation, code_gen, etc.
  description TEXT NOT NULL,
  model TEXT NOT NULL,
  batch_size INTEGER NOT NULL,
  concurrent_agents INTEGER NOT NULL,
  provider TEXT NOT NULL,
  -- γ inputs
  tokens_in INTEGER DEFAULT 0,
  tokens_out INTEGER DEFAULT 0,
  wall_clock_seconds INTEGER DEFAULT 0,
  api_calls INTEGER DEFAULT 0,
  -- η inputs
  items_completed INTEGER DEFAULT 0,
  items_failed INTEGER DEFAULT 0,
  quality_score REAL DEFAULT 0,   -- 0.0 to 1.0
  lessons_extracted INTEGER DEFAULT 0,
  -- Derived (auto-computed by D1)
  gamma REAL GENERATED ALWAYS AS (...) STORED,
  eta REAL GENERATED ALWAYS AS (...) STORED,
  efficiency REAL GENERATED ALWAYS AS (eta / gamma) STORED,
  success_rate REAL GENERATED ALWAYS AS (...) STORED
);
```

## Quick Start

### Record an Experiment

```bash
curl -X POST https://harness-experiments.casey-digennaro.workers.dev/experiment \
  -H "Content-Type: application/json" \
  -d '{
    "category": "readme_generation",
    "description": "18-repo batch with Seed-2.0-mini",
    "model": "deepinfra/bytedance/seed-2.0-mini",
    "batch_size": 18,
    "concurrent_agents": 5,
    "provider": "deepinfra",
    "tokens_in": 80000,
    "tokens_out": 25000,
    "wall_clock_seconds": 960,
    "api_calls": 18,
    "items_completed": 18,
    "items_failed": 0,
    "quality_score": 0.85,
    "lessons_extracted": 2
  }'
```

### Query Lessons

```bash
curl https://harness-experiments.casey-digennaro.workers.dev/lessons
```

Returns distilled findings sorted by confidence, with category summaries and best-model-per-category.

### Get Optimal Parameters

```bash
curl https://harness-experiments.casey-digennaro.workers.dev/optimal
```

### Analyze a Dimension

```bash
curl -X POST https://harness-experiments.casey-digennaro.workers.dev/analyze \
  -H "Content-Type: application/json" \
  -d '{"dimension": "batch_size"}'
```

Valid dimensions: `batch_size`, `model`, `provider`, `concurrent_agents`, `category`.

### Dashboard

```bash
curl https://harness-experiments.casey-digennaro.workers.dev/dashboard
```

## API Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/experiment` | Record experiment result |
| `GET` | `/experiments` | List experiments (filter by `?category=`, `?model=`, `?provider=`, `?min_batch=`, `?max_batch=`, `?limit=`) |
| `GET` | `/experiment/:id` | Single experiment by ID |
| `GET` | `/lessons` | Distilled key findings with confidence scores |
| `GET` | `/optimal` | Current optimal parameters per category |
| `POST` | `/analyze` | Run analysis on a dimension |
| `GET` | `/dashboard` | Productivity summary |
| `GET` | `/docs` | Interactive HTML documentation |

## Architecture Notes

- **γ + η = C**: Every experiment is a data point in the conservation law. The harness uses aggregated efficiency data to adjust γ/η allocation for future cycles (via the [harness-api](https://github.com/SuperInstance/superinstance-harness) Worker).
- **Scale invariance**: The efficiency metric η/γ is scale-invariant — it works for a single agent or a fleet of 100. This is why the conservation law holds at fleet level.
- **Generated columns**: D1's `GENERATED ALWAYS AS` computes γ, η, efficiency, and success_rate automatically. No application code needed — the database enforces the math.
- **Cache strategy**: KV caches dashboard (5min TTL) and lessons/optimal (1hr TTL). Recording a new experiment invalidates caches.

## Experiment Categories

| Category | What It Measures | Key Finding |
|----------|-----------------|-------------|
| `readme_generation` | README quality upgrades | 18 repos/batch optimal, Seed-2.0-mini efficient |
| `code_generation` | Code writing tasks | Specificity → success (future data) |
| `build_optimization` | Build harness tuning | Kill at 10min, pre-seed declarations (future data) |
| `model_comparison` | Cross-model experiments | Seed-2.0-mini cheapest quality (current data) |
| `orchestration` | Multi-agent coordination | 5 concurrent max (future data) |

## References

- SuperInstance Conservation Law: γ + η = C. See [ARCHITECTURE.md](https://github.com/SuperInstance/SuperInstance/blob/main/ARCHITECTURE.md)
- Cloudflare D1 Generated Columns: [SQLite docs](https://www.sqlite.org/gencol.html)
- Cloudflare Workers AI: [@cf/baai/bge-small-en-v1.5](https://developers.cloudflare.com/workers-ai/models/bge-small-en-v1.5/)

## License

MIT
