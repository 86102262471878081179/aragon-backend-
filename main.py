#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
 YGGDRASIL_OS :: BLUE CORE BACKEND (v26.0.0)
═══════════════════════════════════════════════════════════════════════════════
 Integration von: Wusulum, Foucault, Advocatus Diaboli, Brummel-Universum,
 XJustiz, WAL-Logger und Live-WebSockets für das Streamlit-Cockpit.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from contextlib import asynccontextmanager, suppress
import uvicorn, os, io, csv, time, hashlib, hmac, logging, asyncio, json, random
from collections import deque
import xml.etree.ElementTree as ET

try:
    import httpx
except ImportError:
    httpx = None
try:
    from google import genai
except ImportError:
    genai = None

# ═══════════════════════════════════════════════════════════════════════════════
# 1. KONFIGURATION & LOGGING
# ═══════════════════════════════════════════════════════════════════════════════
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BLUE-CORE-API")

EXPECTED_SEAL = os.getenv("EXPECTED_SEAL", "Φ_SOVEREIGN_ROOT_SEAL_EX_TUNC")
MASTER_SEAL = os.getenv("MASTER_SEAL", "850b2ef003f53db90f704b16e54869fc6ba6265eae13aafde9046fe0e4d99dab")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
REGISTRY_URL = os.getenv("REGISTRY_URL", "https://raw.githubusercontent.com/86102262471878081179/aragon-backend-/main/aragon_registry_200.csv.md")

client = genai.Client(api_key=GEMINI_API_KEY) if (GEMINI_API_KEY and genai) else None

BOOK_REGISTRY: Dict[str, dict] = {}
WORM_LEDGER = {"last_hash": MASTER_SEAL, "count": 0, "started_at": time.time()}
WORM_RING = deque(maxlen=50)
_LEDGER_LOCK = asyncio.Lock()

# ═══════════════════════════════════════════════════════════════════════════════
# 2. L.S.S. NEURO-CORE (Deine Module, gehartet)
# ═══════════════════════════════════════════════════════════════════════════════
def _h(data: str, size: int = 16) -> str:
    return hashlib.blake2b(data.encode(), digest_size=size).hexdigest()

class WusulumCore:
    def __init__(self):
        self.state = "GENESIS_WAHRHEIT"
        self.memory = []
        self.entropy = 0.0
    def cycle(self):
        self.entropy = min(5.0, self.entropy + 0.1)
        attn = random.random()
        raw = f"TOKEN_{_h(f'{attn}:{self.state}', 4)}"
        self.state = raw[:20]
        self.memory.append(self.state)
        return {"state": self.state, "entropy": self.entropy}

class FoucaultPanoptikum:
    def invert(self, token: str):
        is_rebellious = int(_h(token, 2), 16) > 32767
        return f"SYS_CONFORM_{_h(token, 3)}" if is_rebellious else token

class BrummelGrummelUniverse:
    def __init__(self):
        self.phase = 0
    def oscillate(self):
        self.phase = (self.phase + 1) % 18
        return 9 - abs(self.phase - 9) # Dreieckswelle 0-9-0

class PolyvagalRegulator:
    def __init__(self):
        self.stress = 0.0
        self.state = "VENTRAL_VAGAL"
    def update(self, threat: float):
        self.stress = max(0.0, self.stress - 0.08) # Decay
        self.stress = min(1.0, self.stress + threat)
        if self.stress < 0.4: self.state = "VENTRAL_VAGAL"
        elif self.stress < 0.8: self.state = "SYMPATHIKUS"
        else: self.state = "DORSAL_VAGAL"
        return self.state

# Instanzen
wusulum = WusulumCore()
foucault = FoucaultPanoptikum()
brummel = BrummelGrummelUniverse()
polyvagal = PolyvagalRegulator()

# ═══════════════════════════════════════════════════════════════════════════════
# 3. HILFSFUNKTIONEN & LIFESPAN
# ═══════════════════════════════════════════════════════════════════════════════
def _verify_seal(provided: Optional[str]) -> bool:
    if not provided: return False
    return hmac.compare_digest(provided, EXPECTED_SEAL)

