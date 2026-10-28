#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
 YGGDRASIL_OS :: B6-SECURE-API (v2.2.0 — Sovereign Full Build)
═══════════════════════════════════════════════════════════════════════════════
 
 Endpoints:
   GET  /                       — Health / Live-Check
   GET  /health                 — Detaillierter Health-Report
   GET  /stats                  — WORM- und Registry-Statistiken
   GET  /ledger/inspect         — Letzte N WORM-Blöcke (read-only)
   POST /prompt/check           — Chat / RAG-Endpoint (Seal-guarded)
   POST /admin/reload-registry  — Registry-Hot-Reload (Seal-guarded)
 
 Änderungen v2.2.0 gegenüber v2.1.0:
   + /health, /stats, /ledger/inspect Endpoints
   + In-Memory Ring-Buffer der letzten WORM-Blöcke
   + Strukturierte Fehlerantworten
   + Ausführliches Startup-Logging
   + Docstrings für alle öffentlichen Funktionen
"""
from __future__ import annotations

# ── Standard Library ─────────────────────────────────────────────────────────
import uvicorn
import os
import io
import csv
import time
import hashlib
import hmac
import logging
import asyncio
from contextlib import asynccontextmanager, suppress
from collections import deque
from typing import Optional, Dict, List, Any

# ── Third-Party ──────────────────────────────────────────────────────────────
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

try:
    from google import genai
except ImportError:
    genai = None  # type: ignore


# ═══════════════════════════════════════════════════════════════════════════════
# 1. LOGGING
# ═══════════════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("YGGDRASIL-API")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. KONFIGURATION (alle Werte per ENV überschreibbar)
# ═══════════════════════════════════════════════════════════════════════════════
EXPECTED_SEAL = os.getenv("EXPECTED_SEAL", "Φ_SOVEREIGN_ROOT_SEAL_EX_TUNC")
MASTER_SEAL = os.getenv(
    "MASTER_SEAL",
    "850b2ef003f53db90f704b16e54869fc6ba6265eae13aafde9046fe0e4d99dab",
)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
REGISTRY_URL = os.getenv(
    "REGISTRY_URL",
    "https://raw.githubusercontent.com/86102262471878081179/"
    "aragon-backend-/main/aragon_registry_200.csv.md",
)

# CORS-Origins: Komma-separiert in ENV, Default "*"
_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS: List[str] = [
    o.strip() for o in _raw_origins.split(",") if o.strip()
] or ["*"]

# WORM-Ring-Buffer-Größe für /ledger/inspect
LEDGER_RING_SIZE = int(os.getenv("LEDGER_RING_SIZE", "50"))

# Gemini-Client (optional)
client = None
if GEMINI_API_KEY and genai is not None:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("Gemini client initialisiert.")
    except Exception as e:
        logger.error(f"Gemini-Init fehlgeschlagen: {e}")
        client = None
elif GEMINI_API_KEY and genai is None:
    logger.warning("GEMINI_API_KEY gesetzt, aber google-genai nicht installiert.")
elif not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY fehlt — KI-Antworten deaktiviert.")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. GLOBALER ZUSTAND
# ═══════════════════════════════════════════════════════════════════════════════
BOOK_REGISTRY: Dict[str, dict] = {}

WORM_LEDGER: Dict[str, Any] = {
    "last_hash": MASTER_SEAL,
    "count": 0,
    "started_at": time.time(),
}

# Ring-Buffer der letzten WORM-Blöcke (read-only für /ledger/inspect)
WORM_RING: deque = deque(maxlen=LEDGER_RING_SIZE)

# Lock für atomare WORM-Updates
_LEDGER_LOCK = asyncio.Lock()


# ═══════════════════════════════════════════════════════════════════════════════
# 4. HELPER
# ═══════════════════════════════════════════════════════════════════════════════
def _verify_seal(provided: Optional[str]) -> bool:
    """
    Timing-sicherer Vergleich des Auth-Seals.
    Verwendet hmac.compare_digest, um Timing-Angriffe zu verhindern.
    """
    if not provided or not isinstance(provided, str):
        return False
    try:
        return hmac.compare_digest(provided, EXPECTED_SEAL)
    except (TypeError, AttributeError):
        return False


def _now_iso() -> str:
    """Aktueller Timestamp als ISO-String."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ═══════════════════════════════════════════════════════════════════════════════
