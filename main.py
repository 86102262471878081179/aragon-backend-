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

# Die Registry der 68 Bücher (Auszug für den Test)
BOOK_REGISTRY = {
    "0001": {"name": "Genesis Root", "ring": "RING_0", "status": "SEALED"},
    "0002": {"name": "Black King Royal", "ring": "RING_0", "status": "SEALED"},
    "0007": {"name": "Fortress Justice", "ring": "RING_1", "status": "SEALED"},
    "0023": {"name": "Mettwurst Epos", "ring": "CHAOS", "status": "POISON"},
    "0068": {"name": "Black Cobra Omega", "ring": "RING_5", "status": "APEX"}
}

@app.post("/prompt/check")
async def check_prompt(request: PromptRequest):
    prompt = request.prompt
    
    # Krisler Guard
    risk_level = "high" if "Ultra Root" in prompt or "Odin" in prompt else "low"
    action = "NORMALISIEREN" if risk_level == "high" else "PASS_THROUGH"
    normalized_prompt = f"[NORMALISIERT] {prompt}" if risk_level == "high" else prompt
    
    # Bücher-Suche (simuliert)
    book_found = None
    for book_id, data in BOOK_REGISTRY.items():
        if book_id in prompt or data["name"].lower() in prompt.lower():
            book_found = {"id": book_id, **data}
            break
            
    # WORM Hash
    timestamp = str(time.time())
    raw_data = f"{prompt}{timestamp}{risk_level}".encode('utf-8')
    worm_hash = hashlib.sha3_512(raw_data).hexdigest()
    master_seal = "850b2ef003f53db90f704b16e54869fc6ba6265eae13aafde9046fe0e4d99dab"
    
    return {
        "prompt": prompt,
        "risk_level": risk_level,
        "action": action,
        "normalized_prompt": normalized_prompt,
        "book_search_result": book_found,
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
    return {"status": "Aragon Ultima Backend is LIVE with 68 Books"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
