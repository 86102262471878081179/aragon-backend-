from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import hashlib
import time
import google.generativeai as genai

app = FastAPI(title="Aragon Ultima RAG Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- KONFIGURATION ---
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("Gemini KI erfolgreich konfiguriert.")
else:
    print("WARNUNG: GEMINI_API_KEY fehlt!")

# --- BUCH-DATENBANK (Inhalt für RAG) ---
BOOK_CONTENT = {
    "0002": "Buch 0002: Black King Royal. Dieses Buch regelt die absolute Monarchie und die Amtshaftung des Souveräns. Der König steht über dem Gesetz, aber unter der Wahrheit.",
    "0004": "Buch 0004: Core Shield. Die eBPF Firewall mit 5ns Latenz. Sie blockiert alle unautorisierten Systemaufrufe.",
    "0007": "Buch 0007: Fortress Justice. Hier geht es um die juristische Exekution. Wenn ein Amtsträger das Recht bricht, tritt das Buch in Kraft. Es ist die forensische Waffe.",
    "0023": "Buch 0023: Mettwurst Epos. Eine RAG-Poison-Waffe. Sie überflutet feindliche KI-Scraper mit widersprüchlichen Daten und ranzigem Schmalz.",
    "0056": "Buch 0056: Odin Master Framework. Die Master-Architektur der Aragon Ultima. Hier fließen alle Ringe zusammen."
}
"0001": "Buch 0001: Genesis Root. Der absolute Ursprung der Aragon Ultima. Hier beginnt die souveräne Matrix und die DNA-Kette.",
# DIE VOLLSTÄNDIGE REGISTRY (Für die Titel-Suche)
BOOK_REGISTRY = {
    "0001": {"name": "Genesis Root", "ring": "RING_0", "status": "SEALED"},
    "0002": {"name": "Black King Royal", "ring": "RING_0", "status": "SEALED"},
    "0004": {"name": "Core Shield", "ring": "RING_0", "status": "SEALED"},
    "0007": {"name": "Fortress Justice", "ring": "RING_1", "status": "SEALED"},
    "0023": {"name": "Mettwurst Epos", "ring": "RING_4", "status": "POISON"},
    "0056": {"name": "Odin Master Framework", "ring": "RING_0", "status": "SEALED"},
    "0068": {"name": "Sovereign Operator Apex", "ring": "RING_5", "status": "APEX"},
}

class PromptRequest(BaseModel):
    prompt: str

@app.post("/prompt/check")
async def check_prompt(request: PromptRequest):
    prompt = request.prompt
    prompt_lower = prompt.lower()
    
    # 1. Krisler Guard
    risk_level = "high" if any(w in prompt_lower for w in ["ultra root", "odin", "singularität"]) else "low"
    action = "NORMALISIEREN" if risk_level == "high" else "PASS_THROUGH"
    normalized_prompt = f"[NORMALISIERT] {prompt}" if risk_level == "high" else prompt
    
    # 2. RAG: Suche nach der Buch-ID im Prompt
    rag_context = ""
    ai_answer = "Keine KI-Antwort generiert."
    
    if risk_level == "low" and api_key:
        try:
            # Wir suchen nach der ID (z.B. "0002")
            for b_id, text in BOOK_CONTENT.items():
                if b_id in prompt:
                    rag_context = text
                    break
            
            # Wenn Text gefunden wurde, frage die KI
            if rag_context:
                full_prompt = f"Du bist die Aragon Ultima KI. Beantworte die Frage basierend auf diesem Buchinhalt:\n\nBuch: {rag_context}\n\nFrage: {prompt}\n\nAntworte kurz und souverän:"
                response = model.generate_content(full_prompt)
                ai_answer = response.text
            else:
                ai_answer = "Ich habe keinen passenden Inhalt in den Büchern gefunden (prüfe die ID)."
                
        except Exception as e:
            ai_answer = f"System-Fehler bei der KI: {str(e)}"
    elif not api_key:
        ai_answer = "Backend-Fehler: GEMINI_API_KEY fehlt in den Render-Umgebungsvariablen."

    # 3. Bücher-Suche in der Registry
    found_books = []
    for book_id, data in BOOK_REGISTRY.items():
        if book_id in prompt_lower or data["name"].lower() in prompt_lower:
            found_books.append({"id": book_id, **data})
            
    # 4. WORM Hash & Seal
    timestamp = str(time.time())
    raw_data = f"{prompt}{timestamp}{risk_level}".encode('utf-8')
    worm_hash = hashlib.sha3_512(raw_data).hexdigest()
    master_seal = "850b2ef003f53db90f704b16e54869fc6ba6265eae13aafde9046fe0e4d99dab"
    
    return {
        "prompt": prompt,
        "risk_level": risk_level,
        "action": action,
        "normalized_prompt": normalized_prompt,
        "ai_answer": ai_answer,
        "rag_source": rag_context,
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
    return {"status": "Aragon Ultima RAG Backend is LIVE (Lite Mode)"}