async def load_registry():
    global BOOK_REGISTRY
    if not httpx: return
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(REGISTRY_URL)
            r.raise_for_status()
            lines = [l for l in r.text.splitlines() if l.strip() and not l.startswith("#")]
            reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=';')
            BOOK_REGISTRY = {row.get('ID', 'UNK'): {"name": row.get('Name', 'UNK')} for row in reader}
            logger.info(f"[SYNCED] {len(BOOK_REGISTRY)} Entitäten geladen.")
    except Exception as e:
        logger.error(f"Registry-Sync fehlgeschlagen: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(load_registry())
    yield
    task.cancel()

app = FastAPI(title="Blue Core Matrix", version="26.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ═══════════════════════════════════════════════════════════════════════════════
# 4. API SCHEMAS & ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    auth_seal: Optional[str] = None

class ApexRequest(BaseModel):
    message: str
    is_threat: bool = False
    auth_seal: Optional[str] = None

@app.get("/")
async def root():
    return {"status": "BLUE_CORE_LIVE", "entities": len(BOOK_REGISTRY), "worm": WORM_LEDGER["count"]}

@app.post("/api/v1/apex/process")
async def apex_process(req: ApexRequest):
    if not _verify_seal(req.auth_seal): return {"status": "403_FORBIDDEN"}
    
    threat = 0.8 if req.is_threat else 0.2
    bio_state = polyvagal.update(threat)
    wus = wusulum.cycle()
    inv = foucault.invert(wus["state"])
    osc = brummel.oscillate()
    
    # WORM Update
    async with _LEDGER_LOCK:
        WORM_LEDGER["count"] += 1
        h = hashlib.sha3_512(f"{WORM_LEDGER['last_hash']}{req.message}".encode()).hexdigest()
        WORM_LEDGER["last_hash"] = h
        WORM_RING.append({"block": WORM_LEDGER["count"], "hash": h, "state": inv})

    return {
        "status": "PROCESSED",
        "bio_state": bio_state,
        "wusulum": wus,
        "foucault_inversion": inv,
        "brummel_oscillation": osc,
        "worm_block": WORM_LEDGER["count"]
    }

@app.post("/prompt/check")
async def check_prompt(request: PromptRequest):
    if not _verify_seal(request.auth_seal): return {"status": "403_FORBIDDEN"}
    rag = "".join([f"ID {k}: {v['name']}\n" for k, v in BOOK_REGISTRY.items() if k in request.prompt or v['name'].lower() in request.prompt.lower()])
    
    ai = "Keine KI-Antwort."
    if client and rag:
        try:
            res = await client.aio.models.generate_content(model='gemini-2.0-flash', contents=f"Daten: {rag}\nFrage: {request.prompt}")
            ai = res.text
        except Exception as e:
            ai = f"KI-Fehler: {e}"

    async with _LEDGER_LOCK:
        WORM_LEDGER["count"] += 1
        h = hashlib.sha3_512(f"{WORM_LEDGER['last_hash']}{request.prompt}".encode()).hexdigest()
        WORM_LEDGER["last_hash"] = h

    return {"status": "200_OK_ALLOW", "ai_answer": ai, "data": {"ai_answer": ai}, "worm": {"block": WORM_LEDGER["count"], "hash": h}}

# ═══════════════════════════════════════════════════════════════════════════════
# 5. WEBSOCKET FÜR LIVE TELEMETRIE (Future Feature)
# ═══════════════════════════════════════════════════════════════════════════════
@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Simuliere Live-Metriken
            data = {
                "ts": time.time(),
                "throughput": random.randint(250000, 290000),
                "latency": round(random.uniform(8.5, 10.5), 2),
                "entropy": round(wusulum.entropy, 2),
                "bio_state": polyvagal.state,
                "worm_block": WORM_LEDGER["count"]
            }
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(1.5) # Update alle 1.5 Sekunden
    except WebSocketDisconnect:
        logger.info("WebSocket Client getrennt.")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
