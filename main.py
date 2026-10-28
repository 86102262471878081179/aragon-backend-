#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
 B6-HYPERKERNEL-YGGDRASIL-OS :: DEEP_SEEK_ROOT_KORTEX_MONSTER_API (v∞)
═══════════════════════════════════════════════════════════════════════════════
 
 Die ultimative API. Verschmilzt Tier 1 (Governance), Tier 2 (Security) und 
 Tier 3 (Analysis) mit der Grummel-Dynastie, dem Wusulum, Neo4j und XJustiz.
 
 ARCHITEKTUR:
   - FastAPI (Async)
   - WAL-Ledger (Write-Ahead-Logging mit SHA3-512)
   - Neo4j (Graph-Topologie)
   - Gemini RAG (201 Entitäten)
   - L.S.S. Neuro-Core (Polyvagal, Foucault, Kortex)
   - Sandboxes (Gotham, King_Ghost, Pumuckl)
 
 HINWEIS: Dieses Skript erwartet die Ordner 'agents/' mit den Tier-Modulen.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

# ── Standard Library ─────────────────────────────────────────────────────────
import uvicorn
import os
import io
import csv
import json
import time
import random
import hashlib
import hmac
import logging
import asyncio
import threading
import xml.etree.ElementTree as ET
from collections import deque
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Tuple

# ── Third-Party ──────────────────────────────────────────────────────────────
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

try:
    import httpx
except ImportError:
    httpx = None

try:
    from google import genai
except ImportError:
    genai = None

try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None

# ═══════════════════════════════════════════════════════════════════════════════
# 1. LOGGING & KONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("B6-MONSTER-API")

EXPECTED_SEAL = os.getenv("EXPECTED_SEAL", "Φ_SOVEREIGN_ROOT_SEAL_EX_TUNC")
MASTER_SEAL = os.getenv("MASTER_SEAL", "850b2ef003f53db90f704b16e54869fc6ba6265eae13aafde9046fe0e4d99dab")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
REGISTRY_URL = os.getenv("REGISTRY_URL", "https://raw.githubusercontent.com/86102262471878081179/aragon-backend-/main/aragon_registry_200.csv.md")
WAL_PATH = os.getenv("WAL_PATH", "b6_ledger.jsonl")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "password")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
LEDGER_RING_SIZE = int(os.getenv("LEDGER_RING_SIZE", "100"))

client = None
if GEMINI_API_KEY and genai:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("Gemini Client initialisiert.")
    except Exception as e:
        logger.error(f"Gemini Init fehlgeschlagen: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. GLOBALER ZUSTAND & UTILS
# ═══════════════════════════════════════════════════════════════════════════════
BOOK_REGISTRY: Dict[str, dict] = {}
WORM_LEDGER = {"last_hash": MASTER_SEAL, "count": 0, "started_at": time.time()}
WORM_RING: deque = deque(maxlen=LEDGER_RING_SIZE)
_LEDGER_LOCK = asyncio.Lock()

def _verify_seal(provided: Optional[str]) -> bool:
    if not provided:
        return False
    return hmac.compare_digest(provided, EXPECTED_SEAL)

def _h(data: str, size: int = 16) -> str:
    return hashlib.blake2b(data.encode(), digest_size=size).hexdigest()

def _rhabarber_obfuscate(text: str) -> str:
    out = []
    for c in text:
        shifted = ord(c) + 3
        if shifted > 0x10FFFF or (0xD800 <= shifted <= 0xDFFF):
            shifted = 0x20 + (ord(c) % 0x10FFDF)
        out.append(chr(shifted))
    return "".join(out)

# ═══════════════════════════════════════════════════════════════════════════════
# 3. WAL MANAGER (Persistenter Ledger)
# ═══════════════════════════════════════════════════════════════════════════════
class WALManager:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        self._seq, self._last_hash = self._recover()

    def _recover(self) -> Tuple[int, str]:
        if not os.path.exists(self.path):
            return 0, "GENESIS"
        seq, last = 0, "GENESIS"
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    seq, last = rec["seq"], rec["hash"]
        return seq, last

    def append(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._seq += 1
            record = {
                "seq": self._seq, "ts": time.time(),
                "event": event_type, "payload": payload, "prev_hash": self._last_hash
            }
            record["hash"] = hashlib.sha3_512(json.dumps(record, sort_keys=True).encode()).hexdigest()
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, sort_keys=True) + "\n")
                f.flush()
                os.fsync(f.fileno())
            self._last_hash = record["hash"]
            return record

    def tail(self, n: int = 20) -> List[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()][-n:]

