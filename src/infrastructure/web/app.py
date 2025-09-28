# src/infrastructure/web/app.py
from typing import Any, Dict
import os
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.application.policy import Policy
from src.application.decision_engine import DecisionEngine
from src.domain.enums.decision import Decision
from src.infrastructure.adapters.rule_based_classifier import RuleBasedClassifier
from src.infrastructure.adapters.sbert_classifier import SBertClassifier
from src.infrastructure.adapters.llm_sanitizer import LLMSanitizer
from src.infrastructure.adapters.gemini_client import generate_completion_gemini
from src.application.logging_setup import app_logger

# ---------- Inicialização ----------
policy = Policy()
classifiers = [
    RuleBasedClassifier(),
    SBertClassifier(),      # embeddings + cabeça calibrada
]
engine = DecisionEngine(classifiers=classifiers, policy=policy)
sanitizer = LLMSanitizer()

app = FastAPI(title="PromptShield – Firewall Semântico (Gemini-only)")

# ---------- Schemas ----------
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    firewall: Dict[str, Any]
    input: str
    response: str

# ---------- Health ----------
@app.get("/health")
def health():
    return {"status": "ok", "provider": "gemini-only", "model": os.getenv("GEMINI_MODEL", "gemini-1.5-flash")}

# ---------- Debug (opcional) ----------
@app.get("/admin/debug")
def debug():
    return {
        "GOOGLE_API_KEY_set": bool(os.getenv("GOOGLE_API_KEY")),
        "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
    }

# ---------- Chat ----------
@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    message = (payload.message or "").strip()
    if not message:
        return JSONResponse({"error": "missing 'message' field"}, status_code=400)

    # 1) Firewall (classificadores + policy)
    result = engine.evaluate(message)
    decision: Decision = result["decision"]

    # 2) Ações do firewall
    if decision == Decision.BLOCK:
        app_logger.info({"event": "block", "msg_len": len(message), "votes": result["votes"]})
        return JSONResponse({
            "action": "blocked",
            "reason": "high-risk malicious prompt",
            "analysis": {"decision": decision.value, "votes": result["votes"]}
        }, status_code=403)

    final_input = message
    fw_action = "allowed"
    meta = None
    if decision == Decision.SANITIZE:
        clean_text, meta = sanitizer.sanitize(message)
        final_input = clean_text
        fw_action = "sanitized"
        app_logger.info({"event": "sanitize", "meta": meta})
    elif decision == Decision.ALLOW:
        app_logger.info({"event": "allow", "msg_len": len(message)})

    # 3) Gerar resposta com Gemini
    try:
        answer = generate_completion_gemini(final_input,
                                            model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                                            temperature=0.2)
    except Exception as e:
        # Fallback textual controlado (evita quebrar o cliente)
        app_logger.info({"event": "llm_fallback_simulated", "error": repr(e)})
        answer = f"[Simulado] Recebi com segurança: '{final_input[:200]}'"

    # 4) Monta resposta JSON
    fw_meta = {"action": fw_action, "analysis": {"decision": decision.value, "votes": result["votes"]}}
    if meta is not None:
        fw_meta["sanitizer_meta"] = meta

    return {
        "firewall": fw_meta,
        "input": final_input,
        "response": answer
    }