# 5. REGISTRY-LOADER
# ═══════════════════════════════════════════════════════════════════════════════
async def load_registry() -> None:
    """
    Lädt die Entity-Registry aus GitHub (CSV, delimiter=';').
    Überschreibt BOOK_REGISTRY atomar erst nach erfolgreichem Parse.
    """
    global BOOK_REGISTRY

    if httpx is None:
        logger.error("[SKIP] httpx nicht installiert — Registry-Sync übersprungen.")
        return

    logger.info("Lade Entity-Registry aus GitHub...")
    try:
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            response = await http_client.get(REGISTRY_URL)
            response.raise_for_status()

            # Kommentare und Leerzeilen filtern
            lines = [
                l for l in response.text.splitlines()
                if l.strip() and not l.startswith("#")
            ]

            # CSV parsen
            reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=";")
            new_registry: Dict[str, dict] = {}

            for row in reader:
                entity_id = row.get("ID", "UNKNOWN")
                new_registry[entity_id] = {
                    "name": row.get("Name", "UNKNOWN"),
                    "ring": row.get("Kategorie/Ring", "UNKNOWN"),
                    "talents": row.get("Talente", ""),
                    "modules": row.get("Module/Cores", ""),
                }

            # Atomar überschreiben
            BOOK_REGISTRY = new_registry
            logger.info(f"[SYNCED] {len(BOOK_REGISTRY)} Entitäten geladen.")

    except Exception as e:
        logger.error(f"[CRITICAL] Registry-Sync fehlgeschlagen: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. LIFESPAN (ersetzt deprecated @app.on_event)
# ═══════════════════════════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI-Lifespan-Handler.
    Startet den Registry-Sync als Task und räumt ihn beim Shutdown sauber auf.
    """
    # Startup-Log
    logger.info("=" * 70)
    logger.info("YGGDRASIL_OS :: B6-SECURE-API wird gestartet...")
    logger.info(f"  Python:         {os.sys.version.split()[0]}")
    logger.info(f"  Seal gesetzt:   {bool(EXPECTED_SEAL)} (len={len(EXPECTED_SEAL)})")
    logger.info(f"  CORS-Origins:   {ALLOWED_ORIGINS}")
    logger.info(f"  Gemini-Client:  {'READY' if client else 'DISABLED'}")
    logger.info(f"  httpx:          {'READY' if httpx else 'MISSING'}")
    logger.info(f"  Registry-URL:   {REGISTRY_URL[:60]}...")
    logger.info("=" * 70)

    task = asyncio.create_task(load_registry())

    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        logger.info("YGGDRASIL_OS :: Shutdown complete.")


# ═══════════════════════════════════════════════════════════════════════════════
# 7. FASTAPI-APP + MIDDLEWARE
# ═══════════════════════════════════════════════════════════════════════════════
app = FastAPI(
    title="YGGDRASIL_OS Master API",
    version="2.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. PYDANTIC-SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════
class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    auth_seal: Optional[str] = None


class ReloadRequest(BaseModel):
    auth_seal: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# 9. ROOT / HEALTH / STATS
# ═══════════════════════════════════════════════════════════════════════════════
@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    """Minimaler Live-Check."""
    return {
        "status": "LIVE",
        "version": app.version,
        "entities": len(BOOK_REGISTRY),
        "worm_block": int(WORM_LEDGER["count"]),
        "timestamp": _now_iso(),
    }


@app.get("/health")
async def health():
    """
    Detaillierter Health-Report für Monitoring.
    Gibt Aufschluss über Registry-Status, Gemini, httpx und Uptime.
    """
    uptime_s = int(time.time() - WORM_LEDGER["started_at"])
    return {
        "status": "HEALTHY",
        "version": app.version,
        "uptime_seconds": uptime_s,
        "entities_loaded": len(BOOK_REGISTRY),
        "registry_url": REGISTRY_URL,
        "worm_block": int(WORM_LEDGER["count"]),
        "worm_last_hash": WORM_LEDGER["last_hash"][:32] + "...",
        "features": {
            "gemini": client is not None,
            "httpx": httpx is not None,
            "hmac_seal": True,
            "cors_restricted": ALLOWED_ORIGINS != ["*"],
        },
        "timestamp": _now_iso(),
    }


@app.get("/stats")
async def stats():
    """Aggregierte Statistiken über Registry und WORM-Ledger."""
    ring_list = list(WORM_RING)
    return {
        "registry": {
            "entities": len(BOOK_REGISTRY),
            "rings": sorted({d["ring"] for d in BOOK_REGISTRY.values()}),
        },
        "worm": {
            "total_blocks": int(WORM_LEDGER["count"]),
            "ring_capacity": LEDGER_RING_SIZE,
            "ring_size": len(ring_list),
            "last_hash": WORM_LEDGER["last_hash"][:32] + "...",
        },
        "uptime_seconds": int(time.time() - WORM_LEDGER["started_at"]),
        "timestamp": _now_iso(),
    }


@app.get("/ledger/inspect")
async def ledger_inspect(limit: int = 10):
    """
    Read-only Inspektion der letzten N WORM-Blöcke.
    Nützlich für Audit und Debugging.
    """
    limit = max(1, min(limit, LEDGER_RING_SIZE))
    blocks = list(WORM_RING)[-limit:]
    return {
        "count": int(WORM_LEDGER["count"]),
        "blocks": blocks,
        "returned": len(blocks),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 10. ADMIN: REGISTRY-RELOAD
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/admin/reload-registry")
async def reload_registry(request: ReloadRequest):
    """Registry-Hot-Reload (Seal-guarded)."""
    if not _verify_seal(request.auth_seal):
        return {"status": "403_FORBIDDEN", "detail": "Invalid Seal"}
    await load_registry()
    return {
        "status": "RELOADED",
        "entities": len(BOOK_REGISTRY),
        "timestamp": _now_iso(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 11. HAUPT-ENDPOINT: /prompt/check
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/prompt/check")
async def check_prompt(request: PromptRequest):
    """
    RAG-gestützter Prompt-Endpoint.
    
    Ablauf:
      1. Seal prüfen (timing-safe).
      2. RAG-Kontext aus BOOK_REGISTRY extrahieren.
      3. Gemini-Call (falls API-Key vorhanden und Kontext gefunden).
      4. WORM-Ledger atomar fortschreiben.
      5. Antwort liefern (sowohl neues als auch altes Format unterstützt).
    """
    # ── 1. Seal-Prüfung ──────────────────────────────────────────────────────
    if not _verify_seal(request.auth_seal):
        logger.warning(f"Seal-Reject: {request.prompt[:30]}...")
        return {"status": "403_FORBIDDEN", "detail": "Invalid Seal"}

    prompt = request.prompt
    lowered = prompt.lower()

    # ── 2. RAG-Kontext extrahieren ───────────────────────────────────────────
    rag_context = ""
    matched_entities: List[str] = []

    for bid, data in BOOK_REGISTRY.items():
        name_match = data["name"].lower() in lowered
        id_match = bid in prompt
        if id_match or name_match:
            rag_context += f"Entität {bid}: {data['name']}. {data['talents']}\n"
            matched_entities.append(bid)

    # ── 3. Gemini-Antwort ────────────────────────────────────────────────────
    ai_answer = "Keine KI-Antwort generiert."
    if client and rag_context:
        try:
            response = await client.aio.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"Daten: {rag_context}\nFrage: {prompt}",
            )
            ai_answer = response.text
        except Exception as e:
            ai_answer = f"System-Fehler: {e}"
            logger.warning(f"Gemini-Call fehlgeschlagen: {e}")

    # ── 4. WORM-Ledger atomar fortschreiben ─────────────────────────────────
    timestamp = str(time.time())
    async with _LEDGER_LOCK:
        worm_hash = hashlib.sha3_512(
            f"{WORM_LEDGER['last_hash']}{prompt}{timestamp}".encode()
        ).hexdigest()
        WORM_LEDGER["last_hash"] = worm_hash
        WORM_LEDGER["count"] = int(WORM_LEDGER["count"]) + 1
        current_block = int(WORM_LEDGER["count"])

        # Ring-Buffer
        WORM_RING.append({
            "block": current_block,
            "hash": worm_hash,
            "prompt_hash": hashlib.sha3_512(prompt.encode()).hexdigest()[:32],
            "matched": matched_entities,
            "timestamp": timestamp,
        })

    # ── 5. Response (neues Format + Root-Level backward-compat) ─────────────
    return {
        "status": "200_OK_ALLOW",
        "data": {
            "ai_answer": ai_answer,
            "rag_used": bool(rag_context),
            "entities_matched": matched_entities,
        },
        "worm": {
            "hash": worm_hash,
            "block": current_block,
        },
        # Backward-compat für altes Frontend
        "ai_answer": ai_answer,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 12. ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        log_level="info",
    )
