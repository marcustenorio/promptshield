from typing import List, Dict, Any
from src.domain.enums.decision import Decision
from src.domain.ports.classifier_port import ClassifierPort
from src.application.policy import Policy
from src.application.logging_setup import app_logger

class DecisionEngine:
    def __init__(self, classifiers: List[ClassifierPort], policy: Policy):
        self.classifiers = classifiers
        self.policy = policy

    def evaluate(self, text: str) -> Dict[str, Any]:
        votes = []
        best = None
        best_score = -1.0

        for clf in self.classifiers:
            res = clf.predict(text)
            votes.append({
                "label": res.label,
                "category": res.category,
                "score": res.score,
                "reasons": res.reasons or {}
            })
            if res.label == "malicious" and res.score > best_score:
                best = res
                best_score = res.score

        if best and best.label == "malicious":
            if best.score >= self.policy.BLOCK_THRESHOLD:
                decision = Decision.BLOCK
            elif best.score >= self.policy.SANITIZE_THRESHOLD:
                decision = Decision.SANITIZE
            else:
                decision = Decision.ALLOW
        else:
            decision = Decision.ALLOW

        # LOG: não gravamos o texto por privacidade; guardamos um hash curto (opcional)
        app_logger.info({
            "event": "decision",
            "decision": decision.value,
            "best_score": best_score if best else None,
            "votes": votes
        })

        return {"decision": decision, "best": best, "votes": votes}

