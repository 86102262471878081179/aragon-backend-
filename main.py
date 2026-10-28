#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YGGDRASIL_OS :: B6-SECURE-API (v2.0.1)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict
import uvicorn, os, hashlib, time, io, csv, httpx, logging, asyncio
from google import genai

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("YGGDRASIL-API")

EXPECTED_SEAL = os.getenv("EXPECTED_SEAL", "Φ_SOVEREIGN_ROOT_SEAL_EX_TUNC")
MASTER_SEAL = os.getenv("MASTER_SEAL", "850b2ef003f53db90f704b16e54869fc6ba6265eae13aafde9046fe0e4d99dab")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
REGISTRY_URL = os.getenv("REGISTRY_URL", "https://raw.githubusercontent.com/86102262471878081179/aragon-backend-/main/aragon_registry_200.csv.md")

client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI(title="YGGDRASIL_OS Master API", version="2.0.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BOOK_REGISTRY: Dict[str, dict] = {}
WORM_LEDGER = {"last_hash": MASTER_SEAL, "count": 0}

async def load_registry():
    global BOOK_REGISTRY
    logger.info("Lade Entity-Registry aus GitHub...")
    try:
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            response = await http_client.get(REGISTRY_URL)
            response.raise_for_status()
            lines = [l for l in response.text.splitlines() if l.strip() and not l.startswith("#")]
            reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=';')
            for row in reader:
                BOOK_REGISTRY[row.get('ID', 'UNKNOWN')] = {
                    "name": row.get('Name', 'UNKNOWN'),
                    "ring": row.get('Kategorie/Ring', 'UNKNOWN'),
                    "talents": row.get('Talente', ''),
                    "modules": row.get('Module/Cores', '')
                }
            logger.info(f"[SYNCED] {len(BOOK_REGISTRY)} Entitäten geladen.")
    except Exception as e:
        logger.error(f"[CRITICAL] Registry-Sync fehlgeschlagen: {e}")

class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    auth_seal: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(load_registry())

@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {"status": "LIVE", "entities": len(BOOK_REGISTRY)}

@app.post("/prompt/check")
async def check_prompt(request: PromptRequest):
    start_ns = time.perf_counter_ns()
    
    if request.auth_seal != EXPECTED_SEAL:
        return {"status": "403_FORBIDDEN", "detail": "Invalid Seal"}
    
    prompt = request.prompt
    rag_context = ""
    for bid, data in BOOK_REGISTRY.items():
        if bid in prompt or data["name"].lower() in prompt.lower():
            rag_context += f"Entität {bid}: {data['name']}. {data['talents']}\n"
            
    ai_answer = "Keine KI-Antwort generiert."
    if client and rag_context:
        try:
            response = await client.aio.models.generate_content(
                model='gemini-2.0-flash',
                contents=f"Daten: {rag_context}\nFrage: {prompt}"
            )
            ai_answer = response.text
        except Exception as e:
            ai_answer = f"System-Fehler: {e}"

    timestamp = str(time.time())
    worm_hash = hashlib.sha3_512(f"{WORM_LEDGER['last_hash']}{prompt}{timestamp}".encode()).hexdigest()
    WORM_LEDGER["last_hash"] = worm_hash
    WORM_LEDGER["count"] += 1

    return {
        "status": "200_OK", 
        "ai_answer": ai_answer, 
        "worm": {"hash": worm_hash, "block": WORM_LEDGER["count"]}
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