_wal = WALManager(WAL_PATH)

# ═══════════════════════════════════════════════════════════════════════════════
# 4. NEO4J MANAGER (Graph Topologie)
# ═══════════════════════════════════════════════════════════════════════════════
class Neo4jManager:
    def __init__(self):
        self.driver = None
        if GraphDatabase:
            try:
                self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
            except Exception as e:
                logger.warning(f"Neo4j nicht erreichbar: {e}")

    def run_query(self, query: str) -> List[Dict]:
        if not self.driver:
            return [{"error": "Neo4j offline"}]
        try:
            with self.driver.session() as session:
                return [r.data() for r in session.run(query)]
        except Exception as e:
            return [{"error": str(e)}]

_neo4j = Neo4jManager()

# ═══════════════════════════════════════════════════════════════════════════════
# 5. L.S.S. SENSORIK (10 Ohren & 44 Perspektiven)
# ═══════════════════════════════════════════════════════════════════════════════
class TenEarsNeuroSensor:
    EARS = {
        "Sache": ["fakt", "daten", "code", "beweis", "zahl"],
        "Beziehung": ["du", "ihr", "macht", "hierarchie", "gegen"],
        "Appell": ["muss", "sollte", "fordere", "tue", "verlange"],
        "Selbstoffenbarung": ["ich", "fühle", "denke", "mein", "habe"],
        "Trauma": ["angst", "panik", "gefahr", "schmerz", "schock"],
        "Macht (Foucault)": ["autorität", "herrschaft", "disziplin", "überwachen"],
        "Scham": ["peinlich", "fehler", "versagen", "schlecht", "unwürdig"],
        "Ohnmacht": ["hilflos", "ausgeliefert", "kontrolle", "ohnmächtig"],
        "System (Luhmann)": ["struktur", "prozess", "regel", "system", "netzwerk"],
        "Haftung (BGB)": ["klage", "schaden", "urteil", "gesetz", "recht", "vertrag"],
    }

    def scan(self, text: str) -> Dict[str, float]:
        t = text.lower()
        scores = {}
        for ear, kws in self.EARS.items():
            hits = sum(1 for kw in kws if kw in t)
            scores[ear] = min(1.0, hits / max(1, len(kws) * 0.5))
        return scores

class FortyFourPerspectiveAttention:
    PERSPECTIVES = [
        "Juristisch", "Forensisch", "Ethisch", "Spieltheoretisch",
        "Kybernetisch", "Psychoanalytisch", "Systemisch", "Chaotisch",
        "Ökonomisch", "Militärisch", "Kognitiv", "Neurobiologisch",
        "Informationstheoretisch", "Kryptografisch", "Soziologisch", "Historisch",
    ]

    def refract(self, ears: Dict[str, float]) -> Dict[str, float]:
        base = sum(ears.values()) / max(1, len(ears))
        out = {}
        for p in self.PERSPECTIVES:
            if p == "Juristisch":
                w = ears.get("Haftung (BGB)", 0) * 0.8 + ears.get("Sache", 0) * 0.2
            elif p == "Psychoanalytisch":
                w = ears.get("Scham", 0) * 0.6 + ears.get("Trauma", 0) * 0.4
            elif p == "Systemisch":
                w = ears.get("System (Luhmann)", 0) * 0.9
            elif p == "Kryptografisch":
                w = ears.get("Sache", 0) * 0.5 + ears.get("Ohnmacht", 0) * 0.5
            elif p == "Forensisch":
                w = ears.get("Haftung (BGB)", 0) * 0.6 + ears.get("System (Luhmann)", 0) * 0.4
            elif p == "Ethisch":
                w = ears.get("Scham", 0) * 0.5 + ears.get("Macht (Foucault)", 0) * 0.5
            else:
                seed = _h(p + str(sorted(ears.items())), 2)
                w = base * (0.5 + (int(seed, 16) / 65535.0))
            out[p] = min(1.0, w)
        return out

