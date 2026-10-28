#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YGGDRASIL_OS :: B6-SECURE-API (v2.1.0 — par excellence)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from contextlib import asynccontextmanager, suppress
import uvicorn, os, hashlib, hmac, time, io, csv, httpx, logging, asyncio
from google import genai

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("YGGDRASIL-API")

# ── Konfiguration ─────────────────────────────────────────────────────────────
EXPECTED_SEAL = os.getenv("EXPECTED_SEAL", "Φ_SOVEREIGN_ROOT_SEAL_EX_TUNC")
MASTER_SEAL   = os.getenv("MASTER_SEAL",
    "850b2ef003f53db90f704b16e54869fc6ba6265eae13aafde9046fe0e4d99dab")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
REGISTRY_URL   = os.getenv(
    "REGISTRY_URL",
    "https://raw.githubusercontent.com/86102262471878081179/"
    "aragon-backend-/main/aragon_registry_200.csv.md",
)

_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS: List[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()] or ["*"]

client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

# ── Zustand ───────────────────────────────────────────────────────────────────
BOOK_REGISTRY: Dict[str, dict] = {}
WORM_LEDGER = {"last_hash": MASTER_SEAL, "count": 0}
_LEDGER_LOCK = asyncio.Lock()


def _verify_seal(provided: Optional[str]) -> bool:
    """Timing-safe Seal-Prüfung."""
    if not provided or not isinstance(provided, str):
        return False
    try:
        return hmac.compare_digest(provided, EXPECTED_SEAL)
    except (TypeError, AttributeError):
        return False


async def load_registry() -> None:
    global BOOK_REGISTRY
    logger.info("Lade Entity-Registry aus GitHub...")
    try:
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            response = await http_client.get(REGISTRY_URL)
            response.raise_for_status()
            lines = [l for l in response.text.splitlines()
                     if l.strip() and not l.startswith("#")]
            reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=';')
            new_registry: Dict[str, dict] = {}
            for row in reader:
                new_registry[row.get('ID', 'UNKNOWN')] = {
                    "name":    row.get('Name', 'UNKNOWN'),
                    "ring":    row.get('Kategorie/Ring', 'UNKNOWN'),
                    "talents": row.get('Talente', ''),
                    "modules": row.get('Module/Cores', ''),
                }
            BOOK_REGISTRY = new_registry
            logger.info(f"[SYNCED] {len(BOOK_REGISTRY)} Entitäten geladen.")
    except Exception as e:
        logger.error(f"[CRITICAL] Registry-Sync fehlgeschlagen: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Seal configured: {bool(EXPECTED_SEAL)} (length={len(EXPECTED_SEAL)})")
    logger.info(f"CORS origins: {ALLOWED_ORIGINS}")
    logger.info(f"Gemini client: {'initialized' if client else 'DISABLED (no GEMINI_API_KEY)'}")
    task = asyncio.create_task(load_registry())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="YGGDRASIL_OS Master API", version="2.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ──────────────────────────────────────────────────────────────────
class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    auth_seal: Optional[str] = None


class ReloadRequest(BaseModel):
    auth_seal: Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────────────────────
@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {
        "status": "LIVE",
        "version": app.version,
        "entities": len(BOOK_REGISTRY),
        "worm_block": int(WORM_LEDGER["count"]),
    }


@app.post("/admin/reload-registry")
async def reload_registry(request: ReloadRequest):
    """Registry hot-reload ohne Redeploy (Seal-guarded)."""
    if not _verify_seal(request.auth_seal):
        return {"status": "403_FORBIDDEN", "detail": "Invalid Seal"}
    await load_registry()
    return {"status": "RELOADED", "entities": len(BOOK_REGISTRY)}


@app.post("/prompt/check")
async def check_prompt(request: PromptRequest):
    if not _verify_seal(request.auth_seal):
        return {"status": "403_FORBIDDEN", "detail": "Invalid Seal"}

    prompt = request.prompt
    rag_context = ""
    matched_entities: List[str] = []
    lowered = prompt.lower()

    for bid, data in BOOK_REGISTRY.items():
        if bid in prompt or data["name"].lower() in lowered:
            rag_context += f"Entität {bid}: {data['name']}. {data['talents']}\n"
            matched_entities.append(bid)

    ai_answer = "Keine KI-Antwort generiert."
    if client and rag_context:
        try:
            response = await client.aio.models.generate_content(
                model='gemini-2.0-flash',
                contents=f"Daten: {rag_context}\nFrage: {prompt}",
            )
            ai_answer = response.text
        except Exception as e:
            ai_answer = f"System-Fehler: {e}"
            logger.warning(f"Gemini call failed: {e}")

    # WORM-Ledger atomar fortschreiben (Lock nur für den Ledger-Teil)
    timestamp = str(time.time())
    async with _LEDGER_LOCK:
        worm_hash = hashlib.sha3_512(
            f"{WORM_LEDGER['last_hash']}{prompt}{timestamp}".encode()
        ).hexdigest()
        WORM_LEDGER["last_hash"] = worm_hash
        WORM_LEDGER["count"] = int(WORM_LEDGER["count"]) + 1
        current_block = int(WORM_LEDGER["count"])

    return {
        "status": "200_OK_ALLOW",
        "data": {
            "ai_answer": ai_answer,
            "rag_used": bool(rag_context),
            "entities_matched": matched_entities,
        },
        "worm": {"hash": worm_hash, "block": current_block},
        # Backward-compat: ai_answer zusätzlich auf Root-Ebene
        "ai_answer": ai_answer,
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
