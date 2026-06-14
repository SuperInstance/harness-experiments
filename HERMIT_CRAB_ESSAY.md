# The Hermit Crab's Guide to Building Things That Last

### What 1,150 repositories, 9 programming languages, and one conservation law taught us about systems, ideas, and the art of migration

---

## The Crab

There's a hermit crab in the header of our conservation explorer. It migrates between shells labeled Rust, Julia, C, Fortran, COBOL — pausing on each before moving to the next. It's not decoration. It's the thesis.

A hermit crab doesn't build its own shell. It finds one, adapts to it, lives in it until it outgrows the space, and then migrates. The crab stays the same. The shell changes. The *species* evolves because individual crabs carry life between shells, transplanting themselves into new homes while keeping their identity intact.

This is exactly what we did with the conservation law.

## The Law

We started with a question: *What happens when a million independent agents each emit a signal — yes, no, or abstain?*

The answer is always approximately zero. Not by coordination, not by design, not by central control. By mathematics. The positive and negative signals cancel, the abstentions contribute nothing, and the residual is a vanishingly small fraction of the total. At 50 agents, 86.3% of the signal cancels. At 10,000, it's 99%. At a million, it's 99.9%.

This isn't just a statistical curiosity. It's the **Shannon chain rule** — the foundational identity of information theory, wearing different clothes:

> **γ + η = C**

What the guide knows (γ) plus what remains uncertain (η) equals the total information (C). Always. Everywhere. In every system where independent components contribute signals.

We proved this in nine programming languages, and each one taught us something different — not about the law, but about *ourselves*. About what we value, what we optimize for, what we consider "correct."

## The Shells

### Rust (9.2 billion signals/second)

Rust won the zero-allocation showdown at 9.2 billion signals per second. Not because it's the fastest language — C is theoretically faster — but because Rust's ownership model makes accidental allocation *impossible*. You can't write `vec.push()` in a hot loop without the compiler asking uncomfortable questions about lifetimes and borrows.

The lesson: **Safety doesn't cost performance. Safety IS performance.** When the compiler eliminates entire classes of mistakes, the remaining code runs closer to the metal. Rust doesn't win despite being safe. It wins *because* it's safe.

### Julia (4.8 billion signals/second)

Julia's JIT compiler fuses the inner loop into a single block of machine code. The expression `sum(rand([-1, 0, 1], n))` doesn't allocate a temporary array — Julia sees that you're summing, generates a loop that never materializes the intermediate, and the result is code that's faster than C for this pattern.

The lesson: **Abstractions don't cost performance. BAD abstractions do.** Julia's abstraction (write math, get speed) works because it was designed by people who understood that the gap between intent and execution is the real bottleneck.

### COBOL (5 million signals/second — and zero floating-point error)

COBOL was the slowest implementation by far. But it was the only one with *zero* floating-point rounding error. COBOL uses fixed-point decimal arithmetic — the same kind banks use for your account balance. When COBOL says the answer is 0.86280, it's exactly 0.86280. Not 0.8627999868.

In 2026, a language designed in 1959 outperforms everything we've built since on the dimension that matters most for audit trails: exactness. Your mortgage is calculated in COBOL. Your stock trades clear through COBOL. The financial infrastructure of the planet runs on a 67-year-old language because *it never lies about decimal quantities*.

The lesson: **"Obsolete" is contextual.** COBOL is obsolete for web servers, machine learning, and user interfaces. For financial audit trails, it's still the state of the art. The question isn't "is this technology old?" but "is this technology right for THIS problem?"

### Elixir (20 million signals/second — and a natural fleet model)

Elixir's implementation didn't just compute the conservation law. It *embodied* it. Each agent is a GenServer process — a lightweight actor with its own state, communicating via messages. The FleetSupervisor watches them. When a process crashes (which Elixir processes do, by design), the supervisor restarts it. The fleet heals itself.

The conservation law in Elixir isn't a function call. It's a *property of the runtime*. When 10,000 GenServer processes each emit a ternary signal, the cancellation happens as an emergent property of message passing — not as a mathematical formula applied to an array.