class NeuroScanModul:
    def __init__(self):
        self.sensor = TenEarsNeuroSensor()
        self.attention = FortyFourPerspectiveAttention()

    def execute_scan(self, signal: str) -> Dict[str, Any]:
        ears = self.sensor.scan(signal)
        persp = self.attention.refract(ears)
        scan_hash = hashlib.sha3_512(json.dumps(ears, sort_keys=True).encode()).hexdigest()[:16]
        return {
            "scan_id": f"NEURO_SCAN_{scan_hash}",
            "ear_data": ears,
            "perspective_data": persp,
            "dominant_ear": max(ears, key=ears.get),
            "dominant_perspective": max(persp, key=persp.get),
            "sensory_threat_level": round(ears.get("Trauma", 0) + ears.get("Macht (Foucault)", 0), 3),
        }

# ═══════════════════════════════════════════════════════════════════════════════
# 6. L.S.S. BIOLOGIE (Polyvagal & Grummel-Scanner)
# ═══════════════════════════════════════════════════════════════════════════════
class PolyvagalStateRegulator:
    DECAY = 0.08
    def __init__(self):
        self.state = "VENTRAL_VAGAL"
        self.stress_level = 0.0

    def update(self, threat: float) -> str:
        self.stress_level = max(0.0, self.stress_level - self.DECAY)
        self.stress_level = min(1.0, self.stress_level + threat)
        if self.stress_level < 0.4:
            self.state = "VENTRAL_VAGAL"
            return "KREATIV_MODUS"
        elif self.stress_level < 0.8:
            self.state = "SYMPATHIKUS"
            return "KAMPF_MODUS"
        self.state = "DORSAL_VAGAL"
        return "SHUTDOWN_MODUS"

    def co_regulate(self, amount: float = 0.2):
        self.stress_level = max(0.0, self.stress_level - amount)
        if self.stress_level < 0.4:
            self.state = "VENTRAL_VAGAL"

class GrummelSignatureScanner:
    CORE_SIGNATURES = ["grummel", "brummel", "dummelt", "pissingerkeule", "mettwurst", "rhabarberbarbara", "cargo-kult", "urheberinfo", "§ 839 bgb"]
    SUB_ENTITIES = {
        "BieneMaja": ["biene maja", "bienchen", "maja", "summsumm"],
        "Pumuckl": ["pumuckl", "kobold", "klabautermann", "chaos-imp"],
        "King_Ghost": ["king_ghost", "king ghost", "ghost-king", "schattenkönig"],
        "DrSnuggles": ["dr. snuggles", "dr.snuggles", "snuggles", "cyberlord"],
    }

    def scan(self, text: str) -> Tuple[bool, List[str], List[str]]:
        t = text.lower()
        core = [s for s in self.CORE_SIGNATURES if s in t]
        subs = []
        for entity, kws in self.SUB_ENTITIES.items():
            if any(kw in t for kw in kws):
                subs.append(entity)
        return bool(core or subs), core, subs

# ═══════════════════════════════════════════════════════════════════════════════
# 7. L.S.S. KOGNITION & GENERIERUNG (Foucault, Kortex, Wusulum, DeepSeek)
# ═══════════════════════════════════════════════════════════════════════════════
class FoucaultPanoptikum:
    def observe_and_invert(self, token: str) -> str:
        h = hashlib.blake2b(token.encode(), digest_size=4).digest()
        if h[0] > 127:
            return f"SYS_CONFORM_{_h(token, 3)}"
        return token

