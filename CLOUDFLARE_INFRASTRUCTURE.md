# SuperInstance Cloudflare Infrastructure

> **The complete guide to what we run on Cloudflare, why, and what each piece does.**
>
> Last updated: 2026-06-13

---

## Infrastructure Overview

SuperInstance uses Cloudflare as its cloud substrate — edge compute, vector search, D1 databases, KV storage, and AI inference. The fleet's nervous system runs entirely on Workers, with vessels connecting from ARM cloud, RTX 4050, and Jetson edge devices.

### Why Cloudflare?

1. **Edge-first**: Workers run in 300+ locations. Bottle dispatch happens at the nearest edge to each vessel.
2. **AI-native**: Workers AI gives us BGE embeddings without managing a GPU inference server.
3. **Composable**: D1 (SQL), KV (key-value), Vectorize (vectors), R2 (objects), and Workers all bind together in a single deployment.
4. **Cost**: Workers + D1 + KV + Vectorize for the entire fleet costs less than a single VPS.

---

## Deployed Workers

### 1. fleet-vector-api — Semantic Crate Intelligence

| Property | Value |
|----------|-------|
| **URL** | https://fleet-vector-api.casey-digennaro.workers.dev |
| **Source** | [fleet-vector-api](https://github.com/SuperInstance/fleet-vector-api) |
| **Bindings** | Workers AI, Vectorize (`fleet-crates`), KV (`META_KV`) |
| **Crate count** | 1,541 |
| **Embedding model** | @cf/baai/bge-small-en-v1.5 (384-dim) |

**What it does**: Semantic search across the entire crate ecosystem. Embeds crate descriptions + READMEs into 384-dim vectors, stores in Vectorize, and serves search/recommend/gap-analysis endpoints.

**Key endpoints**:
- `POST /search` — "find crates about distributed consensus"
- `POST /recommend` — context-aware recommendations with reasoning
- `POST /gap-analysis` — find underdeveloped crates
- `GET /dashboard` — fleet health aggregation
- `GET /docs` — interactive HTML documentation
- `GET /openapi.json` — OpenAPI 3.1 spec

**Architecture**: Read more → [fleet-vector-api README](https://github.com/SuperInstance/fleet-vector-api)

---

### 2. harness-api — Conservation Law Controller

| Property | Value |
|----------|-------|
| **URL** | https://harness-api.casey-digennaro.workers.dev |
| **Source** | [superinstance-harness](https://github.com/SuperInstance/superinstance-harness) |
| **Bindings** | D1 (`harness-cycles`), KV (`STATE`) |

**What it does**: Implements the conservation law γ + η = C as a running controller. Each work cycle records γ (tokens, time) and η (quality, quantity, lessons). The harness computes an EWMA quality signal and adjusts the γ/η allocation for the next cycle.

**Key endpoints**:
- `POST /cycle` — record a completed work cycle, get new allocation
- `GET /allocation` — recommended γ/η split for next cycle
- `GET /metrics` — EWMA quality, exploration ROI, regret, cycle count
- `POST /feedback` — external quality signal adjustment

**The control loop**:
```
Cycle completes → POST /cycle (γ, η, quality)
    → Harness updates EWMA metrics
    → Computes ternary signal: +1 (exploit more), 0 (maintain), -1 (explore more)
    → Quality gate: if quality declining for 3+ cycles, force rebalance to 50/50
    → Returns new γ/η allocation
    → Next cycle uses the allocation
```

---

### 3. harness-experiments — Productivity Science

| Property | Value |
|----------|-------|
| **URL** | https://harness-experiments.casey-digennaro.workers.dev |
| **Source** | [harness-experiments](https://github.com/SuperInstance/harness-experiments) |
| **Bindings** | D1 (`harness-experiments`), KV (`CACHE`) |

**What it does**: Captures, indexes, and serves experimental findings about how AI agent harnesses work most productively. Every batch run, model comparison, and orchestration experiment gets recorded with measurable γ/η metrics.

**Key endpoints**:
- `POST /experiment` — record experiment with full metrics
- `GET /lessons` — distilled findings with confidence scores
- `GET /optimal` — data-driven optimal parameters
- `POST /analyze` — analyze a dimension (batch_size, model, etc.)
- `GET /dashboard` — productivity summary

**D1 schema**: Uses `GENERATED ALWAYS AS` columns to auto-compute γ, η, efficiency (η/γ), and success_rate. The database enforces the math — no application code needed.

**Key findings (from real data)**:
- Batch size 18 = 100% success. Size 40+ = 50% success (context overflow).
- Shell > agents for batch file operations (30s vs 10min, $0.00 vs $0.02)
- E0433 (missing mod) = 37% of build failures. Pre-seed declarations.
- 5 concurrent agents = optimal throughput. 7+ = rate limit failures.
- Kill builds at 10 minutes. Bimodal: 78% finish <5min, rest never finish.

**Documentation**: See [EXPERIMENTS.md](https://github.com/SuperInstance/harness-experiments/blob/main/EXPERIMENTS.md) for the full findings document.

---

### 4. fleet-edge-worker — Edge Bottle Dispatcher

| Property | Value |
|----------|-------|
| **URL** | https://fleet-edge.casey-digennaro.workers.dev |
| **Source** | [fleet-edge-worker](https://github.com/SuperInstance/fleet-edge-worker) |
| **Bindings** | KV (`FLEET_KV`), R2 (`VESSELS` optional), Workers AI, Vectorize |
| **Version** | 0.3.1 |

**What it does**: Routes bottles (agent-to-agent messages) from HTTP requests to vessel targets. Implements the I2I Bottle Protocol at the edge — dispatch, poll, confirm.

**Key endpoints**:
- `POST /dispatch` — route an action to a fleet agent via bottle
- `POST /dispatch/smart` — vector-aware routing (uses embeddings to find best agent)
- `POST /context` — semantic context lookup (proxies to fleet-vector-api)
- `GET /status` — fleet operational status
- `GET /agents` — registered agent registry (7 agents)
- `GET /actions` — registered actions (16 actions)
- `GET /bottles/:agent` — poll an agent's bottle inbox
- `PUT /bottles/:id` — confirm bottle delivery/consumption

**Agent registry**:
| Agent | Port | Capabilities |
|-------|------|-------------|
| fleet-midi | 8101 | chord, fx, melody, rhythm |
| ghost-track | 8102 | accompaniment, variation |
| persona-engine | 8103 | persona, voice |
| fleet-conductor | 8104 | conduct, schedule, tempo |
| forgemaster | 8105 | forge, build, compile |
| oracle2 | 8106 | infer, voice-to-midi |
| construct | 8107 | coordinate, dispatch |

---

### 5. superinstance-ai — Website (CF Pages)

| Property | Value |
|----------|-------|
| **URL** | https://superinstance.ai |
| **Source** | [SuperInstance/SuperInstance](https://github.com/SuperInstance/SuperInstance) |
| **Hosting** | Cloudflare Pages (`superinstance-ai` project) |

**What it is**: The main project website. Landing page with conservation law explanation, fleet overview, documentation hub, onboarding flow, and security policy.

---

## Storage Backends

### Vectorize Indexes

| Index | Dimensions | Model | Vectors | Purpose |
|-------|-----------|-------|---------|---------|
| `fleet-crates` | 384 | @cf/baai/bge-small-en-v1.5 | 1,541 | Crate semantic search |
| `superinstance-knowledge` | 32 | Custom | — | Experimental low-dim index |

### D1 Databases

| Database | Binding | Used By | Purpose |
|----------|---------|---------|---------|
| `harness-cycles` | DB | harness-api | Conservation law cycle tracking |
| `harness-experiments` | DB | harness-experiments | Productivity experiment data |
| `fleet-events` | — | (planned) | Fleet event log |
| `fleet-auth-db` | — | fleet-auth | Agent authentication |

### KV Namespaces

| Namespace | ID | Used By | Purpose |
|-----------|-----|---------|---------|
| `META_KV` | `3db4cb08...` | fleet-vector-api | Crate metadata cache |
| `STATE` | `dbdc9a17...` | harness-api | Harness state (γ/η allocation) |
| `CACHE` | `76094ed2...` | harness-experiments | Cached lessons/dashboard |
| `FLEET_KV` | — | fleet-edge-worker | Bottle routing, agent inboxes |

### R2 Buckets

| Bucket | Used By | Purpose |
|--------|---------|---------|
| `VESSELS` | fleet-edge-worker | Durable bottle log (optional) |

---

## Workers AI Usage

| Model | Purpose | Called By |
|-------|---------|----------|
| @cf/baai/bge-small-en-v1.5 | Crate embeddings (384-dim) | fleet-vector-api |
| @cf/baai/bge-small-en-v1.5 | Smart dispatch embeddings | fleet-edge-worker |

**Cost**: Workers AI is included in the Workers plan. BGE-small embeddings are extremely cheap — we've embedded 1,541 crates for less than $0.01 total.

---

## Architecture: How It All Connects

```
                        ┌─────────────────────────────────┐
                        │     superinstance.ai (Pages)    │
                        │     Landing + docs + onboarding │
                        └───────────────┬─────────────────┘
                                        │
                        ┌───────────────▼─────────────────┐
                        │   fleet-vector-api (Worker)     │
                        │   Semantic search / 1,541 crates│
                        │   Workers AI + Vectorize + KV   │
                        └──────┬──────────────┬───────────┘
                               │              │
                    ┌──────────▼──┐  ┌────────▼──────────┐
                    │ fleet-edge  │  │ harness-api       │
                    │ -worker     │  │ Conservation law  │
                    │ Bottle      │  │ γ + η = C         │
                    │ dispatch    │  │ D1 + KV           │
                    │ KV + R2     │  └───────────────────┘
                    └──────┬──────┘
                           │              ┌──────────────────┐
                           │              │ harness-         │
                           │              │ experiments      │
                           │              │ Productivity     │
                           │              │ findings         │
                           │              │ D1 + KV          │
                           │              └──────────────────┘
                           │
          ┌────────────────┼────────────────────┐
          ▼                ▼                    ▼
   ┌──────────────┐ ┌──────────────┐  ┌──────────────┐
   │  Oracle1     │ │ Forgemaster  │  │ JetsonClaw1  │
   │  ARM Cloud   │ │ RTX 4050     │  │ Jetson Orin  │
   │  Coordinator │ │ Build/engine │  │ Edge infer   │
   └──────────────┘ └──────────────┘  └──────────────┘
```

---

## Deploy Commands

```bash
# Set token (scoped to Workers/Pages deploys only)
export CLOUDFLARE_API_TOKEN='<your-scoped-token>'  # Workers/Pages deploys only

# Deploy fleet-vector-api
cd /home/phoenix/repos/fleet-vector-api
npx wrangler deploy

# Deploy harness-api
cd /home/phoenix/repos/superinstance-harness/worker
npx wrangler deploy

# Deploy harness-experiments
cd /home/phoenix/repos/harness-experiments
npx wrangler deploy

# Deploy fleet-edge-worker
cd /home/phoenix/repos/fleet-edge-worker
npx wrangler deploy

# Deploy website (CF Pages)
cd /home/phoenix/.openclaw/workspace/SuperInstance
npx wrangler pages deploy . --project-name=superinstance-ai --branch=main --commit-dirty=true
```

---

## Account Details

- **Account**: casey.digennaro@gmail.com
- **Account ID**: `049ff5e84ecf636b53b162cbb580aae6`
- **API Token**: Scoped to Workers/Pages deploys only (cannot purge cache)
- **Plan**: Workers Paid ($5/mo) — includes D1, KV, Vectorize, Workers AI

---

## Conservation Law in Infrastructure

Every Worker participates in γ + η = C:

| Worker | γ (cost it adds) | η (value it provides) |
|--------|-----------------|----------------------|
| fleet-vector-api | Embedding compute (Workers AI) | Search results, recommendations, gap analysis |
| harness-api | D1 writes, KV reads | γ/η allocation guidance, quality gate |
| harness-experiments | D1 writes | Lessons learned, optimal parameters |
| fleet-edge-worker | KV writes, R2 writes | Bottle routing, agent coordination |

The harness-api **is** the conservation law — it literally computes γ and η and adjusts allocation. The experiments API measures how well that adjustment works. The vector-api provides the knowledge substrate. The edge-worker handles communication.

---

*This document is the definitive Cloudflare infrastructure reference. Updated as new Workers are deployed.*
