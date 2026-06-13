# What We Learned: AI Agent Orchestration Experiments

> **This document captures what we discovered by running 695+ subagent tasks across 1,148+ repos.** It's not theory — it's measured findings from real build waves, real failures, and real productivity data. The goal: help others build better agent harnesses by starting from our data, not from scratch.

---

## The Paradigm: Measured Orchestration

Most AI agent systems are tuned by intuition. You run a batch, it feels fast or slow, you adjust. But you never write down the numbers. Over time, you develop a "sense" for what works — but that sense doesn't transfer to others, and it degrades when the underlying models change.

**The SuperInstance approach**: treat every agent run as an experiment. Record γ (cost), η (value), efficiency (η/γ), quality, and lessons. Store in D1. Query before making decisions. The harness becomes a *scientific instrument*, not a gut feeling.

This matters because **orchestration parameters dominate cost**. The difference between batch size 18 and batch size 40 isn't 2× throughput — it's the difference between 100% success and 50% failure. That's a 4× swing in effective cost. You can't afford to guess.

---

## Finding 1: The Batch Size Cliff

### The Experiment

We ran 13 batches of README upgrades, varying batch sizes from 8 to 57 repos per agent:

| Batch Size | Runs | Success Rate | Avg Duration | Notes |
|-----------|------|-------------|-------------|-------|
| 8-10 | 2 | 100% | 8 min | Small, reliable, but underutilizes context |
| **18** | **6** | **100%** | **13 min** | **Sweet spot — full context utilization without overflow** |
| 27 | 2 | 100% | 18 min | Works for small source files |
| 33 | 4 | 100% | 22 min | Works but approaching limit |
| 40 | 1 | 50% | 41 min (died) | Context overflow at ~20 repos |
| 57 | 1 | 53% | 29 min (died) | Context overflow at ~30 repos |

### The Mechanism

Why does batch size 18 work but 40 doesn't? It's not about the number of repos — it's about **total context budget**. Each repo requires:

1. Reading `Cargo.toml` (~200 tokens)
2. Reading `src/*.rs` (~500-2000 tokens per file, 1-5 files)
3. Writing a 4KB README (~1000-1500 tokens output)
4. System prompt + instructions (~500 tokens)

At 18 repos × ~3000 tokens average input = ~54k tokens. Well within a 128k context window.

At 40 repos × ~3000 tokens = ~120k tokens. Right at the limit. Any repo with larger source files (multiple modules, long implementations) pushes over.

**The ternary exception**: Batch b8 (18 ternary-* repos) failed at 8 minutes because ternary crates have unusually large source files (complex trait implementations, extensive match arms). The same 18-repo batch size that works for simple crates fails for complex ones. **Batch size must account for per-item complexity, not just item count.**

### The Rule

> **Batch size = context_budget / (per_item_read_cost + per_item_write_cost + overhead)**
>
> For 128k context, README generation with typical Rust crates: **18 items.**
> For complex crates (large source): **9 items.**
> For simple tasks (metadata only): **50+ items.**

### How to Apply This

Before spawning an agent batch, estimate:
1. How much source code will be read per item? (tokens)
2. How much output per item? (tokens)
3. Total = items × (read + write + overhead). Keep under 60% of context window.

---

## Finding 2: Shell > Agents for Batch Operations

### The Experiment

We needed to add LICENSE files to 300 repos. We tried two approaches:

| Approach | Time | Success | Cost |
|----------|------|---------|------|
| Agent (subagent task) | 10+ minutes | Partial (ran out of context) | ~$0.02 |
| Shell loop (`for d in */; do cp LICENSE "$d"; done`) | 0.3 seconds | 100% | $0.00 |

### The Lesson

Agents are for **decisions**, not **repetitive file operations**. The overhead of LLM inference (latency, token cost, context management) is pure waste when the task is deterministic.

**Decision tree:**
- Does the task require reading and understanding source code? → **Agent**
- Does the task require writing prose, math, or explanations? → **Agent**
- Is it the same operation repeated N times? → **Shell**
- Does it require choosing between approaches? → **Agent**
- Is it a file copy, rename, or metadata update? → **Shell**

### The Deeper Principle

**LLMs are universal computers** — they can do anything. But "can" ≠ "should." A Turing machine can sort an array, but you'd use `sort()`. Similarly, an LLM can add LICENSE files, but you'd use `cp`. The conservation law γ + η = C tells us: if a shell script achieves the same η at near-zero γ, the agent path wastes C.

---

## Finding 3: Specificity Drives Success

### The Experiment

We ran 445+ build waves. Some specs were concrete ("implement a ring buffer with `push()`, `pop()`, `len()`, `clear()`, using `VecDeque` internally"). Others were abstract ("implement a useful data structure").

| Spec Type | Retry Rate | First-Pass Success | Average Quality |
|-----------|-----------|-------------------|-----------------|
| Concrete (exact API, types, behavior) | 0% | 100% | High |
| Semi-specific (domain + rough API) | 20% | 70% | Medium |
| Abstract ("implement something useful") | 50%+ | 30% | Low |

### The Mechanism

LLMs are **completion engines**. Given a specific prompt, there's one good completion. Given an abstract prompt, there are thousands of possible completions — and the model has to guess which one you want. Each guess is a roll of the dice.

Concrete specs collapse the probability space. "Implement `fn push(&mut self, item: T) -> Result<(), T>` where the error case is buffer-full" leaves almost no ambiguity. The model writes the obvious implementation, and it works.

### The Rule

> **Specificity = determinism.** The more concrete your spec, the less the model has to guess, and the higher the success rate. This isn't about prompt engineering — it's about **information density**. A spec that says exactly what to build contains more information than one that says "something useful."

