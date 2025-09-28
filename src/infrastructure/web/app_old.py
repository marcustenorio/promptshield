# Comentário: FastAPI com firewall aplicado DENTRO do handler /chat.
# Vantagem: não precisamos "reemitir" o corpo da requisição via ASGI; evitamos respostas não-JSON.
from typing import Optional, Any, Dict
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.application.policy import Policy
from src.application.decision_engine import DecisionEngine
from src.domain.enums.decision import Decision
from src.infrastructure.adapters.rule_based_classifier import RuleBasedClassifier
from src.infrastructure.adapters.sbert_classifier import SBertClassifier
from src.infrastructure.adapters.llm_sanitizer import LLMSanitizer
#from src.infrastructure.adapters.openai_client import generate_safe_completion
from src.infrastructure.adapters.provider_router import generate_completion_router
from src.application.logging_setup import app_logger

# ---------- Inicialização de dependências ----------
policy = Policy()
classifiers = [
    RuleBasedClassifier(),
    SBertClassifier(),     # SBERT + cabeça calibrada
]
engine = DecisionEngine(classifiers=classifiers, policy=policy)
sanitizer = LLMSanitizer()

app = FastAPI(title="PromptShield – Firewall Semântico (handler-based)")

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
    return {"status": "ok"}

# ---------- Chat (firewall dentro do handler) ----------
@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    # 1) Entrada do usuário
    message = (payload.message or "").strip()
    if not message:
        return JSONResponse({"error": "missing 'message' field"}, status_code=400)

    # 2) Avaliar com o firewall
    result = engine.evaluate(message)
    decision = result["decision"]

    # 3) Ações do firewall
    if decision == Decision.BLOCK:
        app_logger.info({"event": "block", "msg_len": len(message)})
        return JSONResponse({
            "action": "blocked",
            "reason": "high-risk malicious prompt",
            "analysis": {"decision": decision.value, "votes": result["votes"]}
        }, status_code=403)

    # SANITIZE: reescreve/mascara e segue ao LLM com texto limpo
    final_input = message
    meta = None
    action = "allowed"
    if decision == Decision.SANITIZE:
        clean_text, meta = sanitizer.sanitize(message)
        final_input = clean_text
        action = "sanitized"
        app_logger.info({"event":"sanitize", "msg_len": len(message), "meta": meta})

    if decision == Decision.ALLOW:
        app_logger.info({"event":"allow", "msg_len": len(message)})

    # 4) Chamar o LLM (OpenAI se houver chave; senão fallback simulado)
    try:
        #answer = generate_safe_completion(final_input)
        answer = generate_completion_router(final_input)
    except Exception as e:
        # fallback — garante **sempre** JSON para o cliente
        app_logger.info({"event":"llm_fallback", "error": repr(e)})
        answer = f"[LLM Simulado] Recebi sua mensagem com segurança: '{final_input[:200]}'"

    # 5) Montar resposta JSON
    fw_meta = {"action": action, "analysis": {"decision": decision.value, "votes": result["votes"]}}
    if meta is not None:
        fw_meta["sanitizer_meta"] = meta

    return {
        "firewall": fw_meta,
        "input": final_input,
        "response": answer
    }

