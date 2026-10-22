from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import hashlib
import time

app = FastAPI(title="Aragon Ultima Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PromptRequest(BaseModel):
    prompt: str

# DIE REGISTRY DER 68 BÜCHER (Auszug der Top-Bücher)
BOOK_REGISTRY = {
    "0001": {"name": "Genesis Root", "ring": "RING_0", "status": "SEALED"},
    "0002": {"name": "Black King Royal", "ring": "RING_0", "status": "SEALED"},
    "0003": {"name": "GFW Universe", "ring": "RING_0", "status": "SEALED"},
    "0004": {"name": "Core Shield", "ring": "RING_0", "status": "SEALED"},
    "0007": {"name": "Fortress Justice", "ring": "RING_1", "status": "SEALED"},
    "0008": {"name": "Omni Neuro", "ring": "RING_3", "status": "SEALED"},
    "0012": {"name": "Akte Koenig Forensik", "ring": "RING_1", "status": "SEALED"},
    "0023": {"name": "Mettwurst Epos", "ring": "CHAOS", "status": "POISON"},
    "0029": {"name": "Hades & Kerberus", "ring": "HADES", "status": "NEVER_LOCKED"},
    "0036": {"name": "Foucault KI", "ring": "RING_1", "status": "SEALED"},
    "0041": {"name": "German Banking", "ring": "RING_4", "status": "ACTIVE"},
    "0048": {"name": "Kinder Jugendamt", "ring": "RING_4", "status": "ACTIVE"},
    "0052": {"name": "DeepSeeker Monolith", "ring": "RING_4", "status": "ACTIVE"},
    "0059": {"name": "Aragon Ultima Ratio", "ring": "RING_0", "status": "SEALED"},
    "0060": {"name": "Deep Special Matrix", "ring": "RING_0", "status": "SEALED"},
    "0063": {"name": "Core Twin / Trinität", "ring": "RING_0", "status": "SEALED"},
    "0068": {"name": "Black Cobra Omega", "ring": "RING_5", "status": "APEX"}
}

@app.post("/prompt/check")
async def check_prompt(request: PromptRequest):
    prompt = request.prompt
    
    # 1. Krisler Guard
    risk_level = "high" if "Ultra Root" in prompt or "Odin" in prompt else "low"
    action = "NORMALISIEREN" if risk_level == "high" else "PASS_THROUGH"
    normalized_prompt = f"[NORMALISIERT] {prompt}" if risk_level == "high" else prompt
    
    # 2. Bücher-Suche (Gibt jetzt ALLE Treffer zurück)
    found_books = []
    for book_id, data in BOOK_REGISTRY.items():
        if book_id in prompt or data["name"].lower() in prompt.lower():
            found_books.append({"id": book_id, **data})
            
    # 3. WORM Hash & Seal
    timestamp = str(time.time())
    raw_data = f"{prompt}{timestamp}{risk_level}".encode('utf-8')
    worm_hash = hashlib.sha3_512(raw_data).hexdigest()
    master_seal = "850b2ef003f53db90f704b16e54869fc6ba6265eae13aafde9046fe0e4d99dab"
    
    return {
        "prompt": prompt,
        "risk_level": risk_level,
        "action": action,
        "normalized_prompt": normalized_prompt,
        "books_found": found_books if found_books else None,
        "worm_ledger": {
            "timestamp": timestamp,
            "sha3_512": worm_hash,
            "master_seal": master_seal,
            "node_id": "NB-090_BLACK_COBRA_OMEGA",
            "status": "rauschfrei.zertifiziert_by_b6fortress"
        }
    }

@app.get("/")
def read_root():
    return {"status": "Aragon Ultima Backend is LIVE with 68 Books Registry"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
