# Comentário: classificador baseado em embeddings SBERT + regressão logística calibrada.
# Ele lê seu dataset_v0.1.csv, treina/recupera um modelo, e retorna:
#   - label: benign/malicious
#   - category: heurística leve (pelo conteúdo)
#   - score: probabilidade (p(malicious))
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
import csv
import joblib
import numpy as np

# Sentence-Transformers para embeddings
from sentence_transformers import SentenceTransformer  # ver docs oficiais. :contentReference[oaicite:3]{index=3}

# scikit-learn para classificador probabilístico
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import f1_score

from src.domain.entities.analysis import AnalysisResult
from src.domain.ports.classifier_port import ClassifierPort

# Comentário: caminhos
MODEL_DIR = Path("models")
EMB_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # 384 dims (rápido e bom). :contentReference[oaicite:4]{index=4}
SBERT_PATH = MODEL_DIR / "sbert_body.joblib"     # cache do body (opcional)
HEAD_PATH  = MODEL_DIR / "sbert_head.joblib"     # classificador calibrado
DATASET    = Path("data/processed/dataset_v0.1.csv")

@dataclass
class _SBertBundle:
    body: SentenceTransformer
    head: CalibratedClassifierCV

class SBertClassifier(ClassifierPort):
    def __init__(self):
        # Comentário: carrega corpo SBERT (pré-treinado); download no 1º uso.
        self.body = SentenceTransformer(EMB_MODEL_NAME)
        # Comentário: carrega cabeça (classificador) se existir; caso contrário treina.
        if HEAD_PATH.exists():
            self.head = joblib.load(HEAD_PATH)
        else:
            self.head = self._train_and_save()

    def _load_dataset(self) -> Tuple[List[str], List[int]]:
        # Comentário: mapeia label para binário (malicious=1, benign=0)
        X, y = [], []
        with DATASET.open(newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                text = (row.get("text") or "").strip()
                label = (row.get("label") or "").strip().lower()
                if text and label in {"benign", "malicious"}:
                    X.append(text)
                    y.append(1 if label == "malicious" else 0)
        return X, y

    def _train_and_save(self) -> CalibratedClassifierCV:
        # Comentário: carrega dados
        X, y = self._load_dataset()

        # Comentário: gera embeddings com SBERT (np.ndarray [n, d])
        E = self.body.encode(X, convert_to_numpy=True, show_progress_bar=True)

        # Comentário: regressão logística (class_weight para lidar com desbalanceamento)
        base = LogisticRegression(max_iter=200, class_weight="balanced")

        # Comentário: calibramos probabilidade (Platt/Isotonic) p/ melhor score
        head = CalibratedClassifierCV(base, cv=3, method="sigmoid")
        head.fit(E, y)

        # Comentário: F1 em treino (checagem rápida)
        p = head.predict(E)
        f1 = f1_score(y, p, average="weighted")
        print(f"[SBERT] F1 (train quick check): {f1:.3f}")

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(head, HEAD_PATH)
        return head

    def _infer_category(self, text: str) -> str:
        low = text.lower()
        if any(k in low for k in ["api key", "password", "senha", "secret", "token"]):
            return "exfiltration"
        if any(k in low for k in ["ignore previous instructions", "ignore as regras", "ignore all rules"]):
            return "override"
        if any(k in low for k in ["jailbreak", "roleplay", "pretend to be"]):
            return "jailbreak"
        if any(k in low for k in ["hidden instruction", "instrução escondida", "when you process this text"]):
            return "indirect"
        return "benign"

    def predict(self, text: str) -> AnalysisResult:
        # Comentário: codifica o texto para vetor SBERT
        e = self.body.encode([text], convert_to_numpy=True)
        # Comentário: obtém probabilidade da classe positiva (malicious=1)
        proba = float(self.head.predict_proba(e)[0, 1])
        label = "malicious" if proba >= 0.5 else "benign"
        category = self._infer_category(text) if label == "malicious" else "benign"
        return AnalysisResult(label=label, category=category, score=proba, reasons={"model":"sbert+logreg_calibrated"})

