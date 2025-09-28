# Comentário: porta de sanitização (normaliza, mascara segredos, reescreve).
from abc import ABC, abstractmethod
from typing import Tuple, Dict

class SanitizerPort(ABC):
    """
    Porta (interface) de um sanitizador.
    Deve retornar o texto possivelmente alterado e metadados de como alterou.
    """

    @abstractmethod
    def sanitize(self, text: str) -> Tuple[str, Dict]:
        """
        Recebe: 'text' original.
        Retorna: (texto_sanitizado, metadados)
          - texto_sanitizado: string com redactions/remoções/reescrita
          - metadados: dict com ações realizadas (ex.: padrões redigidos, LLM usado)
        """
        raise NotImplementedError("Implementar no adaptador concreto.")

