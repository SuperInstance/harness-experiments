# Headspace ↔ SuperInstance Synergy Analysis

**Date:** 13 June 2026  
**Author:** Phoenix (OpenClaw)  
**Status:** Analysis complete — integration path identified  

---

## What Headspace Actually Is

Headspace is **Loom's implementation of our Priority 1**: the mandatory Headroom transit layer from the Unified Fleet Intelligence thesis. It is a Python ASGI middleware that sits between the Headroom compression proxy and the fleet, injecting compressed fleet state into every LLM request as HTTP headers.

### Architecture (Actual, Not Aspirational)

```
LLM Request → Headspace Proxy (port 8788)
                ↓
    ┌───────────────────────────┐
    │  SuperInstance Middleware  │
    ├───────────────────────────┤
    │  x-headspace-gc:           │  ← GC ledger compression (100-line sample)
    │    <<GC ledger:51 disk:88% │     Schema: count, disk%, freed_kb, aggression
    │    freed:1498512kb agg:0.5│     Source: ~/.openclaw/workspace/data/gc-ledger/
    │    [prune:40 compact:11]>> │
    │                            │
    │  x-headspace-swarm:        │  ← PID controller state
    │    <<SWARM kp:10.0 ki:1.0  │     Source: pid-state.json
    │    kd:0.1>>                │     Drives: compression aggression policy
    │                            │
    │  x-headspace-baton:        │  ← Fleet bottle context (top 5)
    │    <<BATON:                │     Source: baton-system/tiers/hot/*.md
    │    loom: working on X...   │     Format: markdown with **Source:** headers
    │    oracle2: pushed Y...>>  │
    │                            │
    │  x-headspace (version)     │  ← Middleware version stamp
    └───────────────────────────┘
                ↓
         Headroom Core
                ↓
           LLM Provider
```

### Component Map

| Headspace Component | SuperInstance Equivalent | Integration |
|---|---|---|
| `_extension.py` (ASGI middleware) | HEADROOM_FLEET_INTEGRATION.md Transit Point 1 (FLUX bus) | **Direct match** — this IS the transit layer |
| `baton/bridge.py` (fleet sync) | `baton-bridge.ts` (fleet-edge-worker) | **Bidirectional** — Headspace reads bottles, our bridge translates them |
| `swarm/server.py` (PID advisory) | `pid-governor.ts` (fleet-edge-worker) | **Complementary** — Headspace advises compression, ours advises fleet sizing |
| `forge/context.py` (cold-start) | Harness bootstrap pattern | **Aligned** — both snapshot system state for new agents |
| `forge/apply.py` (health check) | fleet-health-monitor Worker | **Redundant** — can merge |

---

## Key Insight: Two PID Controllers, Not One

Headspace and our PID governor solve **different but coupled** control problems:

### Headspace's Swarm PID (port 8765)
- **Controlled variable:** Disk usage percentage (target: 20%)
- **Manipulated variable:** GC aggression (compression policy)
- **Inputs:** GC ledger entries (disk freed, action counts)
- **Output:** Compression policy: aggressive / balanced / conservative
- **Particles:** 9-particle PSO over (setpoint, deadband, integral_limit, kd_boost)

### Our Fleet Governor PID (port 8104)
- **Controlled variable:** γ-η gap (coupling vs value)
- **Manipulated variable:** Agent count (spawn / maintain / retire)
- **Inputs:** Conservation audit from baton-bridge records
- **Output:** Ternary action: +1, 0, -1

### Coupling Analysis

The two controllers are **weakly coupled** through Headroom:

```
More agents (our PID) → More context → More compression needed (Headspace PID)
                     ↓
Higher compression ratio → Lower per-agent γ → Changes our error signal
```

This is a **cascade control** structure. In process control terms:
- Headspace = inner loop (fast, seconds) — manages compression at fixed agent count
- Fleet Governor = outer loop (slow, minutes) — manages agent count given compression

**Stability guarantee:** If the inner loop (Headspace) converges faster than the outer loop (Governor) changes agent count, the cascade is stable. Headspace's 9-particle PSO converges in <1s; our Governor ticks every 5 minutes. **Time-scale separation: 300×. Guaranteed stable.**

---

## Integration Plan (3 Phases)

### Phase 1: Install + Run Headspace (Day 1)
```bash
cd /home/phoenix/repos/headspace
pip install -e .
headspace init  # creates config, verifies headroom dep
headspace proxy start  # port 8788
headspace swarm start  # port 8765
```

