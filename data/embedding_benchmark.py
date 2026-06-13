#!/usr/bin/env python3
"""
Experiment 3 standalone: Local embeddings with raw transformers
"""
import torch
import time
import json

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {DEVICE}")

# Use transformers directly, skip sentence_transformers wrapper
from transformers import AutoTokenizer, AutoModel
import torch.nn.functional as F

MODEL_NAME = "BAAI/bge-small-en-v1.5"
print(f"Loading {MODEL_NAME}...")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME).to(DEVICE).eval()

def encode(texts, batch_size=32):
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        encoded = tokenizer(batch, padding=True, truncation=True, max_length=512, return_tensors="pt").to(DEVICE)
        with torch.no_grad():
            outputs = model(**encoded)
            # BGE uses mean pooling
            token_embeddings = outputs.last_hidden_state
            mask = encoded['attention_mask'].unsqueeze(-1).float()
            pooled = (token_embeddings * mask).sum(1) / mask.sum(1)
            pooled = F.normalize(pooled, p=2, dim=1)
            all_embeddings.append(pooled.cpu())
    return torch.cat(all_embeddings, dim=0)

test_texts = [
    "Ternary arithmetic logic unit for balanced ternary computation",
    "Conservation law based agent coordination protocol",
    "Fast Fourier transform implementation with windowing",
    "Merkle tree with async support for distributed systems",
    "Rate limiter using token bucket algorithm",
    "Bloom filter with optimal hashing for set membership",
    "R-tree spatial index for geographic queries",
    "Topological sort with cycle detection for DAG processing",
] * 12  # 96 texts

results = []
for batch_size in [1, 8, 16, 32, 64, 96]:
    texts = test_texts[:batch_size]
    
    # Warmup
    encode(texts[:4])
    torch.cuda.synchronize()
    
    start = time.perf_counter()
    for _ in range(10):
        emb = encode(texts)
    torch.cuda.synchronize()
    encode_time = (time.perf_counter() - start) / 10
    
    cf_estimated = 0.05 * batch_size  # 50ms per text via CF Workers AI
    throughput = batch_size / encode_time
    
    result = {
        "batch_size": batch_size,
        "local_ms": round(encode_time * 1000, 1),
        "local_throughput": round(throughput, 1),
        "cf_estimated_ms": round(cf_estimated * 1000, 1),
        "speedup_vs_cf": round(cf_estimated / encode_time, 1),
        "embedding_dim": emb.shape[1],
        "gpu_mem_mb": round(torch.cuda.memory_allocated() / 1e6, 1),
    }
    results.append(result)
    print(f"  batch={batch_size:>3}: local={result['local_ms']:.0f}ms ({result['local_throughput']:.0f} texts/s), CF~{result['cf_estimated_ms']:.0f}ms, speedup={result['speedup_vs_cf']}x")

with open("/home/phoenix/.openclaw/workspace/embedding_results.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"\n✅ Results saved. Dim={results[-1]['embedding_dim']}, peak throughput={max(r['local_throughput'] for r in results)} texts/s")
