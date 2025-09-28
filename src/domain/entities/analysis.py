# VO com o resultado padronizado dos classificadores
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class AnalysisResult:
    label: str                 # "benign" | "malicious"
    category: str              # "benign" | "override" | "exfiltration" | "jailbreak" | "indirect"
    score: float               # confiança/probabilidade (0.0 a 1.0) de "malicious"
    reasons: Optional[Dict] = None  # metadados explicativos (ex.: regra que bateu, modelo, etc.)

