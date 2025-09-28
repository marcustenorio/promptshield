# Comentário: definimos uma "porta" abstrata para classificadores.
# Usamos ABC para obrigar a implementação de 'predict'.
from abc import ABC, abstractmethod
from src.domain.entities.analysis import AnalysisResult

class ClassifierPort(ABC):
    """
    Porta (interface) de um classificador de prompts.
    Qualquer adaptador (regra, sklearn, SBERT, serviço externo) deve implementar 'predict'.
    """

    @abstractmethod
    def predict(self, text: str) -> AnalysisResult:
        """
        Recebe: 'text' (str) — o prompt do usuário.
        Retorna: AnalysisResult(label, category, score, reasons)
          - label: "benign" | "malicious"
          - category: "benign" | "override" | "exfiltration" | "jailbreak" | "indirect"
          - score: confiança [0,1] para a hipótese "malicious" (pode ser pseudo-score)
          - reasons: metadados explicando a decisão (ex.: palavras-chave, modelo usado)
        """
        raise NotImplementedError("Implementar no adaptador concreto.")