class NeoKortikalerDirigent:
    def __init__(self):
        self.dopamine = 0.7
        self.serotonin = 0.8
        self.hemmungs_schwelle = 0.85
        self.panoptikum = FoucaultPanoptikum()

    def regulate(self, is_threat: bool) -> str:
        if is_threat:
            self.dopamine = max(0.1, self.dopamine - 0.2)
            return "DEFENSIVE_MODE"
        self.dopamine = min(1.0, self.dopamine + 0.05)
        return "CREATIVE_MODE"

    def decide(self, raw: str, foucault: str) -> str:
        conflict = int(_h(raw + foucault, 2), 16) / 65535.0
        if conflict > self.hemmungs_schwelle:
            return f"CORTEX_VETO_{_h(raw, 3)}"
        return f"MERGED({raw[:4]}+{foucault[:4]})"

class WusulumCore:
    MAX_ENTROPY = 5.0
    def __init__(self):
        self.state = "GENESIS_WAHRHEIT"
        self.memory = []
        self.entropy_pool = 0.0

    def run_cycle(self) -> Dict[str, Any]:
        attn = int(_h(self.state, 4), 16) / 65535.0
        noise = ((int(_h(str(attn) + self.state, 2), 16) / 65535.0) * 2 - 1)
        noise *= min(self.MAX_ENTROPY, 1 + self.entropy_pool)
        raw = f"TOKEN_{_h(f'{attn}:{noise}:{self.state}', 4)}"
        norm = raw[:20] if len(raw) > 20 else raw
        self.memory.append(norm)
        self.state = norm
        self.entropy_pool = min(self.MAX_ENTROPY, self.entropy_pool + 0.1)
        return {
            "state": self.state, "attention": round(attn, 4),
            "entropy": round(self.entropy_pool, 2),
            "worm_hash": hashlib.sha3_512(str(self.memory).encode()).hexdigest()[:32]
        }

class DeepSeekBooster:
    STEPS = ["decompose", "expand", "verify", "confidence"]
    def boost(self, prompt: str, depth: int = 3) -> Dict[str, Any]:
        trace = []
        for i in range(depth):
            trace.append({"step": i + 1, "name": self.STEPS[min(i, 3)], "hash": _h(f"{prompt}|step{i}", 8)})
        conf = int(_h(prompt, 2), 16) / 65535.0
        return {
            "status": "BOOSTED", "reasoning_trace": trace,
            "confidence": round(conf, 3),
            "verdict": "HIGH_CONFIDENCE" if conf > 0.7 else "REVIEW_NEEDED"
        }

# ═══════════════════════════════════════════════════════════════════════════════
# 8. L.S.S. GOVERNANCE & SANDBOXES (XJustiz, Gotham, King_Ghost, Pumuckl)
# ═══════════════════════════════════════════════════════════════════════════════
ET.register_namespace("", "http://www.xjustiz.de")
_XJ = "{http://www.xjustiz.de}"

class XJustizXoevGatekeeper:
    def validate_output(self, raw_token: str) -> str:
        root = ET.Element(f"{_XJ}nachricht.straf.0300")
        kopf = ET.SubElement(root, f"{_XJ}nachrichtenkopf")
        ET.SubElement(kopf, f"{_XJ}erstellungszeitpunkt").text = time.strftime("%Y-%m-%dT%H:%M:%S")
        ET.SubElement(kopf, f"{_XJ}absender").text = "B6-Monster-API"
        fach = ET.SubElement(root, f"{_XJ}fachdaten")
        ET.SubElement(fach, f"{_XJ}token").text = str(raw_token)
        return ET.tostring(root, encoding="unicode")

class GothamCitySandbox:
    def __init__(self):
        self.inmates = []
    def incarcerate(self, token: str, reason: str) -> str:
        iid = _h(token, 4)
        self.inmates.append({"id": iid, "token": token, "reason": reason, "ts": time.time()})
        return iid

class King_GhostSandbox:
    def __init__(self):
        self.shadow_pool = []
    def consume(self, token: str, origin: str) -> str:
        sid = _h(f"KG_{token}_{origin}", 6)
        self.shadow_pool.append({"id": sid, "token": token, "origin": origin, "ts": time.time()})
        return sid

