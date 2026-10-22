from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

app = FastAPI(title="Aragon Ultima Backend")

# CORS-Middleware: Erlaubt dem Streamlit-Cockpit den Zugriff
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PromptRequest(BaseModel):
    prompt: str

@app.post("/prompt/check")
async def check_prompt(request: PromptRequest):
    prompt = request.prompt
    risk_level = "high" if "Ultra Root" in prompt else "low"
    action = "NORMALISIEREN" if risk_level == "high" else "PASS_THROUGH"
    
    return {
        "prompt": prompt,
        "risk_level": risk_level,
        "action": action,
        "normalized_prompt": f"[NORMALISIERT] {prompt}" if risk_level == "high" else prompt
    }

@app.get("/")
def read_root():
    return {"status": "Aragon Ultima Backend is LIVE"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
