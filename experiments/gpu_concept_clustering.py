#!/usr/bin/env python3
"""
GPU-Accelerated Ecosystem Concept Clustering
=============================================
Uses RTX 4050 to cluster all SuperInstance repos by semantic similarity,
revealing hidden cross-pollination opportunities and architecture patterns.

This is the "ideas, not just artifacts" vectorization layer.
"""

import torch
import torch.nn.functional as F
import numpy as np
import json
import time
from pathlib import Path
from collections import defaultdict

# ─── Config ──────────────────────────────────────────────────
EMBEDDING_DIM = 384
BATCH_SIZE = 512  # Process 512 repos at once on GPU
TOP_K_NEIGHBORS = 10
N_CLUSTERS = 15

def load_ecosystem_data():
    """Load repo names and descriptions from our vector index."""
    # Try to get data from our semantic search server
    import urllib.request
    
    try:
        # Get stats
        req = urllib.request.Request("http://localhost:7777/stats")
        with urllib.request.urlopen(req, timeout=5) as resp:
            stats = json.loads(resp.read())
        print(f"Index stats: {stats}")
    except:
        pass
    
    # Load from our enriched embeddings
    embed_file = Path("/home/phoenix/.openclaw/workspace/scripts/embeddings.npy")
    meta_file = Path("/home/phoenix/.openclaw/workspace/scripts/repo_names.json")
    
    # Try alternative locations
    alt_paths = [
        "/home/phoenix/.openclaw/workspace/experiments/ecosystem_embeddings.npy",
        "/home/phoenix/.openclaw/workspace/scripts/ecosystem_embeddings.npy",
    ]
    
    # Generate embeddings from repo names if precomputed not available
    print("Loading ecosystem data from repos directory...")
    repo_dir = Path("/home/phoenix/repos")
    repos = []
    for d in sorted(repo_dir.iterdir()):
        if d.is_dir() and (d / ".git").exists():
            # Read README for description
            readme = ""
            for rm in ["README.md", "readme.md"]:
                rm_path = d / rm
                if rm_path.exists():
                    readme = rm_path.read_text()[:500]
                    break
            repos.append({"name": d.name, "description": readme})
    
    print(f"Loaded {len(repos)} repos")
    return repos

def compute_embeddings_gpu(repos, model_name="BAAI/bge-small-en-v1.5"):
    """Compute embeddings using GPU."""
    from transformers import AutoTokenizer, AutoModel
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    if device.type == "cuda":
        props = torch.cuda.get_device_properties(0)
        print(f"GPU: {props.name}, {props.total_memory / 1e9:.1f}GB, {props.multi_processor_count} SMs")
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name).to(device).eval()
    
    texts = [f"{r['name']}: {r['description'][:200]}" for r in repos]
    all_embeddings = []
    
    t0 = time.time()
    with torch.no_grad():
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i+BATCH_SIZE]
            encoded = tokenizer(batch, padding=True, truncation=True, 
                              max_length=128, return_tensors="pt").to(device)
            
            outputs = model(**encoded)
            # Mean pooling
            attention_mask = encoded['attention_mask']
            token_embeddings = outputs.last_hidden_state
            input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
            embeddings = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
            embeddings = F.normalize(embeddings, p=2, dim=1)
            all_embeddings.append(embeddings.cpu().numpy())
    
    elapsed = time.time() - t0
    embeddings = np.vstack(all_embeddings)
    throughput = len(texts) / elapsed
    print(f"Embedded {len(texts)} repos in {elapsed:.2f}s ({throughput:.0f} repos/s)")
    
    return embeddings

def gpu_cosine_similarity_matrix(embeddings):
    """Compute full cosine similarity matrix on GPU."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    emb_tensor = torch.from_numpy(embeddings).to(device)
    n = emb_tensor.shape[0]
    
    print(f"Computing {n}×{n} similarity matrix on GPU...")
    t0 = time.time()
    
    # Batch computation to fit in GPU memory
    chunk_size = 256
    sim_matrix = np.zeros((n, n), dtype=np.float32)
    
    for i in range(0, n, chunk_size):
        i_end = min(i + chunk_size, n)
        chunk = emb_tensor[i:i_end]  # (chunk, dim)
        
        # Cosine similarity = dot product (already normalized)
        sims = torch.mm(chunk, emb_tensor.T)  # (chunk, n)
        sim_matrix[i:i_end] = sims.cpu().numpy()
    
    elapsed = time.time() - t0
    print(f"Similarity matrix: {elapsed:.3f}s ({n*n/elapsed/1e6:.1f}M pairs/s)")
    
    return sim_matrix

def cluster_repos_gpu(embeddings, n_clusters=N_CLUSTERS):
    """K-means clustering on GPU."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    emb_tensor = torch.from_numpy(embeddings).to(device)
    n, dim = emb_tensor.shape
    
    print(f"\nGPU K-means clustering (k={n_clusters})...")
    
    # Initialize centroids using k-means++
    torch.manual_seed(42)
    centroids = torch.zeros(n_clusters, dim, device=device)
    centroids[0] = emb_tensor[torch.randint(0, n, (1,))]
    
    for k in range(1, n_clusters):
        # Compute distances to nearest centroid
        dists = torch.cdist(emb_tensor, centroids[:k])  # (n, k)
        min_dists = dists.min(dim=1).values  # (n,)
        
        # Sample proportional to distance²
        probs = min_dists ** 2
        probs = probs / probs.sum()
        idx = torch.multinomial(probs, 1)
        centroids[k] = emb_tensor[idx]
    
    # K-means iterations
    labels = torch.zeros(n, dtype=torch.long, device=device)
    
    for iteration in range(100):
        # Assign points to nearest centroid
        dists = torch.cdist(emb_tensor, centroids)
        new_labels = dists.argmin(dim=1)
        
        if torch.equal(new_labels, labels):
            print(f"  Converged at iteration {iteration}")
            break
        
        labels = new_labels
        
        # Update centroids
        for k in range(n_clusters):
            mask = labels == k
            if mask.any():
                centroids[k] = emb_tensor[mask].mean(dim=0)
    
    return labels.cpu().numpy()