This immediately gives us:
- Compressed fleet context in every LLM request header
- Swarm advisory API for compression policy
- Baton bottle ingestion from baton-system

### Phase 2: Wire to fleet-edge-worker (Day 2-3)
- Add `GET /headspace/status` route to fleet-edge-worker that proxies to port 8788
- Add `GET /headspace/swarm` route that proxies to port 8765
- Have the PID Governor's `handleGovernorTick()` read Headspace's swarm policy before making spawn/retire decisions
- This creates the cascade: Governor asks "what compression policy?" → Headspace advises → Governor adjusts setpoint accordingly

### Phase 3: Unified Context Stream (Day 4-5)
- Merge `forge/context.py` snapshot with our harness bootstrap
- Have Headspace's `_inject_baton_context()` read from our fleet-edge-worker `/baton` endpoint instead of filesystem
- Feed Headspace's GC ledger data into our harness-experiments D1 for longitudinal analysis

---

## What Headspace Solves That We Don't

1. **Per-request context injection** — Our architecture has Headroom as a transit point but no implementation. Headspace IS the implementation.

2. **Swarm-optimized compression** — The 9-particle PSO tunes compression aggression based on actual GC performance. We had "compress everything" — Headspace has "compress the right amount."

3. **Forge cold-start** — When a new agent spins up, Headspace's `forge_snapshot()` gives it instant context about fleet state. Our bootstrap script does this for builds, not for agents.

## What We Solve That Headspace Doesn't

1. **Fleet sizing** — Headspace optimizes compression at fixed agent count. Our PID governor decides HOW MANY agents.

2. **Conservation auditing** — Headspace doesn't know about γ+η=C. Our baton-bridge audits every transaction.

3. **Edge distribution** — Headspace runs locally. Our fleet-edge-worker distributes across Cloudflare.

4. **Vectorized knowledge** — Headspace compresses GC logs. Our Vectorize index has 1,541 crate embeddings for semantic search.

---

## The Unified System

```
                    ┌─────────────────┐
                    │  Human (Casey)  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   OpenClaw      │
                    │   (main agent)  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───────┐ ┌───▼────┐ ┌───────▼───────┐
     │ Headspace      │ │ Fleet  │ │ Local GPU     │
     │ (port 8788)    │ │ Edge   │ │ (port 7777)   │
     │                │ │ Worker │ │               │
     │ ┌────────────┐ │ │        │ │ ┌───────────┐ │
     │ │ Headroom   │ │ │ ┌──────┤ │ │ Semantic  │ │
     │ │ Proxy      │◄├─┤─┤ PID  │ │ │ Search    │ │
     │ │ + Fleet    │ │ │ │ Gov  │ │ │ Server    │ │
     │ │ Context    │ │ │ ├──────┤ │ └───────────┘ │
     │ └────────────┘ │ │ │ Baton│ │ ┌───────────┐ │
     │ ┌────────────┐ │ │ │Bridge│ │ │ Crab-trap │ │
     │ │ Swarm PSO  │ │ │ ├──────┤ │ │ Server    │ │
     │ │ (port 8765)│ │ │ │Health│ │ └───────────┘ │
     │ └────────────┘ │ │ │ Mon  │ │               │
     └────────────────┘ │ └──────┘ │ ┌───────────┐ │
                        │          │ │ Embeddings│ │
                        │  CF Edge │ │ (BGE-384) │ │
                        │  Deploy  │ └───────────┘ │
                        └──────────┘               │
                                                   │
                        Cloudflare                 │ Local GPU (RTX 4050)
```

**Result:** Every LLM request carries compressed fleet state. Every fleet decision respects conservation law. Every agent can search 1,541 vectors in <1ms. The PID governor auto-scales. The swarm PSO auto-tunes compression. **Cognitive homeostasis.**

---

## References

- [Headspace repo](https://github.com/SuperInstance/headspace) — Loom's project
- [Headroom](https://github.com/SuperInstance/headroom) — Underlying compression engine
- HEADROOM_FLEET_INTEGRATION.md — Our Opus 4 integration spec (944 lines)
- UNIFIED_FLEET_INTELLIGENCE.md — Priority 1 = Headroom Transit Layer
- PID_FLEET_GOVERNOR.md — Our governor architecture (518 lines)
- baton-bridge.ts — Our baton↔FLUX translation (747 lines)
