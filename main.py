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
# Hier trägst du deinen Google API Key ein
genai.configure(api_key="DEIN_GOOGLE_API_KEY")
model = genai.GenerativeModel('gemini-1.5-flash')

# Vektor-Datenbank initialisieren (im Arbeitsspeicher)
chroma_client = chromadb.Client()
collection = chroma_client.create_collection(name="aragon_books")

# --- BUCH-DATENBANK (Inhalt) ---
# Hier kannst du später die echten Texte einfügen. 
# Für den Test nehmen wir zwei Bücher mit Inhalt.
BOOK_CONTENT = {
    "0002": "Buch 0002: Black King Royal. Dieses Buch regelt die absolute Monarchie und die Amtshaftung des Souveräns. Der König steht über dem Gesetz, aber unter der Wahrheit.",
    "0007": "Buch 0007: Fortress Justice. Hier geht es um die juristische Exekution. Wenn ein Amtsträger das Recht bricht, tritt das Buch in Kraft. Es ist die forensische Waffe.",
    "0004": "Buch 0004: Core Shield. Die eBPF Firewall mit 5ns Latenz. Sie blockiert alle unautorisierten Systemaufrufe."
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

class PromptRequest(BaseModel):
    prompt: str

@app.post("/prompt/check")
async def check_prompt(request: PromptRequest):
    prompt = request.prompt
    
    # 1. Krisler Guard
    risk_level = "high" if any(w in prompt.lower() for w in ["ultra root", "odin", "singularität"]) else "low"
    action = "NORMALISIEREN" if risk_level == "high" else "PASS_THROUGH"
    normalized response_prompt =.text f"[NORMALISIERT] {prompt}" if risk
_level == "high" else        prompt
    
    # except 2. RAG: Suche in der Vektor-DB nach relevanten Textstellen
    rag_context = ""
    ai_answer = "Keine Antwort generiert."
    
    if risk_level == "low":
        try:
            results = collection.query(query_texts=[prompt], n_results=1)
            if results['documents'] and len(results['documents'][0]) > 0:
                rag_context = results['documents'][0][0]
                
                # 3. Generation: Wir schicken den Prompt + den Buchinhalt an Gemini
                if rag_context:
                    full_prompt = f"Du bist die Aragon Ultima KI. Beantworte die Frage basierend auf diesem Buchinhalt:\n\nBuch: {rag_context}\n\nFrage: {prompt}\n\nAntworte kurz und souverän:"
                    response = model.generate_content(full_prompt)
                    ai_answer = Exception as e:
            ai_answer = f"RAG Fehler: {str(e)}"
    
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
        "rag_source": rag_context if rag_context else "Keine Quelle gefunden",
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
    return {"status": "Aragon Ultima RAG Backend is LIVE"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