def find_cross_pollination(sim_matrix, repo_names, threshold=0.75):
    """Find unexpected high-similarity pairs (cross-pollination candidates)."""
    n = len(repo_names)
    pairs = []
    
    for i in range(n):
        for j in range(i+1, n):
            sim = sim_matrix[i, j]
            if sim > threshold:
                # Check if they share prefix (expected similarity)
                name_i = repo_names[i].split('-')[0]
                name_j = repo_names[j].split('-')[0]
                if name_i != name_j:  # Different prefix = unexpected
                    pairs.append((repo_names[i], repo_names[j], float(sim)))
    
    pairs.sort(key=lambda x: -x[2])
    return pairs

def analyze_clusters(labels, repo_names, embeddings):
    """Analyze cluster composition and find centroids."""
    clusters = defaultdict(list)
    for i, label in enumerate(labels):
        clusters[int(label)].append(repo_names[i])
    
    # Compute cluster centroids in GPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    emb_tensor = torch.from_numpy(embeddings).to(device)
    
    print(f"\n{'═' * 70}")
    print(f"  Ecosystem Concept Clusters ({len(clusters)} clusters)")
    print(f"{'═' * 70}")
    
    for cluster_id in sorted(clusters.keys()):
        members = clusters[cluster_id]
        
        # Get centroid
        indices = [i for i, l in enumerate(labels) if l == cluster_id]
        centroid = emb_tensor[indices].mean(dim=0)
        centroid_np = F.normalize(centroid.unsqueeze(0), p=2, dim=1).cpu().numpy()[0]
        
        # Find most central member
        member_embs = embeddings[indices]
        sims_to_centroid = member_embs @ centroid_np
        most_central_idx = np.argmax(sims_to_centroid)
        
        print(f"\n┌─ Cluster {cluster_id} ({len(members)} repos)")
        print(f"│  Center: {members[most_central_idx]}")
        
        # Show top 8 members
        shown = min(8, len(members))
        for name in members[:shown]:
            print(f"│  · {name}")
        if len(members) > shown:
            print(f"│  · ... and {len(members) - shown} more")
        print(f"└─")
    
    return clusters

def main():
    print("═" * 70)
    print("  GPU-Accelerated Ecosystem Concept Clustering")
    print("  SuperInstance Repository Network Analysis")
    print("═" * 70)
    print()
    
    # Check GPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        props = torch.cuda.get_device_properties(0)
        print(f"GPU: {props.name}")
        print(f"  SMs: {props.multi_processor_count}")
        print(f"  VRAM: {props.total_memory / 1e9:.1f}GB")
        print(f"  CUDA: {torch.version.cuda}")
    else:
        print("⚠ GPU not available, using CPU")
    
    # Load data
    repos = load_ecosystem_data()
    repo_names = [r["name"] for r in repos]
    
    # Compute embeddings
    embeddings = compute_embeddings_gpu(repos)
    
    # Similarity matrix
    sim_matrix = gpu_cosine_similarity_matrix(embeddings)
    
    # Clustering
    labels = cluster_repos_gpu(embeddings, n_clusters=N_CLUSTERS)
    clusters = analyze_clusters(labels, repo_names, embeddings)
    
    # Cross-pollination
    pairs = find_cross_pollination(sim_matrix, repo_names, threshold=0.7)
    print(f"\n{'═' * 70}")
    print(f"  Cross-Pollination Candidates ({len(pairs)} pairs > 0.70)")
    print(f"{'═' * 70}")
    for name_a, name_b, sim in pairs[:20]:
        print(f"  {sim:.3f}  {name_a} ↔ {name_b}")
    
    # Architecture patterns
    print(f"\n{'═' * 70}")
    print("  Architecture Pattern Detection")
    print(f"{'═' * 70}")
    
    # Count by prefix
    prefix_counts = defaultdict(int)
    for name in repo_names:
        prefix = name.split('-')[0]
        prefix_counts[prefix] += 1
    
    print("\n  Top ecosystem components:")
    for prefix, count in sorted(prefix_counts.items(), key=lambda x: -x[1])[:15]:
        bar = "█" * min(count, 50)
        print(f"    {prefix:20s} {count:4d} {bar}")
    
    # Save results
    results = {
        "n_repos": len(repos),
        "n_clusters": N_CLUSTERS,
        "clusters": {str(k): v for k, v in clusters.items()},
        "cross_pollination": [{"a": a, "b": b, "sim": s} for a, b, s in pairs[:50]],
    }
    
    output = Path("/home/phoenix/.openclaw/workspace/experiments/gpu_concept_analysis.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output}")
    
    print(f"\n{'═' * 70}")
    print("  Analysis Complete")
    print(f"{'═' * 70}")

if __name__ == "__main__":
    main()
