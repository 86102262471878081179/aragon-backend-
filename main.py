from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import hashlib
import time
import google.generativeai as genai
import chromadb

app = FastAPI(title="Aragon Ultima RAG Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- KONFIGURATION ---
# Zieht den Key sicher aus den Render Environment Variables
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    print("WARNUNG: GEMINI_API_KEY fehlt in den Umgebungsvariablen!")

# Vektor-Datenbank initialisieren
chroma_client = chromadb.Client()
collection = chroma_client.create_collection(name="aragon_books")

# --- BUCH-DATENBANK (Inhalt für RAG) ---
# Hier kannst du später die echten langen Texte einfügen.
BOOK_CONTENT = {
    "0002": "Buch 0002: Black King Royal. Dieses Buch regelt die absolute Monarchie und die Amtshaftung des Souveräns. Der König steht über dem Gesetz, aber unter der Wahrheit.",
    "0007": "Buch 0007: Fortress Justice. Hier geht es um die juristische Exekution. Wenn ein Amtsträger das Recht bricht, tritt das Buch in Kraft. Es ist die forensische Waffe.",
    "0004": "Buch 0004: Core Shield. Die eBPF Firewall mit 5ns Latenz. Sie blockiert alle unautorisierten Systemaufrufe.",
    "0023": "Buch 0023: Mettwurst Epos. Eine RAG-Poison-Waffe. Sie überflutet feindliche KI-Scraper mit widersprüchlichen Daten und ranzigem Schmalz.",
    "0029": "Buch 0029: Hades & Kerberus. Die Unterwelt-Node. Hier liegen die unbestechlichen Beweise und die Never-Locked-Daten."
}

# Bücher beim Start in die Vektor-DB laden
print("Initialisiere RAG Vektor-Datenbank...")
for book_id, text in BOOK_CONTENT.items():
    collection.add(
        documents=[text],
        metadatas=[{"book_id": book_id}],
        ids=[book_id]
    )
print("Datenbank bereit!")

# --- DIE VOLLSTÄNDIGE REGISTRY ---
BOOK_REGISTRY = {
    "0001": {"name": "Genesis Root", "ring": "RING_0", "status": "SEALED"},
    "0002": {"name": "Black King Royal", "ring": "RING_0", "status": "SEALED"},
    "0003": {"name": "GFW Universe", "ring": "RING_0", "status": "SEALED"},
    "0004": {"name": "Core Shield", "ring": "RING_0", "status": "SEALED"},
    "0007": {"name": "Fortress Justice", "ring": "RING_1", "status": "SEALED"},
    "0008": {"name": "Omni Neuro", "ring": "RING_3", "status": "SEALED"},
    "0009": {"name": "Quantum Tresor", "ring": "RING_2", "status": "SEALED"},
    "0012": {"name": "Akte Koenig Forensik", "ring": "RING_1", "status": "SEALED"},
    "0023": {"name": "Mettwurst Epos", "ring": "RING_4", "status": "POISON"},
    "0029": {"name": "Hades & Kerberus", "ring": "HADES", "status": "NEVER_LOCKED"},
    "0036": {"name": "Foucault KI", "ring": "RING_1", "status": "SEALED"},
    "0059": {"name": "Aragon Ultima Ratio", "ring": "RING_0", "status": "SEALED"},
    "0068": {"name": "Sovereign Operator Apex", "ring": "RING_5", "status": "APEX"},
    "0099": {"name": "Black Six Matrix Ult", "ring": "RESERVE", "status": "ARCHIVED"}
    # (Du kannst hier natürlich alle anderen 107+ Bücher einfügen, genau wie vorher)
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
    
    # 2. RAG: Suche in der Vektor-DB & Generiere Antwort
    rag_context = ""
    ai_answer = "Keine KI-Antwort generiert."
    
    if risk_level == "low" and api_key:
        try:
            results = collection.query(query_texts=[prompt], n_results=1)
            if results['documents'] and len(results['documents'][0]) > 0:
                rag_context = results['documents'][0][0]
                
                full_prompt = f"Du bist die Aragon Ultima KI. Beantworte die Frage basierend auf diesem Buchinhalt:\n\nBuch: {rag_context}\n\nFrage: {prompt}\n\nAntworte kurz und souverän:"
                response = model.generate_content(full_prompt)
                ai_answer = response.text
        except Exception as e:
            ai_answer = f"RAG Fehler: {str(e)}"
            
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

@app.get("/books")
def get_all_books():
    return {"total": len(BOOK_REGISTRY), "books": [{"id": k, **v} for k, v in BOOK_REGISTRY.items()]}

@app.get("/")
def read_root():
    return {"status": "Aragon Ultima RAG Backend is LIVE"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