### How to Apply This

Before spawning a task, ask: "Could a competent programmer implement this from my spec alone, without asking questions?" If no, add detail until yes. The spec is the single most important input to the conservation law — vague specs spike γ (rework) without increasing η.

---

## Finding 4: The Bimodal Build Distribution

### The Data

From 445+ build waves, build times fall into two clusters:

```
Duration (minutes)
  │
  │  ████  ████  ████  ████
  │  ████  ████  ████  ████     ← 78% of builds
  │  ████  ████  ████  ████       Complete in <5 min
  │
  │  (gap — almost nothing here)
  │
  │                          ██
  │                          ██
  │                          ██   ← 22% of builds
  │                          ██     Never complete (timeout at 30 min)
  │
  └──────────────────────────────
   0    5    10    15    20    30
```

**Key insight**: Almost no build takes 10-15 minutes. Builds either succeed fast or hang forever. This means waiting is pure waste — if it hasn't built in 10 minutes, it never will.

### The Rule

> **Kill builds at 10 minutes.** The 78% that will succeed have already succeeded. The 22% that haven't will never succeed — they're stuck in dependency resolution hell or infinite macro expansion. Killing at 10 min saves 20 minutes of wasted compute per stuck build.

---

## Finding 5: E0433 Dominates Build Failures

### The Data

From build error analysis across 445+ waves:

| Error Code | Frequency | Cause |
|-----------|-----------|-------|
| **E0433** | **37%** | Missing `mod X;` declaration |
| E0277 | 12% | Trait not implemented |
| E0308 | 10% | Type mismatch |
| E0425 | 8% | Cannot find value/function in scope |
| Other | 33% | Various |

### The Fix

Pre-seed module declarations in `lib.rs` before writing implementation. A simple script:

```bash
for crate in */; do
  cd "$crate/src"
  modules=$(find . -name "*.rs" ! -name "lib.rs" -exec basename {} .rs \;)
  for mod in $modules; do
    grep -q "pub mod $mod;" lib.rs || echo "pub mod $mod;" >> lib.rs
  done
done
```

This eliminates 37% of all build failures with a 10-line shell script. **The conservation law loves this**: near-zero γ, massive η.

---

## Finding 6: The 3-Tier Model Strategy

### What We Use

| Tier | Model | Cost | Best For | When to Use |
|------|-------|------|----------|-------------|
| Expensive | Fable 5 | $$ | Architecture decisions, naming | When the decision will be expensive to reverse |
| Mid | GLM-5.1 (Z.ai) | $ | Decomposition, bridging | When you need to translate architecture → specs |
| Cheap | Seed-2.0-mini (DeepInfra) | ¢ | Execution, batch operations | When you have clear specs and need parallelism |

### The Intelligence Signal

Casey's insight: **the difference between tiers IS the intelligence**. Fable sees structure, names what matters, discards 90% of details. GLM-5.1 takes that structure and decomposes it into executable specs. DeepInfra executes without seeing the whole.

This is a **cost optimization via information loss**. Each tier sees less context than the one above. Fable's γ is high (large context, expensive model) but its η is also high (it makes decisions that prevent rework). DeepInfra's γ is low but its η per task is also low — it's only cheap because the tasks are well-specified.

The harness measures this and adjusts: if GLM-5.1's specs are good enough that DeepInfra succeeds on first pass, the harness routes more work to DeepInfra. If not, it bumps work back to GLM-5.1.

---

## Finding 7: Concurrency Limits

### The Data

| Concurrent Agents | Throughput | Failure Rate | Cause |
|------------------|-----------|-------------|-------|
| 1 | 1× | 0% | Baseline |
| 3 | 2.8× | 2% | Near-linear scaling |
| **5** | **4.5×** | **3%** | **Sweet spot — 5 is the gateway limit** |
| 7 | 4.0× | 15% | Rate limit errors reduce effective throughput |
| 10 | 3.2× | 30% | More failures than successes — net negative |

### The Mechanism

API rate limits are the hard wall. With 5 concurrent agents making requests every ~30 seconds, you're at ~10 req/min — within most rate limits. At 7+, you exceed 14 req/min and start getting 429 errors. Each 429 is wasted γ (retry overhead) with zero η.

### The Rule

> **5 concurrent agents is the optimal throughput point.** Beyond that, rate limit retries dominate and net throughput drops. This is provider-specific but holds for Z.ai and DeepInfra with current rate limits.

---

## The Meta-Lesson: Document Everything

The most important finding isn't any individual number — it's that **having the numbers at all** changes how you work. Before we built the experiments API, we "knew" that 40 repos was too many. After, we knew it was exactly 40 at 50% success vs. 18 at 100%, and the decision was obvious.

Documentation > intuition. Measurements > vibes. The conservation law works because it's measurable. The harness works because we record what happened.

---

## Future Experiments

| Question | How to Test | Expected Finding |
|----------|------------|-----------------|
| Does quality degrade with agent fatigue? | Track quality_score vs. position-in-batch | Slight degradation after position 12 |
| Is parallel always better than sequential? | Same task, sequential vs. parallel | Parallel wins for independent tasks, sequential for dependent |
| What's the optimal prompt length? | Vary system prompt length, measure quality | Concise-but-specific beats verbose |
| Does model routing save money? | A/B test single-model vs. 3-tier | 3-tier saves ~60% with same quality |

---

*This document is updated as new experiments complete. See [live data](https://harness-experiments.casey-digennaro.workers.dev/lessons) for the latest findings.*

*"The crab inherits the shell. The forge shapes the steel. The right moment matters more than the right output."*
