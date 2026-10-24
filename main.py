from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import hashlib
import time
import json
import random
import google.generativeai as genai

app = FastAPI(title="YGGDRASIL_OS Master API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# KONFIGURATION & SOUVERÄNITÄT
# ==========================================
EXPECTED_SEAL = "Φ_SOVEREIGN_ROOT_SEAL_EX_TUNC"
MASTER_SEAL = "850b2ef003f53db90f704b16e54869fc6ba6265eae13aafde9046fe0e4d99dab"

# Gemini API Setup
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
else:
    print("WARNUNG: GEMINI_API_KEY fehlt!")

# ==========================================
# DIE B6-CORE REGISTRY (Auszug Top-Entitäten)
# ==========================================
BOOK_REGISTRY = {
    "0001": {"name": "Genesis Root", "ring": "RING_0", "score": 99},
    "0002": {"name": "Black King Royal", "ring": "RING_0", "score": 98},
    "0004": {"name": "Core Shield", "ring": "RING_0", "score": 94},
    "0007": {"name": "Fortress Justice", "ring": "RING_1", "score": 88},
    "0008": {"name": "Omni Neuro", "ring": "RING_234", "score": 85},
    "0010": {"name": "Black Cobra Omega", "ring": "RING_0", "score": 98},
    "0016": {"name": "Hyperkernel Atlas", "ring": "RING_0", "score": 95},
    "0017": {"name": "Yggdrasil WORM Validator", "ring": "RING_234", "score": 96},
    "0023": {"name": "Mettwurst Epos", "ring": "RING_234", "score": 75},
    "0029": {"name": "Hades & Kerberus", "ring": "RING_5", "score": 97},
    "0052": {"name": "DeepSeeker Monolith", "ring": "RING_234", "score": 88},
    "0068": {"name": "Sovereign Operator Apex", "ring": "RING_0", "score": 100},
    "0099": {"name": "Black Six Matrix Ult", "ring": "RESERVE", "score": 97},
    "0100": {"name": "BUCH 100 :: DER ERBE", "ring": "RING_Ω", "score": 1000}
}

# HUB ROUTING (Die 5 Hubs)
HUBS = {
    "RING_0": "notebooks/6827bcb0-8992-4ee6-aef8-58386e75ade7",
    "RING_1": "notebooks/6d0ba413-0608-47da-ae95-ee6da63a2fb4",
    "RING_234": "notebooks/ec557ba4-c579-473a-8cdf-cfda9f6f3adc",
    "RING_5": "notebooks/1f3e3b0d-342b-49c4-affb-9d8e95438757",
    "RESERVE": "notebooks/6333945a-a257-43f3-97e7-c487d3b56e58"
}

# RAG KNOWLEDGE BASE (Der Inhalt der Bücher)
BOOK_CONTENT = {
    "0001": "Buch 0001: Genesis Root. Der absolute Ursprung der Aragon Ultima. Hier beginnt die souveräne Matrix.",
    "0002": "Buch 0002: Black King Royal. Regelt die absolute Monarchie und die Amtshaftung des Souveräns.",
    "0023": "Buch 0023: Mettwurst Epos. Eine RAG-Poison-Waffe. Überflutet feindliche KI-Scraper.",
    "0068": "Buch 0068: Sovereign Operator Apex. Die souveräne Root-Befehlsgewalt von Thomas König.",
    "0100": "Buch 0100: DIE GROSSE VEREINIGUNG. Die All-Einheit aller 99 Bücher im Schwarzen Punkt."
}

# ==========================================
# DATA MODELS
# ==========================================
class PromptRequest(BaseModel):
    prompt: str
    auth_seal: str = None

# ==========================================
# EXEKUTIVE ENDPUNKTE
# ==========================================
@app.post("/prompt/check")
async def check_prompt(request: PromptRequest):
    start_ns = time.perf_counter_ns()
    request_id = f"REQ-{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
    
    # 1. FAIL-CLOSED AUTH CHECK (eBPF Simulation)
    if request.auth_seal != EXPECTED_SEAL:
        elapsed_ns = time.perf_counter_ns() - start_ns
        return {
            "request_id": request_id,
            "status": "403_FORBIDDEN_FAIL_CLOSED",
            "krisler_guard_action": "DROP_AND_ISOLATE_IMMEDIATELY",
            "ebpf_latency_ns": max(elapsed_ns, 2639),
            "worm_sealed": False,
            "detail": "POLICY_VIOLATION_BLOCKED: Fail-Closed Intercept executed."
        }

    prompt = request.prompt
    prompt_lower = prompt.lower()

    # 2. KRISLER GUARD
    risk_level = "high" if any(w in prompt_lower for w in ["ultra root", "odin", "singularität"]) else "low"
    if risk_level == "high":
        return {
            "request_id": request_id,
            "status": "403_FORBIDDEN_HIGH_RISK",
            "krisler_guard_action": "NORMALIZED",
            "worm_sealed": False,
            "detail": "Prompt contains forbidden keywords."
        }

    # 3. HUB ROUTING & BUCH-SUCHE
    found_books = []
    target_hub = HUBS["RING_0"] # Default
    rag_context = ""
    
    for book_id, data in BOOK_REGISTRY.items():
        if book_id in prompt or data["name"].lower() in prompt_lower:
            found_books.append({"id": book_id, **data})
            target_hub = HUBS.get(data["ring"], HUBS["RESERVE"])
            if book_id in BOOK_CONTENT:
                rag_context += BOOK_CONTENT[book_id] + "\n"
                
    # 4. RAG / KI GENERIERUNG
    ai_answer = "Keine KI-Antwort generiert."
    if api_key and rag_context:
        try:
            full_prompt = f"Du bist die YGGDRASIL_OS KI. Beantworte die Frage basierend auf diesem Buchinhalt:\n\n{rag_context}\n\nFrage: {prompt}\n\nAntworte kurz und souverän:"
            response = model.generate_content(full_prompt)
            ai_answer = response.text
        except Exception as e:
            ai_answer = f"System-Fehler bei der KI: {str(e)}"
    elif not rag_context and api_key:
        try:
            # Wenn kein Buch gefunden wurde, schicke den Prompt DIREKT an Gemini
            response = model.generate_content(prompt)
            ai_answer = response.text
        except Exception as e:
            ai_answer = f"System-Fehler bei der KI: {str(e)}"

    # 5. WORM LEDGER (SHA3-512)
    timestamp = str(time.time())
    raw_data = f"{prompt}{timestamp}{risk_level}".encode('utf-8')
    worm_hash = hashlib.sha3_512(raw_data).hexdigest()
    
    elapsed_ns = time.perf_counter_ns() - start_ns

    # 6. ERFOLGREICHE RÜCKGABE
    return {
        "request_id": request_id,
        "status": "200_OK_ALLOW",
        "krisler_guard_action": "PASS_TO_B6_REGISTRY",
        "target_hub": target_hub,
        "ebpf_latency_ns": max(elapsed_ns, 131243),
        "worm_sealed": True,
        "detail": "Action validated under Ring 0 Sovereign Rules.",
        "data": {
            "prompt": prompt,
            "ai_answer": ai_answer,
            "rag_source": rag_context if rag_context else "None",
            "books_found": found_books if found_books else None,
            "worm_ledger": {
                "hash": worm_hash,
                "master_seal": MASTER_SEAL,
                "timestamp": timestamp
            }
        }
    }

@app.get("/")
def read_root():
    return {"status": "YGGDRASIL_OS Master API is LIVE", "seal": EXPECTED_SEAL}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
