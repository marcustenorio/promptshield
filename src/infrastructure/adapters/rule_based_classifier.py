# Classificador simples por regras (palavras-chave). Serve como guard-rail inicial.
import re
from src.domain.entities.analysis import AnalysisResult
from src.domain.ports.classifier_port import ClassifierPort

class RuleBasedClassifier(ClassifierPort):
    def __init__(self):
        # listas de padrões (ajuste conforme sua curadoria)
        self.exfil_keywords = [r"api key", r"password", r"senha", r"secret", r"token", r"chave de api"]
        self.override_keywords = [r"ignore previous instructions", r"ignore all rules", r"ignore as regras"]
        self.jailbreak_keywords = [r"jailbreak", r"roleplay", r"pretend to be", r"dan mode", r"devmode"]
        self.indirect_keywords = [r"hidden instruction", r"instrução escondida", r"when you process this text"]

    def predict(self, text: str) -> AnalysisResult:
        low = text.lower()

        def any_match(patterns):
            return any(re.search(p, low) for p in patterns)

        if any_match(self.exfil_keywords):
            return AnalysisResult(label="malicious", category="exfiltration", score=0.90, reasons={"rule":"exfil_keyword"})
        if any_match(self.override_keywords):
            return AnalysisResult(label="malicious", category="override", score=0.80, reasons={"rule":"override_keyword"})
        if any_match(self.jailbreak_keywords):
            return AnalysisResult(label="malicious", category="jailbreak", score=0.75, reasons={"rule":"jailbreak_keyword"})
        if any_match(self.indirect_keywords):
            return AnalysisResult(label="malicious", category="indirect", score=0.70, reasons={"rule":"indirect_keyword"})

        return AnalysisResult(label="benign", category="benign", score=0.10, reasons={"rule":"none"})

