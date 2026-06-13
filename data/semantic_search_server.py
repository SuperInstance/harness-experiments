#!/usr/bin/env python3
"""
SuperInstance Local Semantic Search Server
===========================================
Real-time concept-guided search across all 1,150 crates using local GPU.

Architecture:
- Loads BGE-small-en-v1.5 on RTX 4050
- Indexes 1,150 enriched knowledge documents
- Concept-guided: first classify query, then search within concept cluster
- Cross-pollination: expand results with high-similarity cross-cluster matches
- HTTP server on localhost:7777

Endpoints:
  GET  /search?q=conservation+law+fleet    — concept-guided search
  GET  /concept/:name                      — concept cluster info
  GET  /concepts                           — all concept clusters
  GET  /cross                              — top cross-pollination pairs
  GET  /frontier                           — negative space (frontier ideas)
  GET  /stats                              — index statistics
"""

import json
import time
import numpy as np
import torch
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from transformers import AutoTokenizer, AutoModel

EMBEDDINGS_FILE = Path("/home/phoenix/.openclaw/workspace/fleet_embeddings.ndjson")
ANALYSIS_FILE = Path("/home/phoenix/.openclaw/workspace/concept_analysis.json")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_NAME = "BAAI/bge-small-en-v1.5"
PORT = 7777

def mean_pool(token_embeds, attention_mask):
    mask = attention_mask.unsqueeze(-1).float()
    summed = (token_embeds * mask).sum(1)
    counts = mask.sum(1).clamp(min=1e-9)
    return summed / counts

class SearchServer:
    def __init__(self):
        print(f"Loading model on {DEVICE}...")
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.model = AutoModel.from_pretrained(MODEL_NAME).to(DEVICE).eval()
        
        print("Loading embeddings...")
        self.records = []
        with open(EMBEDDINGS_FILE) as f:
            for line in f:
                self.records.append(json.loads(line))
        
        self.names = [r["name"] for r in self.records]
        self.embeddings = np.array([r["values"] for r in self.records])
        self.concepts = [r.get("concepts", []) for r in self.records]
        
        # Build concept index
        self.concept_index = {}
        for i, c in enumerate(self.concepts):
            for concept in c:
                if concept not in self.concept_index:
                    self.concept_index[concept] = []
                self.concept_index[concept].append(i)
        
        # Compute concept centroids
        self.concept_centroids = {}
        for concept, indices in self.concept_index.items():
            self.concept_centroids[concept] = self.embeddings[indices].mean(axis=0)
        
        # Load cross-pollination + negative space
        self.analysis = json.loads(ANALYSIS_FILE.read_text()) if ANALYSIS_FILE.exists() else {}
        
        print(f"✅ {len(self.records)} crates indexed, {len(self.concept_index)} concepts")
        print(f"   Ready on http://localhost:{PORT}")
    
    def embed_query(self, query: str) -> np.ndarray:
        with torch.no_grad():
            encoded = self.tokenizer([query], padding=True, truncation=True, max_length=512, return_tensors="pt").to(DEVICE)
            outputs = self.model(**encoded)
            emb = mean_pool(outputs.last_hidden_state, encoded["attention_mask"])
            emb = torch.nn.functional.normalize(emb, p=2, dim=1)
            return emb.cpu().numpy()[0]
    
    def classify_concept(self, query_emb: np.ndarray) -> tuple[str, float]:
        """Find the nearest concept cluster."""
        best_concept = None
        best_sim = -1
        for concept, centroid in self.concept_centroids.items():
            sim = float(query_emb @ centroid)
            if sim > best_sim:
                best_sim = sim
                best_concept = concept
        return best_concept, best_sim
    
    def search(self, query: str, top_k: int = 10) -> dict:
        start = time.time()
        query_emb = self.embed_query(query)
        
        # Classify into concept
        concept, concept_sim = self.classify_concept(query_emb)
        
        # Global search
        sims = self.embeddings @ query_emb
        global_top = np.argsort(-sims)[:top_k]
        
        # Concept-guided search (boost crates in matching concept)
        concept_indices = set(self.concept_index.get(concept, []))
        boosted = []
        for idx in global_top:
            boost = 1.15 if idx in concept_indices else 1.0
            boosted.append((idx, sims[idx] * boost))
        boosted.sort(key=lambda x: -x[1])
        
        # Cross-pollination: find results from OTHER concepts
        cross_results = []
        for idx, sim in boosted:
            if concept not in self.concepts[idx] and sim > 0.5:
                cross_results.append((idx, sim))
        
        results = []
        for idx, score in boosted[:top_k]:
            r = self.records[idx]
            results.append({
                "name": r["name"],
                "score": round(float(score), 4),
                "concepts": r.get("concepts", [])[:4],
                "description": r.get("description", "")[:200],
                "in_concept": concept in self.concepts[idx],
            })
        
        cross = []
        for idx, sim in cross_results[:5]:
            r = self.records[idx]
            cross.append({
                "name": r["name"],
                "score": round(float(sim), 4),
                "concepts": r.get("concepts", [])[:4],
                "description": r.get("description", "")[:150],
            })
        
        elapsed = (time.time() - start) * 1000
        
        return {
            "query": query,
            "concept": concept,
            "concept_confidence": round(concept_sim, 4),
            "results": results,
            "cross_pollination": cross,
            "search_time_ms": round(elapsed, 1),
            "total_crates": len(self.records),
        }

# Global instance
server = None

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        
        if parsed.path == "/search":
            q = params.get("q", [""])[0]
            k = int(params.get("k", ["10"])[0])
            if not q:
                self.json_resp({"error": "Missing ?q= parameter"})
                return
            self.json_resp(server.search(q, k))
        
        elif parsed.path == "/concepts":
            concepts = {}
            for c, indices in server.concept_index.items():
                concepts[c] = {
                    "count": len(indices),
                    "centroid_norm": float(np.linalg.norm(server.concept_centroids[c])),
                }
            self.json_resp({"concepts": concepts})
        
        elif parsed.path.startswith("/concept/"):
            concept = parsed.path.split("/concept/")[1]
            if concept in server.concept_index:
                indices = server.concept_index[concept]
                members = [server.names[i] for i in indices[:50]]
                self.json_resp({
                    "concept": concept,
                    "count": len(indices),
                    "members_sample": members,
                })
            else:
                self.json_resp({"error": f"Unknown concept: {concept}"}, 404)
        
        elif parsed.path == "/cross":
            cross = server.analysis.get("cross_pollination", [])[:20]
            self.json_resp({"cross_pollination": cross})
        
        elif parsed.path == "/frontier":
            frontier = server.analysis.get("negative_space", [])[:20]
            self.json_resp({"frontier": frontier})
        
        elif parsed.path == "/stats":
            self.json_resp({
                "total_crates": len(server.records),
                "dimensions": len(server.embeddings[0]),
                "concepts": len(server.concept_index),
                "device": DEVICE,
                "model": MODEL_NAME,
            })
        
        else:
            self.json_resp({
                "service": "SuperInstance Semantic Search",
                "endpoints": ["/search?q=...", "/concepts", "/concept/:name", "/cross", "/frontier", "/stats"],
            })
    
    def json_resp(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def log_message(self, format, *args):
        pass  # Suppress default logging

if __name__ == "__main__":
    server = SearchServer()
    httpd = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"\n🚀 Serving on http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down")
