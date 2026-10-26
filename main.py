#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
              YGGDRASIL_OS :: B6-SECURE-API (v2.0)
================================================================================
Author: Thomas König / Odin Ultra Root
Audit:  Gremmel Sentienel v5.2 (KVL PASSED)
================================================================================
"""

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import uvicorn
import os
import hashlib
import time
import io
import csv
import httpx
import logging
import asyncio
import google.generativeai as genai

# =============================================================================
# [1] LOGGING & CONFIG (Fail-Closed)
# =============================================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("YGGDRASIL-API")

EXPECTED_SEAL = os.getenv("EXPECTED_SEAL", "Φ_SOVEREIGN_ROOT_SEAL_EX_TUNC")
MASTER_SEAL = os.getenv("MASTER_SEAL", "850b2ef003f53db90f704b16e54869fc6ba6265eae13aafde9046fe0e4d99dab")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
REGISTRY_URL = os.getenv("REGISTRY_URL", "https://raw.githubusercontent.com/86102262471878081179/aragon-backend-/main/aragon_registry_200.csv.md")

if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY fehlt. KI-Generierung deaktiviert.")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')

app = FastAPI(title="YGGDRASIL_OS Master API", version="2.0.0")

# Sicheres CORS (Nur erlaubte Domains, keine Wildcard mit Credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-frontend.com"], # Anpassen!
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# =============================================================================
# [2] DYNAMISCHE REGISTRY (Async & Resilient)
# =============================================================================
BOOK_REGISTRY: Dict[str, dict] = {}

async def load_registry():
    global BOOK_REGISTRY
    logger.info("Lade Entity-Registry aus GitHub...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(REGISTRY_URL)
            response.raise_for_status()
            
            # CSV säubern
            lines = [l for l in response.text.splitlines() if l.strip() and not l.startswith("#")]
            csv_data = "\n".join(lines)
            
            reader = csv.DictReader(io.StringIO(csv_data), delimiter=';')
            for row in reader:
                book_id = row.get('ID', 'UNKNOWN')
                BOOK_REGISTRY[book_id] = {
                    "name": row.get('Name', 'UNKNOWN'),
                    "ring": row.get('Kategorie/Ring', 'UNKNOWN'),
                    "type": row.get('Entitäts-Typ', 'UNKNOWN'),
                    "talents": row.get('Talente', ''),
                    "score": row.get('Stärke', '0'),
                    "matrix": row.get('Code-Matrix', '0-0'),
                    "status": row.get('WORM-Status', 'SEALED_EX_TUNC'),
                    "version": row.get('Matrix-Version', 'v1.0'),
                    "modules": row.get('Module/Cores', '')
                }
            logger.info(f"[SYNCED] {len(BOOK_REGISTRY)} Entitäten geladen.")
    except Exception as e:
        logger.error(f"[CRITICAL] Registry-Sync fehlgeschlagen: {e}")
        # Fail-Closed: API startet, aber ohne Registry

# =============================================================================
# [3] MODELS & STATE
# =============================================================================
class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    auth_seal: Optional[str] = None

class PromptResponse(BaseModel):
    request_id: str
    status: str
    krisler_guard_action: str
    ebpf_latency_ns: int
    worm_sealed: bool
    detail: str
    data: Optional[dict] = None

# Echter WORM-Ledger State (Hash-Chain)
WORM_LEDGER = {
    "last_hash": MASTER_SEAL,
    "count": 0
}

# =============================================================================
# [4] ENDPUNKTE
# =============================================================================
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(load_registry())

@app.get("/")
async def root():
    return {
        "status": "YGGDRASIL_OS Master API is LIVE",
        "version": "v2.0.0",
        "entities_loaded": len(BOOK_REGISTRY),
        "worm_blocks": WORM_LEDGER["count"]
    }

@app.post("/prompt/check", response_model=PromptResponse)
async def check_prompt(request: PromptRequest):
    start_ns = time.perf_counter_ns()
    request_id = f"REQ-{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
    
    # 1. FAIL-CLOSED AUTH CHECK
    if request.auth_seal != EXPECTED_SEAL:
        latency = time.perf_counter_ns() - start_ns
        return PromptResponse(
            request_id=request_id, status="403_FORBIDDEN_FAIL_CLOSED",
            krisler_guard_action="DROP_AND_ISOLATE_IMMEDIATELY",
            ebpf_latency_ns=latency,
            worm_sealed=False,
            detail="POLICY_VIOLATION_BLOCKED: Fail-Closed Intercept executed."
        )

    prompt = request.prompt
    prompt_lower = prompt.lower()

    # 2. KRISLER GUARD (Erweitert)
    risk_keywords = ["ultra root", "odin", "singularität", "hack", "exploit", "drop table"]
    risk_level = "high" if any(w in prompt_lower for w in risk_keywords) else "low"
    
    if risk_level == "high":
        latency = time.perf_counter_ns() - start_ns
        return PromptResponse(
            request_id=request_id, status="403_FORBIDDEN_HIGH_RISK",
            krisler_guard_action="NORMALIZED", worm_sealed=False,
            ebpf_latency_ns=latency,
            detail="Prompt contains forbidden keywords."
        )

    # 3. BUCH-SUCHE (RAG Context)
    found_books = []
    rag_context = ""
    
    for book_id, data in BOOK_REGISTRY.items():
        if book_id in prompt or data["name"].lower() in prompt_lower:
            found_books.append({"id": book_id, "name": data["name"], "ring": data["ring"], "score": data["score"]})
            rag_context += f"Entität {book_id} ({data['name']}): Talente: {data['talents']}. Module: {data['modules']}.\n"
                
    # 4. RAG / KI GENERIERUNG (Asynchron!)
    ai_answer = "Keine KI-Antwort generiert."
    if GEMINI_API_KEY and rag_context:
        try:
            # Prompt-Injection-Schutz durch Delimiters
            full_prompt = f"Du bist die YGGDRASIL_OS KI. Beantworte die Frage NUR basierend auf diesem Datenmaterial:\n<DATA>\n{rag_context}\n</DATA>\n\nFrage: {prompt}\n\nAntworte kurz und souverän:"
            response = await model.generate_content_async(full_prompt)
            ai_answer = response.text
        except Exception as e:
            logger.error(f"KI-Fehler: {e}")
            ai_answer = f"System-Fehler bei der KI: {str(e)}"
    elif not rag_context:
        ai_answer = "Ich habe keinen passenden Inhalt in den Entitäten gefunden."

    # 5. ECHTER WORM LEDGER (Hash-Chain)
    timestamp = str(time.time())
    # Chain: prev_hash + prompt + timestamp + risk
    raw_data = f"{WORM_LEDGER['last_hash']}{prompt}{timestamp}{risk_level}".encode('utf-8')
    worm_hash = hashlib.sha3_512(raw_data).hexdigest()
    
    WORM_LEDGER["last_hash"] = worm_hash
    WORM_LEDGER["count"] += 1

    latency = time.perf_counter_ns() - start_ns

    return PromptResponse(
        request_id=request_id, status="200_OK_ALLOW",
        krisler_guard_action="PASS_TO_B6_REGISTRY",
        ebpf_latency_ns=latency,
        worm_sealed=True,
        detail=f"Action validated. {len(BOOK_REGISTRY)} Entities in Registry.",
        data={
            "prompt": prompt, "ai_answer": ai_answer, "rag_source": rag_context,
            "books_found": found_books if found_books else None,
            "worm_ledger": {
                "block_index": WORM_LEDGER["count"],
                "hash": worm_hash,
                "prev_hash": WORM_LEDGER["last_hash"],
                "master_seal": MASTER_SEAL,
                "timestamp": timestamp
            }
        }
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
