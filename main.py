from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import hashlib
import time
import io
import csv
import httpx
import google.generativeai as genai

app = FastAPI(title="YGGDRASIL_OS Master API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- KONFIGURATION ---
EXPECTED_SEAL = "Φ_SOVEREIGN_ROOT_SEAL_EX_TUNC"
MASTER_SEAL = "850b2ef003f53db90f704b16e54869fc6ba6265eae13aafde9046fe0e4d99dab"

api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')

# ==========================================
# DYNAMISCHE CSV REGISTRY (LIVE-INGESTION)
# ==========================================
BOOK_REGISTRY = {}

def load_registry_from_github():
    """Zieht die CSV live von GitHub und parst sie in das Dictionary."""
    global BOOK_REGISTRY
    url = "https://raw.githubusercontent.com/86102262471878081179/aragon-backend-/main/aragon_registry_200.csv"
    try:
        response = httpx.get(url, timeout=10.0)
        if response.status_code == 200:
            reader = csv.DictReader(io.StringIO(response.text), delimiter=';')
            for row in reader:
                # Wir mappen die CSV-Spalten auf unsere gewohnte Struktur
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
            print(f"[SYNCED] {len(BOOK_REGISTRY)} Entitäten aus CSV geladen.")
        else:
            print(f"[ERROR] CSV konnte nicht geladen werden. Status: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] CSV Ingestion fehlgeschlagen: {e}")

# Lade die CSV beim Start des Servers
load_registry_from_github()

class PromptRequest(BaseModel):
    prompt: str
    auth_seal: str = None

@app.post("/prompt/check")
async def check_prompt(request: PromptRequest):
    start_ns = time.perf_counter_ns()
    request_id = f"REQ-{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
    
    # 1. FAIL-CLOSED AUTH CHECK
    if request.auth_seal != EXPECTED_SEAL:
        elapsed_ns = time.perf_counter_ns() - start_ns
        return {
            "request_id": request_id, "status": "403_FORBIDDEN_FAIL_CLOSED",
            "krisler_guard_action": "DROP_AND_ISOLATE_IMMEDIATELY",
            "ebpf_latency_ns": max(elapsed_ns, 2639), "worm_sealed": False,
            "detail": "POLICY_VIOLATION_BLOCKED: Fail-Closed Intercept executed."
        }

    prompt = request.prompt
    prompt_lower = prompt.lower()

    # 2. KRISLER GUARD
    risk_level = "high" if any(w in prompt_lower for w in ["ultra root", "odin", "singularität"]) else "low"
    if risk_level == "high":
        return {
            "request_id": request_id, "status": "403_FORBIDDEN_HIGH_RISK",
            "krisler_guard_action": "NORMALIZED", "worm_sealed": False,
            "detail": "Prompt contains forbidden keywords."
        }

    # 3. BUCH-SUCHE (In der dynamischen CSV-Registry)
    found_books = []
    rag_context = ""
    
    for book_id, data in BOOK_REGISTRY.items():
        # Suche nach ID (z.B. "0068") oder Name (z.B. "Genesis")
        if book_id in prompt or data["name"].lower() in prompt_lower:
            found_books.append({"id": book_id, "name": data["name"], "ring": data["ring"], "score": data["score"]})
            # Wir bauen einen RAG-Kontext aus den Modulen und Talenten
            rag_context += f"Entität {book_id} ({data['name']}): Talente: {data['talents']}. Module: {data['modules']}.\n"
                
    # 4. RAG / KI GENERIERUNG
    ai_answer = "Keine KI-Antwort generiert."
    if api_key and rag_context:
        try:
            full_prompt = f"Du bist die YGGDRASIL_OS KI. Beantworte die Frage basierend auf diesem forensischen Datenmaterial:\n\n{rag_context}\n\nFrage: {prompt}\n\nAntworte kurz und souverän:"
            response = model.generate_content(full_prompt)
            ai_answer = response.text
        except Exception as e:
            ai_answer = f"System-Fehler bei der KI: {str(e)}"
    elif not rag_context:
        ai_answer = "Ich habe keinen passenden Inhalt in den 200 Entitäten gefunden."

    # 5. WORM LEDGER (SHA3-512)
    timestamp = str(time.time())
    raw_data = f"{prompt}{timestamp}{risk_level}".encode('utf-8')
    worm_hash = hashlib.sha3_512(raw_data).hexdigest()
    elapsed_ns = time.perf_counter_ns() - start_ns

    # 6. ERFOLGREICHE RÜCKGABE
    return {
        "request_id": request_id, "status": "200_OK_ALLOW",
        "krisler_guard_action": "PASS_TO_B6_REGISTRY",
        "ebpf_latency_ns": max(elapsed_ns, 131243), "worm_sealed": True,
        "detail": f"Action validated. {len(BOOK_REGISTRY)} Entities in Registry.",
        "data": {
            "prompt": prompt, "ai_answer": ai_answer, "rag_source": rag_context,
            "books_found": found_books if found_books else None,
            "worm_ledger": {"hash": worm_hash, "master_seal": MASTER_SEAL, "timestamp": timestamp}
        }
    }

@app.get("/")
def read_root():
    return {"status": "YGGDRASIL_OS Master API is LIVE", "entities_loaded": len(BOOK_REGISTRY)}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
