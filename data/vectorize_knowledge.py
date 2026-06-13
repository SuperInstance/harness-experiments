#!/usr/bin/env python3
"""
SuperInstance Knowledge Vectorizer
===================================
Generates enriched embedding documents for each crate that capture not just
the crate's function, but its conceptual relationships, mathematical
foundations, and position in the conservation law taxonomy.

This produces "knowledge documents" — composite texts that embed the IDEA,
not just the artifact. When vectorized, these create a semantic graph where
searching for "cancellation effect" finds fleet coordination, where looking
for "optimal radix" finds ternary computing, and where "energy preservation"
finds both the conservation law and the wavelet decomposition.
"""

import os
import json
import hashlib
import requests
from pathlib import Path

REPOS_DIR = Path("/home/phoenix/repos")
OUTPUT_FILE = Path("/home/phoenix/.openclaw/workspace/enriched_knowledge.json")

# Conceptual tags that map crates to IDEA clusters
CONCEPT_CLUSTERS = {
    "conservation": ["conservation", "gamma", "eta", "energy", "balance", "invariant", "preservation"],
    "ternary": ["ternary", "trit", "trinary", "base-3", "radix", "balanced", "{-1,0,+1}"],
    "fleet": ["fleet", "agent", "coordination", "dispatch", "orchestrat", "multi-agent", "swarm"],
    "wavelet": ["wavelet", "haar", "decompose", "frequency", "spectral", "filter bank"],
    "graph": ["graph", "tree", "node", "edge", "vertex", "topolog", "mesh", "network"],
    "crypto": ["crypto", "hash", "cipher", "encrypt", "key", "signature", "hmac", "pbkdf"],
    "compute": ["gpu", "cuda", "parallel", "shader", "kernel", "wgpu", "compute"],
    "storage": ["store", "database", "kv", "cache", "persist", "disk", "index"],
    "protocol": ["protocol", "wire", "packet", "frame", "codec", "encode", "decode", "serialize"],
    "math": ["matrix", "vector", "tensor", "linear", "algebra", "eigen", "fourier", "transform"],
    "systems": ["kernel", "syscall", "driver", "interrupt", "memory", "alloc", "schedulers"],
    "search": ["search", "query", "index", "rank", "score", "match", "embedding", "vector"],
}

def classify_concepts(name: str, readme: str) -> list[str]:
    """Tag a crate with concept clusters based on name + README content."""
    text = (name + " " + readme[:4000]).lower()
    tags = []
    for cluster, keywords in CONCEPT_CLUSTERS.items():
        if any(kw in text for kw in keywords):
            tags.append(cluster)
    return tags or ["misc"]

def build_knowledge_doc(name: str, readme: str, cargo: str = "") -> str:
    """
    Build an enriched knowledge document for embedding.
    This is NOT the README — it's a composite that captures the IDEA.
    """
    concepts = classify_concepts(name, readme)
    
    # Extract first paragraph (definition)
    lines = readme.split("\n")
    definition = ""
    for i, line in enumerate(lines):
        if line.strip() and not line.startswith("#") and not line.startswith("!["):
            definition = line.strip()
            break
    
    # Extract math references
    math_refs = []
    for line in lines:
        if "$$" in line or "\\frac" in line or "O(" in line or "∑" in line or "γ" in line:
            math_refs.append(line.strip()[:200])
    
    # Extract section headers (structure)
    sections = [l.lstrip("# ").strip() for l in lines if l.startswith("#")]
    
    # Build composite embedding doc
    doc_parts = [
        f"CRATE: {name}",
        f"CONCEPTS: {', '.join(concepts)}",
        f"DEFINITION: {definition}",
        f"SECTIONS: {' | '.join(sections[:12])}",
    ]
    
    if math_refs:
        doc_parts.append(f"MATH: {' | '.join(math_refs[:5])}")
    
    # Architecture notes section (γ+η=C connection)
    in_arch = False
    arch_text = []
    for line in lines:
        if "architecture" in line.lower() and line.startswith("#"):
            in_arch = True
            continue
        if in_arch:
            if line.startswith("#"):
                break
            if line.strip():
                arch_text.append(line.strip())
    if arch_text:
        doc_parts.append(f"ARCHITECTURE: {' '.join(arch_text[:3])}")
    
    # Add cross-references based on concept clusters
    cross_refs = []
    for concept in concepts:
        cross_refs.append(f"relates-to:{concept}")
    doc_parts.append(f"CROSS_REFS: {' '.join(cross_refs)}")
    
    return "\n".join(doc_parts)

def main():
    """Process all repos and generate enriched knowledge documents."""
    results = []
    stats = {"total": 0, "with_readme": 0, "enriched": 0}
    
    for repo_dir in sorted(REPOS_DIR.iterdir()):
        if not repo_dir.is_dir() or not (repo_dir / ".git").exists():
            continue
        
        stats["total"] += 1
        name = repo_dir.name
        readme_path = repo_dir / "README.md"
        
        if not readme_path.exists():
            continue
        
        readme = readme_path.read_text(errors="replace")
        stats["with_readme"] += 1
        
        cargo_path = repo_dir / "Cargo.toml"
        cargo = cargo_path.read_text(errors="replace") if cargo_path.exists() else ""
        
        # Build enriched doc
        doc = build_knowledge_doc(name, readme, cargo)
        concepts = classify_concepts(name, readme)
        
        results.append({
            "name": name,
            "description": doc[:500],  # Short description for metadata
            "readme_length": len(readme),
            "concepts": concepts,
            "knowledge_doc": doc,
        })
        stats["enriched"] += 1
    
    # Write output
    OUTPUT_FILE.write_text(json.dumps({
        "stats": stats,
        "documents": results,
    }, indent=2))
    
    print(f"✅ Processed {stats['total']} repos")
    print(f"   With README: {stats['with_readme']}")
    print(f"   Enriched: {stats['enriched']}")
    
    # Concept distribution
    concept_counts = {}
    for r in results:
        for c in r["concepts"]:
            concept_counts[c] = concept_counts.get(c, 0) + 1
    
    print("\n📊 Concept Distribution:")
    for concept, count in sorted(concept_counts.items(), key=lambda x: -x[1]):
        print(f"   {concept}: {count} crates")
    
    print(f"\n📝 Output: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