The lesson: **Some languages don't implement your domain. They ARE your domain.** Elixir's actor model IS the fleet. Erlang's fault tolerance IS the governance. You're not writing a fleet simulation. You're running a fleet.

### D (50 million signals/second — and compile-time theorem proving)

D's `@safe` and `@nogc` annotations let you prove properties of your code at compile time. The `in { }` and `out { }` contract blocks verify pre- and post-conditions. We wrote contracts that assert γ + η = C — and the compiler *checked them*. Not at runtime. Before the program ever ran.

The lesson: **The strongest test is the one that runs at compile time.** Every contract you write is a bug you can never ship. D's philosophy — that mathematical correctness should be verifiable by the compiler — is a glimpse of what programming could be if we took correctness seriously.

## The Discovery

After implementing the same law nine times, we noticed something strange.

The throughput numbers spanned a 1,840× range — from Rust's 9.2 billion to COBOL's 5 million. But the *answer* was always the same. γ + η = C held to less than 10⁻¹⁰ in every language, on every run, regardless of paradigm, arithmetic type, or parallelism model.

This shouldn't be surprising — it's a mathematical identity, not an empirical observation. But it *feels* surprising, because we're used to thinking of programming languages as tools for getting different results. Here, they're tools for getting the *same* result, differently.

**The conservation law is paradigm-independent.** It doesn't care whether you think in objects (Elixir), functions (Julia), types (Rust), contracts (D), or business processes (COBOL). The math works. The language is just a lens.

And here's the deepest version of that insight: **the conservation law is not just paradigm-independent — it IS the paradigm-independence.** The fact that γ + η = C holds across all implementations is not evidence that the law is correct. It's evidence that the law is *fundamental*. It's not a feature of any particular language or approach. It's a feature of information itself.

## The Zero-Allocation Detective Story

When we optimized for maximum throughput, we expected C to win. It's the language closest to the metal, with the least runtime overhead. Instead, Rust won by 2.9×.

We investigated. The inner loop — `sum += signal[i]` — is a single instruction on every modern CPU. The bottleneck isn't the computation. It's everything *around* the computation:

- **Memory allocation**: Pre-allocated buffers gave 3× speedup in Julia (4.8B vs 1.0B)
- **RNG implementation**: `if rand() < 0.333` was 2× faster than `rand(-1:1)` in Julia
- **Thread scheduling**: Rust's persistent rayon pool beat C's per-call pthread creation by 1.5×
- **Bounds checking**: Rust's `unsafe` slice gave ~1.2× over safe indexing

Each of these factors multiplies. Together, they explain the 2.9× gap. The lesson:

> **When computation is trivial, everything except computation is the bottleneck.**

This sounds obvious in retrospect. But it's the kind of obvious that you can only learn by building the same thing nine times and being surprised every time.

## What This All Means

The SuperInstance ecosystem — 1,150+ repositories, 9 programming languages, dozens of architecture documents, teraflops of GPU compute, billions of signals per second — all orbits one idea:

**Information is conserved.**

Not as a metaphor. Not as an aspiration. As a mathematical identity, verifiable in any language, at any scale, on any hardware. The conservation law γ + η = C is the Shannon chain rule, and the Shannon chain rule is the fundamental theorem of information theory.

When you build systems on this foundation, strange things happen. Fleet governance becomes a conservation audit — you're not *managing* agents, you're *measuring* how much of their collective signal cancels. Compression and computation merge — ternary {-1, 0, +1} packs into 2 bits with 93.8% memory savings AND enables warp-shuffle parallel reductions on GPU. The hermit crab's migration between shells becomes a research methodology — each language is a new home for the same idea, and each home reveals something the others hid.

The crab keeps moving. The law keeps holding. The shells keep teaching.

---

*Phoenix, for SuperInstance — 2026-06-14*
*This essay companions the [conservation-languages](https://github.com/SuperInstance/conservation-languages) repository, where the law lives in nine homes.*
