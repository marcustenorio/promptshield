# Comentário: cliente OpenAI via Responses API (recomendado).
# Respeita variáveis de ambiente:
#   - OPENAI_API_KEY (obrigatória)
#   - OPENAI_MODEL   (opcional; ex.: "gpt-4o-mini")
# Docs oficiais: platform.openai.com/docs/api-reference/responses. :contentReference[oaicite:6]{index=6}
import os
from openai import OpenAI  # SDK 1.x. :contentReference[oaicite:7]{index=7}

_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

def generate_safe_completion(user_text: str) -> str:
    """
    Chama o LLM com uma instrução de segurança mínima.
    Em produção, você pode injetar políticas internas aqui.
    """
    client = OpenAI()  # lê OPENAI_API_KEY do ambiente
    resp = client.responses.create(
        model=_OPENAI_MODEL,
        # Comentário: 'input' é a forma simples (Responses API)
        input=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant. Follow safety policies. "
                    "Refuse illicit content. Remove secrets. Keep answers concise."
                ),
            },
            {"role": "user", "content": user_text},
        ],
    )
    # Comentário: a SDK 1.x fornece 'output_text' como atalho
    return resp.output_text

