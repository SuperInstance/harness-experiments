#!/usr/bin/env python3
"""
Concept Graph Analyzer
======================
Computes concept centroids, cross-pollination pairs, and negative space
from the locally-generated enriched embeddings.
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict

EMBEDDINGS_FILE = Path("/home/phoenix/.openclaw/workspace/fleet_embeddings.ndjson")
OUTPUT_FILE = Path("/home/phoenix/.openclaw/workspace/concept_analysis.json")

CONCEPT_CLUSTERS = {
    "conservation": ["conservation", "gamma", "eta", "energy", "balance", "invariant", "preservation"],
    "ternary": ["ternary", "trit", "trinary", "base-3", "radix", "balanced"],
    "fleet": ["fleet", "agent", "coordination", "dispatch", "orchestrat", "multi-agent"],
    "wavelet": ["wavelet", "haar", "decompose", "frequency", "spectral"],
    "graph": ["graph", "tree", "node", "edge", "vertex", "topolog", "mesh"],
    "crypto": ["crypto", "hash", "cipher", "encrypt", "key", "signature", "hmac"],
    "compute": ["gpu", "cuda", "parallel", "shader", "kernel", "wgpu", "compute"],
    "storage": ["store", "database", "kv", "cache", "persist", "disk", "index"],
    "protocol": ["protocol", "wire", "packet", "frame", "codec", "serialize"],
    "math": ["matrix", "vector", "tensor", "linear", "algebra", "eigen", "fourier"],
    "systems": ["kernel", "syscall", "driver", "interrupt", "memory", "alloc"],
    "search": ["search", "query", "rank", "score", "match", "embedding", "vector"],
}

def main():
    # Load all embeddings
    records = []
    with open(EMBEDDINGS_FILE) as f:
        for line in f:
            records.append(json.loads(line))
    
    print(f"Loaded {len(records)} crate embeddings")
    
    names = [r["name"] for r in records]
    embeddings = np.array([r["values"] for r in records])
    concepts_per = [r.get("concepts", []) for r in records]
    
    # 1. Compute concept centroids
    concept_centroids = {}
    concept_members = {}
    for concept in CONCEPT_CLUSTERS:
        mask = [concept in c for c in concepts_per]
        if sum(mask) > 0:
            centroid = embeddings[mask].mean(axis=0)
            concept_centroids[concept] = centroid.tolist()
            concept_members[concept] = [names[i] for i, m in enumerate(mask) if m]
    
    # 2. Concept-to-concept similarity matrix
    concept_names = list(concept_centroids.keys())
    centroid_arr = np.array([concept_centroids[c] for c in concept_names])
    concept_sims = centroid_arr @ centroid_arr.T
    
    print("\n📊 Concept-to-Concept Similarity (top pairs):")
    pairs = []
    for i in range(len(concept_names)):
        for j in range(i+1, len(concept_names)):
            pairs.append((concept_names[i], concept_names[j], concept_sims[i][j]))
    pairs.sort(key=lambda x: -x[2])
    for a, b, sim in pairs[:15]:
        print(f"  {a} ↔ {b}: {sim:.3f}")
    
    # 3. Cross-pollination detection
    # Find crates that are in different concept clusters but have high similarity
    print("\n🔬 Cross-Pollination Pairs (different cluster, high similarity):")
    cross_pairs = []
    sim_matrix = embeddings @ embeddings.T
    
    for i in range(len(names)):
        # Get top 5 similar crates
        top_idx = np.argsort(-sim_matrix[i])[1:6]
        for j in top_idx:
            if i >= j:
                continue
            # Check if they share any concept
            shared = set(concepts_per[i]) & set(concepts_per[j])
            if not shared and sim_matrix[i][j] > 0.75:
                cross_pairs.append((names[i], names[j], float(sim_matrix[i][j]), 
                                    concepts_per[i], concepts_per[j]))
    
    cross_pairs.sort(key=lambda x: -x[2])
    for a, b, sim, ca, cb in cross_pairs[:20]:
        print(f"  {a} ({','.join(ca[:2])}) ↔ {b} ({','.join(cb[:2])}): {sim:.3f}")
    
    # 4. Negative space detection
    # Find the centroid of all embeddings, then find crates far from any concept centroid
    global_centroid = embeddings.mean(axis=0)
    
    # For each crate, compute distance to nearest concept centroid
    min_distances = []
    for i in range(len(names)):
        dists = [np.linalg.norm(embeddings[i] - centroid_arr[j]) for j in range(len(concept_names))]
        min_dist = min(dists)
        nearest_concept = concept_names[np.argmin(dists)]
        min_distances.append((names[i], float(min_dist), nearest_concept, concepts_per[i]))
    
    min_distances.sort(key=lambda x: -x[1])
    print("\n🕳️ Negative Space (far from all concept centroids — unexplored territory):")
    for name, dist, nearest, concepts in min_distances[:15]:
        print(f"  {name}: dist={dist:.3f} (nearest: {nearest}, concepts: {','.join(concepts[:3])})")
    
    # 5. Concept density map
    print("\n📈 Concept Density:")
    for concept in concept_names:
        n = len(concept_members[concept])
        print(f"  {concept}: {n} crates")
    
    # Save full analysis
    output = {
        "concept_centroids": concept_centroids,
        "concept_members": concept_members,
        "concept_similarities": {
            f"{concept_names[i]}_{concept_names[j]}": float(concept_sims[i][j])
            for i in range(len(concept_names))
            for j in range(i+1, len(concept_names))
        },
        "cross_pollination": [
            {"a": a, "b": b, "similarity": sim, "concepts_a": ca, "concepts_b": cb}
            for a, b, sim, ca, cb in cross_pairs[:50]
        ],
        "negative_space": [
            {"name": n, "distance": d, "nearest_concept": nc, "concepts": c}
            for n, d, nc, c in min_distances[:50]
        ],
    }
    
    OUTPUT_FILE.write_text(json.dumps(output, indent=2))
    print(f"\n✅ Full analysis: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
