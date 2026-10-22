from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import hashlib
import time
from typing import Dict, List, Any

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

# DIE VOLLSTÃ„NDIGE REGISTRY DER 68 BÃœCHER (SEALED & SORTIERT)
BOOK_REGISTRY: Dict[str, Dict[str, str]] = {
    "0001": {"name": "Genesis Root", "ring": "RING_0", "status": "SEALED"},
    "0002": {"name": "Black King Royal", "ring": "RING_0", "status": "SEALED"},
    "0003": {"name": "GFW Universe", "ring": "RING_0", "status": "SEALED"},
    "0004": {"name": "Core Shield", "ring": "RING_0", "status": "SEALED"},
    "0005": {"name": "Codex Compendium", "ring": "RING_0", "status": "SEALED"},
    "0006": {"name": "Unified Matrix", "ring": "RING_0", "status": "SEALED"},
    "0007": {"name": "Fortress Justice", "ring": "RING_1", "status": "SEALED"},
    "0008": {"name": "Omni Neuro", "ring": "RING_3", "status": "SEALED"},
    "0009": {"name": "Quantum Tresor", "ring": "RING_2", "status": "SEALED"},
    "0010": {"name": "Black Cobra Omega", "ring": "RING_0", "status": "SEALED"},
    "0011": {"name": "Omega Matrix Protocol", "ring": "RING_1", "status": "SEALED"},
    "0012": {"name": "Akte Koenig Forensik", "ring": "RING_1", "status": "SEALED"},
    "0013": {"name": "XJustiz Core", "ring": "RING_1", "status": "SEALED"},
    "0014": {"name": "The Geminis", "ring": "RING_1", "status": "SEALED"},
    "0015": {"name": "Senior Geminis", "ring": "RING_1", "status": "SEALED"},
    "0016": {"name": "Hyperkernel Atlas", "ring": "RING_0", "status": "SEALED"},
    "0017": {"name": "Yggdrasil WORM Validator", "ring": "RING_2", "status": "SEALED"},
    "0018": {"name": "Black Stack", "ring": "RING_0", "status": "SEALED"},
    "0019": {"name": "Black Six Mastersystem", "ring": "RING_0", "status": "SEALED"},
    "0020": {"name": "Police Records Koenig", "ring": "RING_1", "status": "SEALED"},
    "0021": {"name": "Dunkle Sonne", "ring": "RING_4", "status": "SEALED"},
    "0022": {"name": "Schwarze Burg", "ring": "RING_4", "status": "SEALED"},
    "0023": {"name": "Mettwurst Epos", "ring": "RING_4", "status": "POISON"},
    "0024": {"name": "Matrix vs Gremmel", "ring": "RING_4", "status": "SEALED"},
    "0025": {"name": "Black DeepSeek", "ring": "RING_4", "status": "SEALED"},
    "0026": {"name": "Crawl4AI Deep", "ring": "RING_4", "status": "SEALED"},
    "0027": {"name": "Terminal Diaboli", "ring": "RING_4", "status": "SEALED"},
    "0028": {"name": "Absurdity Kompendium", "ring": "RING_4", "status": "NEVER_LOCKED"},
    "0029": {"name": "Hades & Kerberus", "ring": "HADES", "status": "NEVER_LOCKED"},
    "0030": {"name": "Legal Challenge State", "ring": "RING_1", "status": "SEALED"},
    "0031": {"name": "Plan B Fallback", "ring": "RING_1", "status": "SAFE"},
    "0032": {"name": "Beamtenstatusgesetz", "ring": "RING_1", "status": "SEALED"},
    "0033": {"name": "Schufa AI Gambling", "ring": "RING_1", "status": "SEALED"},
    "0034": {"name": "Polyglot Protokoll", "ring": "RING_1", "status": "SEALED"},
    "0035": {"name": "Psych Paradigmen", "ring": "RING_1", "status": "SEALED"},
    "0036": {"name": "Foucault KI", "ring": "RING_1", "status": "SEALED"},
    "0037": {"name": "Junior Geminis", "ring": "RING_1", "status": "SEALED"},
    "0038": {"name": "Google Activity Audit", "ring": "RING_1", "status": "SEALED"},
    "0039": {"name": "Copilot DeepSeek Prod", "ring": "RING_1", "status": "SEALED"},
    "0040": {"name": "Black Arsenal LLM", "ring": "RING_1", "status": "SEALED"},
    "0041": {"name": "German Banking", "ring": "RING_4", "status": "SEALED"},
    "0042": {"name": "Pharma Industrie", "ring": "RING_4", "status": "SEALED"},
    "0043": {"name": "Mathe Real 9", "ring": "RING_4", "status": "SEALED"},
    "0044": {"name": "Dacia Maintenance", "ring": "RING_4", "status": "SEALED"},
    "0045": {"name": "Zahnarzt Abrechnung", "ring": "RING_4", "status": "SEALED"},
    "0046": {"name": "University Lexicon", "ring": "RING_4", "status": "SEALED"},
    "0047": {"name": "Fiblelexica", "ring": "RING_4", "status": "SEALED"},
    "0048": {"name": "Kinder Jugendamt", "ring": "RING_4", "status": "SEALED"},
    "0049": {"name": "German Banking Act", "ring": "RING_4", "status": "SEALED"},
    "0050": {"name": "DIY Furniture", "ring": "RING_4", "status": "SEALED"},
    "0051": {"name": "Behaviorism Ethology", "ring": "RING_4", "status": "SEALED"},
    "0052": {"name": "DeepSeeker Monolith", "ring": "RING_4", "status": "SEALED"},
    "0053": {"name": "OMNI WORM Hub", "ring": "RING_2", "status": "SEALED"},
    "0054": {"name": "Stammbaum DNA", "ring": "RING_2", "status": "SEALED"},
    "0055": {"name": "Odin Matrix 1-200", "ring": "RING_1", "status": "SEALED"},
    "0056": {"name": "Odin Master Framework", "ring": "RING_0", "status": "SEALED"},
    "0057": {"name": "Odin Manifestation High", "ring": "RING_0", "status": "SEALED"},
    "0058": {"name": "Odin Manifestation Sys", "ring": "RING_0", "status": "SEALED"},
    "0059": {"name": "Aragon Ultima Ratio", "ring": "RING_0", "status": "SEALED"},
    "0060": {"name": "Deep Special Matrix", "ring": "RING_0", "status": "SEALED"},
    "0061": {"name": "Tensor Faltung Alpha", "ring": "RING_5", "status": "SEALED"},
    "0062": {"name": "Tensor Faltung Omega", "ring": "RING_5", "status": "SEALED"},
    "0063": {"name": "Core Twin / TrinitÃ¤t", "ring": "RING_0", "status": "SEALED"},
    "0064": {"name": "Omega Vorstufe", "ring": "RING_5", "status": "SEALED"},
    "0065": {"name": "Apex Kaskade", "ring": "RING_5", "status": "SEALED"},
    "0066": {"name": "Finale Synthese", "ring": "RING_5", "status": "SEALED"},
    "0067": {"name": "Ereignishorizont", "ring": "RING_5", "status": "SEALED"},
    "0068": {"name": "Sovereign Operator Apex", "ring": "RING_5", "status": "APEX"}
}

