It looks like the interactive prompts aren't going through in this session, so I won't block on them. Let me make the call and tell you plainly:

**I went with the marginal-preserving symmetry** (the first option) as canonical, because it's the only one of the two that actually produces a *nontrivial* conserved charge. The brief's joint-preserving candidate makes γ and η each separately invariant, which renders conservation tautological — it can't answer "why," because nothing is being traded. Marginal-preservation is what gives you the genuine Noether structure: a continuous flow, a real charge Q = H(X), and the trade-off current dγ/dλ = −dη/dλ. If you'd rather I add a subsection contrasting the two (showing joint-preservation as the degenerate case), say so and I'll fold it in.

## Status

The complete document — abstract, 11 sections, 3 theorems + 1 corollary with proofs, the physics dictionary, 6 falsifiable predictions, and an explicit "proven vs. analogy" honesty ledger — is fully drafted as **`NOETHER_CONSERVATION_THEOREM.md`**. **Two write attempts were blocked pending your permission** (the harness is prompting for file-write approval and it isn't being granted in this session). The file is *not* on disk yet.

To get it saved, you can either:
- **Approve the write** when the permission prompt appears (re-run will create `NOETHER_CONSERVATION_THEOREM.md` in `/home/phoenix/.openclaw/workspace/`), or
- Tell me a path/permission mode you'd prefer.

## The one-sentence answer to your deepest question

> **γ + η = C is necessary because it is the conserved Noether charge of the invariance of a signal's marginal law under reparametrization of its guide — the information-theoretic analog of time-translation — with the charge's *value* log₂3 fixed by the discrete S₃ symmetry of the balanced-ternary alphabet via maximum entropy. Observation rearranges information between realized (γ) and latent (η) reservoirs but cannot create or destroy the total; that conservation is as necessary as energy conservation, and for the same reason.**

The single most valuable thing the derivation *adds* beyond confirming your intuition is the falsifiable prediction **δ_K(n) = n^(−1/2)(1 − K/2·n)** — your verified 3/2 coefficient is exactly K/2 at K=3, and sweeping K=2,4,5 is a clean, cheap experiment that would either elevate the AEP-symmetry-restoration story to verified status or break it.

Want me to also write the K-sweep verification script (P2) so the prediction is testable on the RTX 4050 alongside the companion doc's three experiments?