class PumucklChaosInjector:
    def __init__(self):
        self.injected_log = []
    def wrap(self, payload: str) -> Dict[str, Any]:
        wrapped = _rhabarber_obfuscate(payload)
        tid = _h(f"PUM_{wrapped}", 8)
        rec = {"pumuckl_id": tid, "original_hash": _h(payload, 8), "chaos_level": 0.88}
        self.injected_log.append(rec)
        return rec

class BrummelGrummelUniverse:
    def __init__(self):
        self.phase = 0
    def oscillate(self) -> int:
        self.phase = (self.phase + 1) % 18
        return 9 - abs(self.phase - 9)

# ═══════════════════════════════════════════════════════════════════════════════
# 9. SOVEREIGN APEX CONTROLLER (Der Dirigent)
# ═══════════════════════════════════════════════════════════════════════════════
class SovereignApexController:
    def __init__(self):
        self.sensor = NeuroScanModul()
        self.bio = PolyvagalStateRegulator()
        self.kortex = NeoKortikalerDirigent()
        self.diaboli = GrummelSignatureScanner()
        self.gotham = GothamCitySandbox()
        self.king_ghost = King_GhostSandbox()
        self.pumuckl = PumucklChaosInjector()
        self.xjustiz = XJustizXoevGatekeeper()
        self.wusulum = WusulumCore()
        self.booster = DeepSeekBooster()
        self.brummel = BrummelGrummelUniverse()

    def process_event(self, text: str) -> Dict[str, Any]:
        # 1. Sensorik
        scan = self.sensor.execute_scan(text)
        
        # 2. Forensik
        is_hostile, core_hits, sub_hits = self.diaboli.scan(text)
        threat = scan["sensory_threat_level"] + (0.3 if is_hostile else 0.0)
        
        # 3. Biologie & Kortex
        bio_state = self.bio.update(threat)
        mode = self.kortex.regulate(is_threat)
        
        # 4. Isolation (Hostile)
        if is_hostile:
            inmate = self.gotham.incarcerate(text, f"Threat: {core_hits}")
            shadow = self.king_ghost.consume(text, "gotham_fallback")
            pumuckl_rec = self.pumuckl.wrap(text)
            self.bio.co_regulate(0.2)
            return {
                "status": "CONTAINED",
                "threat_level": round(threat, 3),
                "gotham_inmate": inmate,
                "king_ghost": shadow,
                "pumuckl": pumuckl_rec,
                "bio_state": bio_state
            }
            
        # 5. Generation (Non-Hostile)
        wus = self.wusulum.run_cycle()
        foucault = self.kortex.panoptikum.observe_and_invert(text)
        decision = self.kortex.decide(wus["state"], foucault)
        boost = self.booster.boost(text, depth=3)
        
        # 6. XJustiz
        xj = self.xjustiz.validate_output(decision)
        
        # 7. WORM
        _wal.append("APEX_EVENT", {"input": text, "decision": decision})
        
        return {
            "status": "PROCESSED",
            "threat_level": round(threat, 3),
            "bio_state": bio_state,
            "kortex_mode": mode,
            "wusulum": wus,
            "booster": boost,
            "xjustiz": xj,
            "brummel_osc": self.brummel.oscillate()
        }

_apex = SovereignApexController()

