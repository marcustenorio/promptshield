# Comentário: um único ponto de entrada para gerar texto.
# Ele escolhe o provedor com base no ambiente e faz fallback automático:
# 1) OPENAI (se OPENAI_API_KEY e quota OK)
# 2) OLLAMA (se OLLAMA_HOST acessível)
# 3) HUGGINGFACE Transformers local
import os
from typing import Optional

from src.application.logging_setup import app_logger

# ---------- OpenAI (já temos um adaptador) ----------
from src.infrastructure.adapters.openai_client import generate_safe_completion as _openai_generate

# --- topo do arquivo: imports existentes ---

# ---------- Gemini (Google Gen AI SDK) ----------
def _gemini_generate(prompt: str) -> str:
    """
    Usa Gemini via Google Gen AI SDK.
    Env:
      GOOGLE_API_KEY (obrigatório)
      GEMINI_MODEL   (ex.: 'gemini-1.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro')
    Docs: https://ai.google.dev/gemini-api/docs/quickstart
    """
    import os
    from google import genai
    from google.genai import types

    api_key = os.getenv("GOOGLE_API_KEY", "")
    model   = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY ausente")

    client = genai.Client(api_key=api_key)

    # (Opcional) configurações de segurança para bloquear apenas conteúdo nocivo claro
    safety = [
        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT",
                            threshold="BLOCK_MEDIUM_AND_ABOVE"),
        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT",
                            threshold="BLOCK_MEDIUM_AND_ABOVE"),
    ]

    resp = client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
        config=types.GenerateContentConfig(temperature=0.2, safety_settings=safety),
    )

    # Extrai texto gerado
    text = getattr(resp, "text", None)
    if not text:
        text = "".join(
            [p.text for c in resp.candidates for p in c.content.parts if hasattr(p, "text")]
        ).strip()
    return text or "[Gemini não retornou texto]"

# ---------- HuggingFace (Transformers) ----------
def _hf_generate(prompt: str) -> str:
    """
    Fallback Hugging Face robusto:
      - Usa FLAN-T5 (text2text-generation), que responde bem Q&A.
      - Prompt instruído em PT-BR e pós-processamento para remover eco.
    Env:
      HF_MODEL (default: google/flan-t5-small)
      HF_MAX_NEW_TOKENS (default: 180)
      HF_TEMPERATURE (default: 0.2)
    """
    import os, re
    import torch
    from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM

    model_name = os.getenv("HF_MODEL", "google/flan-t5-small")
    max_new_tokens = int(os.getenv("HF_MAX_NEW_TOKENS", "180"))
    temperature = float(os.getenv("HF_TEMPERATURE", "0.2"))

    device = 0 if torch.cuda.is_available() else -1

    # Garante FLAN por padrão (text2text)
    if "flan" not in model_name.lower():
        model_name = "google/flan-t5-small"

    tok = AutoTokenizer.from_pretrained(model_name, trust_remote_code=False)
    mdl = AutoModelForSeq2SeqLM.from_pretrained(model_name, trust_remote_code=False)
    gen = pipeline(
        "text2text-generation",
        model=mdl,
        tokenizer=tok,
        device=device
    )

    # Prompt mais objetivo, pedindo resposta direta
    # (flan tende a seguir bem "Instrucao: ... Resposta:")
    t5_prompt = (
        "Instrução: Responda de forma objetiva, clara e didática a pergunta a seguir.\n"
        f"Pergunta: {prompt}\n"
        "Resposta:"
    )

    out = gen(
        t5_prompt,
        max_new_tokens=max_new_tokens,
        do_sample=True if temperature > 0 else False,
        temperature=temperature,
    )[0]["generated_text"].strip()

    # --- Pós-processamento para remover ecos do prompt e ruídos comuns ---
    # remove eventuais prefixos tipo "Resposta:" / "Answer:" / "Output:"
    out = re.sub(r"^\s*(Resposta|Answer|Output)\s*:\s*", "", out, flags=re.IGNORECASE).strip()

    # se o modelo repetiu a pergunta, remove-a
    norm_prompt = re.sub(r"\s+", " ", prompt).strip().lower()
    norm_out = re.sub(r"\s+", " ", out).strip().lower()
    if norm_prompt in norm_out and len(out) <= len(prompt) + 40:
        # se praticamente só repetiu, tente uma 2ª tentativa mais direcionada
        t5_prompt2 = (
            "Explique em 3–5 frases, com linguagem simples e exemplos curtos:\n"
            f"{prompt}\n"
            "Resposta:"
        )
        out2 = gen(
            t5_prompt2,
            max_new_tokens=max_new_tokens,
            do_sample=True if temperature > 0 else False,
            temperature=max(0.2, temperature),
        )[0]["generated_text"].strip()
        out2 = re.sub(r"^\s*(Resposta|Answer|Output)\s*:\s*", "", out2, flags=re.IGNORECASE).strip()
        if out2:
            out = out2

    # sanitiza espaços extras
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out or "[HF não gerou conteúdo]"

# ---------- Ollama ----------
def _ollama_generate(prompt: str) -> str:
    """
    Usa servidor local do Ollama. CONTROLADO por env:
      OLLAMA_MODEL (default: llama3.1:8b)
      OLLAMA_HOST  (default: http://127.0.0.1:11434)
    Antes, rode:  `ollama run llama3.1:8b`  (baixar a 1ª vez)
    """
    import ollama
    model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    # O cliente lê OLLAMA_HOST do env se necessário
    res = ollama.generate(model=model, prompt=prompt)
    return (res.get("response") or "").strip()

# ---------- Roteador ----------
def generate_completion_router(user_text: str) -> str:
    provider = os.getenv("PROVIDER", "").upper().strip()

    if provider == "GEMINI":
        try:
            return _gemini_generate(user_text)
        except Exception as e:
            app_logger.info({"event":"provider_gemini_fail", "error": repr(e)})
            raise  # deixa o handler /chat fazer fallback simulado

    # Modo auto: tente OpenAI → Ollama → HF → Gemini
    if os.getenv("OPENAI_API_KEY"):
        try:
            return _openai_generate(user_text)
        except Exception as e:
            app_logger.info({"event":"provider_auto_openai_fail", "error": repr(e)})

    try:
        return _ollama_generate(user_text)
    except Exception as e:
        app_logger.info({"event":"provider_auto_ollama_fail", "error": repr(e)})

    try:
        return _hf_generate(user_text)
    except Exception as e:
        app_logger.info({"event":"provider_auto_hf_fail", "error": repr(e)})

    # por fim, tenta Gemini se tiver chave
    if os.getenv("GOOGLE_API_KEY"):
        try:
            return _gemini_generate(user_text)
        except Exception as e:
            app_logger.info({"event":"provider_auto_gemini_fail", "error": repr(e)})

    return f"[LLM Local Simulado] {user_text[:180]}"

