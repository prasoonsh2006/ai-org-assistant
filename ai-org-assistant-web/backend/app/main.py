from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .config import CORS_ORIGINS
from .services.llm_service import general_chat
from .services.code_tools import multi_decode

app = FastAPI(title="AI Organization Assistant API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []

@app.post("/api/tools/multi-decode")
def multi_decode_api(payload: dict):
    value = str(payload.get("value",""))
    if not value:
        raise HTTPException(status_code=400, detail="value is required")
    return {"results": multi_decode(value)}

@app.get("/api/tools")
def tools():
    return {"tools":[
        "multi-decoder","json-formatter","base64","url-encoder-decoder",
        "jwt-inspector","regex-tester","timestamp-converter","hash-generator",
        "code-explainer","code-reviewer","sql-assistant","document-analyzer"
    ]}

@app.get("/api/health")
def health():
    return {"status":"ok","service":"ai-org-assistant"}

@app.post("/api/chat")
def chat(payload: ChatRequest):
    try:
        return {"answer": general_chat(payload.message, payload.history)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