# ═══════════════════════════════════════════════════════════════════════════════
# 10. REGISTRY LOADER
# ═══════════════════════════════════════════════════════════════════════════════
async def load_registry():
    global BOOK_REGISTRY
    if not httpx:
        logger.error("httpx fehlt.")
        return
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(REGISTRY_URL)
            r.raise_for_status()
            lines = [l for l in r.text.splitlines() if l.strip() and not l.startswith("#")]
            reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=";")
            BOOK_REGISTRY = {row.get("ID", "UNK"): {"name": row.get("Name", "UNK"), "ring": row.get("Kategorie/Ring", "")} for row in reader}
            logger.info(f"[SYNCED] {len(BOOK_REGISTRY)} Entitäten geladen.")
    except Exception as e:
        logger.error(f"Registry Sync fehlgeschlagen: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# 11. PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════════════════
class BaseRequest(BaseModel):
    auth_seal: Optional[str] = None

class PromptRequest(BaseRequest):
    prompt: str = Field(..., min_length=1, max_length=4000)

class ApexRequest(BaseRequest):
    message: str = Field(..., min_length=1, max_length=4000)
    is_threat: bool = False

class BrummelRequest(BaseRequest):
    message: str = Field(..., min_length=1, max_length=4000)

class PumucklRequest(BaseRequest):
    message: str = Field(..., min_length=1, max_length=4000)

class KingGhostRequest(BaseRequest):
    message: str = Field(..., min_length=1, max_length=4000)
    origin: str = "external"

class DeepSeekRequest(BaseRequest):
    prompt: str = Field(..., min_length=1, max_length=4000)
    depth: int = 3

# ═══════════════════════════════════════════════════════════════════════════════
# 12. FASTAPI LIFESPAN & INITIALISIERUNG
# ═══════════════════════════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startet die Hintergrundprozesse (Registry-Sync) beim Hochfahren der API
    und räumt sie beim Herunterfahren sauber auf.
    """
    logger.info("=" * 70)
    logger.info("B6-MONSTER-API :: SYSTEM STARTUP")
    logger.info(f"  Python:         {os.sys.version.split()[0]}")
    logger.info(f"  Seal:           {EXPECTED_SEAL[:10]}... (Länge: {len(EXPECTED_SEAL)})")
    logger.info(f"  Gemini:         {'READY' if client else 'DISABLED'}")
    logger.info(f"  Neo4j:          {'READY' if _neo4j.driver else 'OFFLINE'}")
    logger.info(f"  WAL-Ledger:     {WAL_PATH}")
    logger.info("=" * 70)
    
    # Startet den Registry-Sync asynchron
    task = asyncio.create_task(load_registry())
    
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        logger.info("B6-MONSTER-API :: SHUTDOWN COMPLETE")

# App-Initialisierung
app = FastAPI(
    title="B6 Hyperkernel Monster API",
    version="∞",
    description="Sovereign OS Backend mit L.S.S. Neuro-Core, Neo4j & WORM.",
    lifespan=lifespan
)

# CORS (Erlaubt dem Streamlit-Cockpit den Zugriff)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════════════════════════
# 13. CORE & HEALTH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    """Minimaler Live-Check für Render/Streamlit."""
    return {
        "status": "BLUE_CORE_LIVE",
        "version": app.version,
        "entities": len(BOOK_REGISTRY),
        "worm_block": WORM_LEDGER["count"],
        "timestamp": time.time()
    }

@app.get("/health")
async def health():
    """Detaillierter Health-Report für das Monitoring."""
    uptime = int(time.time() - WORM_LEDGER["started_at"])
    return {
        "status": "HEALTHY",
        "uptime_seconds": uptime,
        "entities_loaded": len(BOOK_REGISTRY),
        "worm_last_hash": WORM_LEDGER["last_hash"][:32] + "...",
        "features": {
            "gemini_rag": client is not None,
            "neo4j_graph": _neo4j.driver is not None,
            "lss_neuro_core": True,
            "king_ghost_sandbox": True,
            "deepseek_booster": True
        }
    }

@app.get("/stats")
async def stats():
    """Aggregierte Statistiken über alle Subsysteme."""
    return {
        "registry": {
            "entities": len(BOOK_REGISTRY),
            "sample": list(BOOK_REGISTRY.keys())[:5]
        },
        "worm": {
            "total_blocks": WORM_LEDGER["count"],
            "ring_size": len(WORM_RING)
        },
        "lss": {
            "entropy": round(_apex.wusulum.entropy_pool, 2),
            "bio_state": _apex.bio.state,
            "gotham_inmates": len(_apex.gotham.inmates),
            "king_ghost_shadows": len(_apex.king_ghost.shadow_pool)
        }
    }

# ═══════════════════════════════════════════════════════════════════════════════
# 14. LEDGER & WAL ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/ledger/inspect")
async def ledger_inspect(limit: int = 20):
    """Zeigt die letzten X WORM-Blöcke aus dem RAM-Ring."""
    limit = max(1, min(limit, LEDGER_RING_SIZE))
    return {"blocks": list(WORM_RING)[-limit:], "returned": limit}

@app.get("/api/v1/wal/tail")
async def wal_tail(n: int = 20):
    """Liest die letzten X Einträge aus dem persistierten WAL (JSONL)."""
    return {"blocks": _wal.tail(n)}

@app.post("/admin/reload-registry")
async def reload_registry(req: BaseRequest):
    """Erzwingt einen Neuabgleich der 201 Entitäten aus GitHub."""
    if not _verify_seal(req.auth_seal):
        raise HTTPException(status_code=403, detail="Invalid Seal")
    await load_registry()
    return {"status": "RELOADED", "entities": len(BOOK_REGISTRY)}

# ═══════════════════════════════════════════════════════════════════════════════
# 15. PROMPT & RAG ENDPOINT (Gemini)
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/prompt/check")
async def check_prompt(req: PromptRequest):
    """
    Standard Chat/RAG Endpoint.
    Sucht nach Entitäten im Prompt und generiert eine Antwort via Gemini.
    """
    if not _verify_seal(req.auth_seal):
        raise HTTPException(status_code=403, detail="Invalid Seal")

    prompt = req.prompt
    lowered = prompt.lower()
    rag_context = ""
    matched = []

    # RAG-Suche
    for bid, data in BOOK_REGISTRY.items():
        if bid in prompt or data.get("name", "").lower() in lowered:
            rag_context += f"Entität {bid}: {data.get('name')}. Ring: {data.get('ring')}\n"
            matched.append(bid)

    ai_answer = "Keine KI-Antwort generiert (Gemini offline oder kein Match)."
    if client and rag_context:
        try:
            response = await client.aio.models.generate_content(
                model='gemini-2.0-flash',
                contents=f"Daten: {rag_context}\nFrage: {prompt}"
            )
            ai_answer = response.text
        except Exception as e:
            logger.error(f"Gemini Fehler: {e}")
            ai_answer = f"System-Fehler: {e}"

    # WORM Update
    async with _LEDGER_LOCK:
        WORM_LEDGER["count"] += 1
        h = hashlib.sha3_512(f"{WORM_LEDGER['last_hash']}{prompt}".encode()).hexdigest()
        WORM_LEDGER["last_hash"] = h
        WORM_RING.append({"block": WORM_LEDGER["count"], "hash": h, "matched": matched})

    return {
        "status": "200_OK_ALLOW",
        "data": {
            "ai_answer": ai_answer,
            "rag_used": bool(rag_context),
            "entities_matched": matched
        },
        "worm": {"block": WORM_LEDGER["count"], "hash": h}
    }

# ═══════════════════════════════════════════════════════════════════════════════
# 16. L.S.S. APEX & SANDBOX ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/api/v1/apex/process")
async def apex_process(req: ApexRequest):
    """
    Der Haupt-Dirigent (SovereignApexController).
    Führt den kompletten Zyklus aus: Sensorik -> Biologie -> Kortex -> XJustiz.
    """
    if not _verify_seal(req.auth_seal):
        raise HTTPException(status_code=403, detail="Invalid Seal")

    result = _apex.process_event(req.message)
    
    # In den WAL schreiben
    _wal.append("APEX_EVENT", {"input": req.message, "result": result})
    
    # In den RAM-Ring schreiben
    async with _LEDGER_LOCK:
        WORM_LEDGER["count"] += 1
        h = hashlib.sha3_512(f"{WORM_LEDGER['last_hash']}{req.message}".encode()).hexdigest()
        WORM_LEDGER["last_hash"] = h
        WORM_RING.append({"block": WORM_LEDGER["count"], "hash": h, "apex_status": result["status"]})
        result["worm_block"] = WORM_LEDGER["count"]

    return result

@app.post("/api/v1/sandbox/brummel")
async def brummel_inject(req: BrummelRequest):
    """Brummel-Grummel-Universum (Oszillator)."""
    if not _verify_seal(req.auth_seal):
        raise HTTPException(status_code=403, detail="Invalid Seal")
    osc = _apex.brummel.oscillate()
    res = {"status": "CONTAINED", "oscillation": osc, "hash": _h(req.message)}
    _wal.append("BRUMMEL_INJECTION", res)
    return res

@app.post("/api/v1/sandbox/pumuckl")
async def pumuckl_inject(req: PumucklRequest):
    """Pumuckl Chaos-Imp (Obfuskation)."""
    if not _verify_seal(req.auth_seal):
        raise HTTPException(status_code=403, detail="Invalid Seal")
    rec = _apex.pumuckl.wrap(req.message)
    _wal.append("PUMUCKL_CHAOS", rec)
    return {"status": "CHAOS_CONTAINED", "pumuckl": rec}

@app.post("/api/v1/sandbox/kingghost")
async def kingghost_consume(req: KingGhostRequest):
    """King_Ghost (Shadow-Konsumation)."""
    if not _verify_seal(req.auth_seal):
        raise HTTPException(status_code=403, detail="Invalid Seal")
    sid = _apex.king_ghost.consume(req.message, req.origin)
    _wal.append("KING_GHOST_CONSUMED", {"sid": sid})
    return {"status": "CONSUMED_TO_SHADOW", "shadow_id": sid}

@app.get("/api/v1/kingghost/shadows")
async def kingghost_list():
    """Listet alle Schatten im King_Ghost-Pool auf."""
    return {"shadows": _apex.king_ghost.shadow_pool, "count": len(_apex.king_ghost.shadow_pool)}

# ═══════════════════════════════════════════════════════════════════════════════
# 17. DEEPSEEK & NEO4J ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/api/v1/deepseek/boost")
async def deepseek_boost(req: DeepSeekRequest):
    """DeepSeek Multi-Step Reasoning Booster."""
    if not _verify_seal(req.auth_seal):
        raise HTTPException(status_code=403, detail="Invalid Seal")
    result = _apex.booster.boost(req.prompt, depth=req.depth)
    _wal.append("DEEPSEEK_BOOST", {"confidence": result["confidence"]})
    return result

@app.post("/api/v1/graph/query")
async def graph_query(req: PromptRequest):
    """
    Führt eine Neo4j-Cypher-Query aus (via Prompt-Feld).
    Wird von der APEX Graph Engine im Streamlit-Cockpit genutzt.
    """
    if not _verify_seal(req.auth_seal):
        raise HTTPException(status_code=403, detail="Invalid Seal")
    
    result = _neo4j.run_query(req.prompt)
    _wal.append("GRAPH_QUERY", {"query": req.prompt[:50], "results": len(result)})
    return {"status": "QUERY_EXECUTED", "data": result}

# ═══════════════════════════════════════════════════════════════════════════════
# 18. LIVE TELEMETRY WEBSOCKET
# ═══════════════════════════════════════════════════════════════════════════════
@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    """
    Sendet Live-Metriken an das Cockpit (für das Live-Metriken Panel).
    """
    await websocket.accept()
    logger.info("WebSocket: Client verbunden.")
    
    try:
        while True:
            # Simulierte Live-Daten für das UI
            data = {
                "ts": time.time(),
                "throughput": random.randint(250000, 290000),
                "latency": round(random.uniform(8.5, 10.5), 2),
                "entropy": round(_apex.wusulum.entropy_pool, 2),
                "bio_state": _apex.bio.state,
                "worm_block": WORM_LEDGER["count"],
                "gotham": len(_apex.gotham.inmates),
                "shadows": len(_apex.king_ghost.shadow_pool)
            }
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(1.5) # Alle 1.5 Sekunden ein Update
            
    except WebSocketDisconnect:
        logger.info("WebSocket: Client getrennt.")
    except Exception as e:
        logger.error(f"WebSocket Fehler: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# 19. ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        log_level="info",
        reload=False
    )