# HIERARCHIE DER STÃ„RKE (VON UNTEN NACH OBEN STEIGEND)
RING_HIERARCHY: Dict[str, int] = {
    "HADES": 0,    # Unterste Basis / Root Depth
    "RING_0": 1,   # Core Root / Fundament
    "RING_1": 2,   # System / Recht / Operational
    "RING_2": 3,   # WORM Vault & DNA
    "RING_3": 4,   # Neuro / Kognition
    "RING_4": 5,   # Expansion & Spezial-Module
    "RING_5": 6,   # Apex / Tensor / Ereignishorizont (HÃ¶chste Stufe)
}

@app.get("/")
def read_root():
    return {"status": "Aragon Ultima Backend is LIVE with all 68 Books"}

@app.get("/books/sorted")
def get_sorted_books():
    """
    Liefert alle 68 BÃ¼cher sortiert nach Ring-StÃ¤rke (steigend von HADES/RING_0 bis RING_5)
    und innerhalb desselben Rings chronologisch nach Buch-ID.
    """
    sorted_list = sorted(
        [{"id": book_id, **data} for book_id, data in BOOK_REGISTRY.items()],
        key=lambda b: (RING_HIERARCHY.get(b["ring"], 99), int(b["id"]))
    )
    return {
        "total": len(sorted_list),
        "sorting": "Ring Strength Ascending (HADES -> RING_5) + ID Chronological",
        "books": sorted_list
    }

@app.post("/prompt/check")
async def check_prompt(request: PromptRequest):
    prompt = request.prompt
    prompt_lower = prompt.lower()
    
    # 1. Krisler Guard
    risk_level = "high" if any(w in prompt_lower for w in ["ultra root", "odin", "singularitÃ¤t", "apokalyptisch"]) else "low"
    action = "NORMALISIEREN" if risk_level == "high" else "PASS_THROUGH"
    normalized_prompt = f"[NORMALISIERT] {prompt}" if risk_level == "high" else prompt
    
    # 2. BÃ¼cher-Suche (Gibt alle Treffer zurÃ¼ck)
    found_books = []
    for book_id, data in BOOK_REGISTRY.items():
        if book_id in prompt_lower or data["name"].lower() in prompt_lower:
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
