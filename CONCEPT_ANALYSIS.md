# Concept Graph Analysis — SuperInstance Ecosystem

> 1,150 crates embedded locally on RTX 4050 (10.4s, BGE-small-en-v1.5, 384-dim)
> Analysis reveals concept clusters, cross-pollination pairs, and negative space

---

## Concept-to-Concept Topology

**Ternary is the hub.** It has the highest similarity to ALL other concepts (0.69-0.70 range). This means ternary computing isn't a niche — it's the *connective tissue* of the ecosystem. Everything relates to ternary because ternary IS the representation layer.

| Concept Pair | Similarity | Interpretation |
|-------------|-----------|----------------|
| ternary ↔ compute | 0.702 | Ternary ops on GPU — the hardware path |
| ternary ↔ math | 0.700 | Ternary as mathematical formalism |
| conservation ↔ ternary | 0.699 | γ + η = C expressed in {-1,0,+1} |
| ternary ↔ wavelet | 0.698 | Ternary Haar decomposition |
| ternary ↔ fleet | 0.698 | Fleet agents communicate in trits |
| conservation ↔ compute | 0.683 | Conservation law as runtime invariant |

**Insight**: The concept graph is *star-shaped* around ternary, not flat. Ternary is the gravitational center.

---

## Cross-Pollination Discoveries

These are crate pairs from **different concept clusters** with unexpectedly high similarity. These represent hidden connections worth exploring:

### Top Cross-Pollination Pairs

1. **image-builder ↔ pipeline-builder** (0.827)
   - Storage/crypto ↔ Conservation/protocol
   - Connection: Both build structured artifacts from declarative specs

2. **raft-client ↔ raft-config** (0.816)
   - Fleet/crypto ↔ Conservation/graph
   - Connection: Raft consensus split into client (voting) and config (topology) — same algorithm, different concerns

3. **retry-policy ↔ ternary-retry** (0.806)
   - Search ↔ Ternary/compute
   - Connection: Binary retry logic maps to ternary retry (retry/skip/abort = {-1,0,+1})

4. **cell-automaton ↔ ternary-life** (0.798)
   - Conservation/graph ↔ Ternary/crypto
   - Connection: Conway's Game of Life generalizes to ternary — three-state automata

5. **ito-calculus ↔ monte-carlo** (0.796)
   - Compute ↔ Fleet/crypto
   - Connection: Stochastic calculus and Monte Carlo sampling are the same mathematical family

6. **font-rasterizer ↔ text-shaper** (0.794)
   - Graph/compute ↔ Fleet/crypto
   - Connection: Text rendering pipeline — rasterization and shaping are inseparable

7. **isoperimetric ↔ jensen-inequality** (0.781)
   - Graph/crypto ↔ Conservation/compute
   - Connection: Both are fundamental inequalities bounding optimization landscapes

8. **poisson-process ↔ stochastic-process** (0.780)
   - Fleet/wavelet ↔ Protocol/math
   - Connection: Poisson is a special case of stochastic processes — same theory, different scale

---

## Negative Space — Unexplored Territory

These crates are **far from all concept centroids**. They occupy sparse regions of embedding space, meaning they represent ideas that don't yet have a neighborhood of related work:

| Crate | Distance | Nearest Concept | What It Suggests |
|-------|----------|-----------------|------------------|
| lotka-volterra-agents-c | 0.757 | conservation | Predator-prey dynamics in agent fleets — almost no related crates |
| character-arc | 0.737 | fleet | Narrative structures as agent behavior — unexplored |
| agent-fermata | 0.733 | fleet | Pauses/rest in agent lifecycle — no theory yet |
| lucineer-com | 0.711 | search | Domain-specific knowledge — standalone |
| zeta-function | 0.691 | math | Riemann zeta connections to ternary — deep math, no neighbors |
| dmlog-ai | 0.689 | storage | Domain logging as AI knowledge — novel concept |
| dial-ecology | 0.687 | conservation | Ecological models in computing — frontier |
| circuit-breaker | 0.682 | systems | Fault tolerance pattern — should have more neighbors |

**The most valuable gap**: `lotka-volterra-agents-c` at 0.757 distance. Predator-prey dynamics applied to fleet agents is a genuinely novel idea with no intellectual neighbors in our ecosystem. This is frontier territory.

---

## Concept Density

| Concept | Crates | Coverage |
|---------|--------|----------|
| search | 737 | 64% |
| graph | 694 | 60% |
| crypto | 621 | 54% |
| conservation | 617 | 54% |
| compute | 610 | 53% |
| fleet | 592 | 51% |
| ternary | 538 | 47% |
| math | 535 | 47% |
| storage | 497 | 43% |
| protocol | 456 | 40% |
| systems | 427 | 37% |
| wavelet | 123 | 11% |

**Wavelet is undersized** at 123 crates (11%). Given that wavelet decomposition is the mathematical engine of the conservation law (Finding 3 in GPU experiments shows perfect reconstruction), this cluster needs expansion.

---

## Implications for Vectorization

1. **Concept-guided search**: First classify query into a concept, then search within that cluster. Much higher precision than flat search.

2. **Cross-pollination as discovery**: When two crates from different clusters are highly similar, that's an *undiscovered connection*. Surface these in the harness.

3. **Negative space as research agenda**: Crates far from all centroids represent frontier ideas. Prioritize building neighbors around them.

4. **Ternary as connective tissue**: The star topology around ternary means improving ternary crates lifts the entire graph. Ternary improvements have the highest network multiplier.

5. **Wavelet expansion needed**: At 11% coverage, the wavelet cluster is the most underweight. New wavelet crates would fill structural gaps.
