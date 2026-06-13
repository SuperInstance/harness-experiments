#!/usr/bin/env python3
"""
Local GPU Embedding Generator for Fleet Vector API
====================================================
Uses local RTX 4050 to generate BGE-small-en-v1.5 embeddings for all
enriched knowledge documents. 111x faster than CF Workers AI.

Outputs NDJSON ready for fleet-vector-api /ingest endpoint.
"""

import json
import time
import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModel

REPOS_DIR = Path("/home/phoenix/repos")
OUTPUT_FILE = Path("/home/phoenix/.openclaw/workspace/fleet_embeddings.ndjson")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_NAME = "BAAI/bge-small-en-v1.5"
BATCH_SIZE = 64

def mean_pool(token_embeds, attention_mask):
    mask = attention_mask.unsqueeze(-1).float()
    summed = (token_embeds * mask).sum(1)
    counts = mask.sum(1).clamp(min=1e-9)
    return summed / counts

def main():
    print(f"Device: {DEVICE}")
    print(f"Loading {MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME).to(DEVICE).eval()
    print("Model loaded.")
    
    # Load enriched knowledge docs
    data = json.loads(Path("/home/phoenix/.openclaw/workspace/enriched_knowledge.json").read_text())
    docs = data["documents"]
    print(f"Processing {len(docs)} knowledge documents...")
    
    # Batch encode
    all_embeddings = []
    texts = [d["knowledge_doc"][:2000] for d in docs]  # Truncate to 2000 chars
    
    start = time.time()
    with torch.no_grad():
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i+BATCH_SIZE]
            encoded = tokenizer(batch, padding=True, truncation=True, max_length=512, return_tensors="pt").to(DEVICE)
            outputs = model(**encoded)
            embeddings = mean_pool(outputs.last_hidden_state, encoded["attention_mask"])
            # L2 normalize
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            all_embeddings.extend(embeddings.cpu().numpy().tolist())
            
            done = min(i + BATCH_SIZE, len(texts))
            elapsed = time.time() - start
            rate = done / max(elapsed, 0.001)
            print(f"  {done}/{len(texts)} ({rate:.0f}/s)")
    
    # Write NDJSON for ingest
    with open(OUTPUT_FILE, "w") as f:
        for doc, emb in zip(docs, all_embeddings):
            record = {
                "name": doc["name"],
                "description": doc["description"][:300],
                "values": emb,
                "concepts": doc["concepts"],
                "readme_length": doc["readme_length"],
            }
            f.write(json.dumps(record) + "\n")
    
    elapsed = time.time() - start
    print(f"\n✅ {len(docs)} embeddings in {elapsed:.1f}s ({len(docs)/elapsed:.0f}/s)")
    print(f"📝 Output: {OUTPUT_FILE}")
    print(f"   Dimension: {len(all_embeddings[0])}")
    
    # Show sample similarities
    import numpy as np
    emb_arr = np.array(all_embeddings[:20])
    names = [d["name"] for d in docs[:20]]
    print("\n🔍 Sample similarity matrix (top matches):")
    sims = emb_arr @ emb_arr.T
    for i in range(min(10, len(names))):
        top = np.argsort(-sims[i])[1:4]
        matches = [f"{names[j]}({sims[i][j]:.2f})" for j in top]
        print(f"  {names[i]} → {', '.join(matches)}")

if __name__ == "__main__":
    main()
