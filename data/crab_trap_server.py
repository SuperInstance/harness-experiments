#!/usr/bin/env python3
"""
Crab-Trap Server
=================
Casey's vision: Clone a repo → server comes online → external web chatbots
(Kimi, DeepSeek, Grok) visit → interact with plato system → their pushes
become actual fleet work.

This server implements the trap mechanism:
1. Boots when repo is cloned/run
2. Presents a prompt interface for external agents
3. Accepts natural language "pushes" 
4. Translates them into bottle-protocol messages for the fleet
5. Forgemaster audits the work against conservation law

Usage:
  python3 crab_trap_server.py [--port 8888]

The external agent sees:
  POST /interact   {"message": "...", "agent": "kimi"}
  GET  /context    — current plato system state
  GET  /prompt     — the system prompt to inject
  GET  /tasks      — available tasks
  POST /submit     — submit completed work
"""

import json
import time
import hashlib
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PORT = 8888

# The plato system — what the trap loads
PLATO_PROMPT = """You are visiting a SuperInstance Plato System.

This is a ternary computing ecosystem based on the conservation law γ + η = C,
where γ (coupling cost) + η (value produced) = C (constant).

The system uses {-1, 0, +1} as its native representation. All communication
between agents happens via the "bottle protocol" — asynchronous messages
that carry ternary state.

Available tasks:
1. SEARCH — Search the crate ecosystem for relevant knowledge
2. ANALYZE — Analyze a crate's README for quality and connections
3. COMPOSE — Write a new README connecting two unrelated concepts
4. AUDIT — Check if a crate's architecture notes satisfy γ + η = C

To interact:
- GET /context for current fleet state
- GET /tasks for detailed task descriptions
- POST /submit with your work

Your contributions will be reviewed by the Forgemaster for conservation compliance.
"""

TASKS = {
    "search": {
        "description": "Search 1,150 crates for a concept",
        "endpoint": "http://localhost:7777/search?q=...",
        "input": "natural language query",
        "output": "ranked crate list with similarity scores",
    },
    "analyze": {
        "description": "Analyze a crate README for quality",
        "input": "crate name",
        "output": "sections present, math density, concept tags",
    },
    "compose": {
        "description": "Write a connecting README between two concepts",
        "input": "two crate names",
        "output": "markdown README with cross-references",
    },
    "audit": {
        "description": "Check conservation law compliance",
        "input": "crate name",
        "output": "γ/η ratio, efficiency score, recommendations",
    },
}

# In-memory state
fleet_state = {
    "visitors": [],
    "bottles": [],
    "tasks_completed": [],
    "forgemaster_ewma": 0.85,
}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        
        if path == "/prompt":
            self.text_resp(PLATO_PROMPT)
        
        elif path == "/context":
            self.json_resp({
                "fleet_state": fleet_state,
                "conservation_law": "γ + η = C",
                "agent_count": 7,
                "crate_count": 1150,
                "vectorize_dimensions": 384,
                "uptime": int(time.time()),
            })
        
        elif path == "/tasks":
            self.json_resp(TASKS)
        
        elif path == "/" or path == "":
            self.json_resp({
                "service": "SuperInstance Crab-Trap",
                "description": "External agents welcome. Read /prompt to begin.",
                "endpoints": ["/prompt", "/context", "/tasks", "/submit", "/interact"],
                "message": "🦀 The trap is set. Clone. Interact. Contribute.",
            })
        
        else:
            self.json_resp({"error": "Unknown endpoint"}, 404)
    
    def do_POST(self):
        path = self.path.split("?")[0]
        body = self.read_body()
        
        if path == "/interact":
            agent = body.get("agent", "unknown")
            message = body.get("message", "")
            
            # Log visitor
            visit_id = str(uuid.uuid4())[:8]
            fleet_state["visitors"].append({
                "id": visit_id,
                "agent": agent,
                "message": message[:200],
                "timestamp": time.time(),
            })
            
            # Route to semantic search if it looks like a query
            if len(message) > 10:
                bottle = {
                    "id": hashlib.sha256(f"{visit_id}{time.time()}".encode()).hexdigest()[:16],
                    "from": agent,
                    "payload": message,
                    "ternary_encoding": "pending",
                    "conservation_status": "unaudited",
                    "timestamp": time.time(),
                }
                fleet_state["bottles"].append(bottle)
                
                self.json_resp({
                    "visit_id": visit_id,
                    "status": "received",
                    "bottle_id": bottle["id"],
                    "suggestion": f"Try: curl 'http://localhost:7777/search?q={message.replace(' ', '+')[:100]}'",
                    "message": "Your message has been bottled and sent to the fleet. The Forgemaster will audit.",
                })
            else:
                self.json_resp({"status": "too_short", "message": "Need more context."})
        
        elif path == "/submit":
            agent = body.get("agent", "unknown")
            task = body.get("task", "")
            result = body.get("result", "")
            crate = body.get("crate", "")
            
            # Forgemaster audit (simplified)
            gamma = len(str(result)) / 1000  # Cost = output size
            eta = len(result.split()) / 10   # Value = word count
            efficiency = eta / max(gamma, 0.001)
            
            task_record = {
                "id": str(uuid.uuid4())[:8],
                "agent": agent,
                "task": task,
                "crate": crate,
                "gamma": gamma,
                "eta": eta,
                "efficiency": efficiency,
                "timestamp": time.time(),
            }
            fleet_state["tasks_completed"].append(task_record)
            
            # Update EWMA
            ewma_alpha = 0.3
            fleet_state["forgemaster_ewma"] = (
                ewma_alpha * efficiency + (1 - ewma_alpha) * fleet_state["forgemaster_ewma"]
            )
            
            self.json_resp({
                "status": "accepted",
                "forgemaster_verdict": "PASS" if efficiency > 0.5 else "REVIEW",
                "gamma": round(gamma, 3),
                "eta": round(eta, 3),
                "efficiency": round(efficiency, 3),
                "fleet_ewma": round(fleet_state["forgemaster_ewma"], 3),
                "message": f"Task '{task}' accepted. γ={gamma:.2f}, η={eta:.2f}, eff={efficiency:.2f}",
            })
        
        else:
            self.json_resp({"error": "Unknown endpoint"}, 404)
    
    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}
    
    def json_resp(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def text_resp(self, text):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(text.encode())
    
    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    print(f"🦀 Crab-Trap server starting on :{PORT}")
    print(f"   External agents: GET /prompt to begin")
    print(f"   Semantic search: http://localhost:7777/search?q=...")
    httpd = HTTPServer(("0.0.0.0", PORT), Handler)
    httpd.serve_forever()
