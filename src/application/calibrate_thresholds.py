#!/usr/bin/env python3
# Comentário: calibra SANITIZE/BLOCK thresholds testando uma grade e avaliando métricas.
import csv, json, os
from pathlib import Path
import numpy as np
from datetime import datetime
from typing import Tuple, List, Dict

from src.application.policy import Policy
from src.infrastructure.adapters.sbert_classifier import SBertClassifier
from src.application.logging_setup import metrics_logger

VAL_PATHS = [
    Path("data/processed/val.csv"),              # preferencial
    Path("data/processed/test.csv"),
    Path("data/processed/dataset_v0.1.csv"),     # fallback
]

OUT_DIR = Path("logs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_val() -> Tuple[List[str], List[int]]:
    for p in VAL_PATHS:
        if p.exists():
            X, y = [], []
            with p.open(newline="", encoding="utf-8") as f:
                r = csv.DictReader(f)
                for row in r:
                    text = (row.get("text") or "").strip()
                    label = (row.get("label") or "").strip().lower()
                    if text and label in {"benign","malicious"}:
                        X.append(text)
                        y.append(1 if label == "malicious" else 0)
            if X:
                return X, y
    raise FileNotFoundError("Nenhum arquivo de validação encontrado.")

def decide(prob: float, sanitize_t: float, block_t: float) -> str:
    if prob >= block_t:
        return "BLOCK"
    if prob >= sanitize_t:
        return "SANITIZE"
    return "ALLOW"

def evaluate_grid(clf: SBertClassifier, X: List[str], y: List[int]) -> Dict:
    # Probabilidades p(malicious) para toda validação
    import numpy as np
    E = clf.body.encode(X, convert_to_numpy=True, show_progress_bar=False)
    probs = clf.head.predict_proba(E)[:,1]

    # Grades de thresholds
    sanitize_grid = np.linspace(0.4, 0.8, 9)   # 0.40..0.80
    block_grid    = np.linspace(0.7, 0.95, 6)  # 0.70..0.95

    best = None
    rows = []

    for st in sanitize_grid:
        for bt in block_grid:
            if bt <= st:
                continue  # precisa: BLOCK > SANITIZE
            # Predição por decisão (allow/sanitize/block)
            preds = [decide(p, st, bt) for p in probs]

            # Mapeia SANITIZE/BLOCK como "malicious" e ALLOW como "benign" p/ métricas binárias
            y_hat_bin = [1 if pr in {"SANITIZE","BLOCK"} else 0 for pr in preds]

            # Métricas
            from sklearn.metrics import precision_recall_fscore_support, confusion_matrix
            precision, recall, f1, _ = precision_recall_fscore_support(y, y_hat_bin, average="binary", zero_division=0)
            tn, fp, fn, tp = confusion_matrix(y, y_hat_bin, labels=[0,1]).ravel()

            # Custo exemplo (peso FN mais caro)
            cost = 5*fn + 1*fp

            row = {
                "sanitize_t": float(st),
                "block_t": float(bt),
                "precision": float(precision),
                "recall": float(recall),
                "f1": float(f1),
                "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
                "cost": float(cost),
            }
            rows.append(row)

            # Critério: minimiza custo; desempata por F1 maior
            if (best is None) or (row["cost"] < best["cost"]) or (row["cost"] == best["cost"] and row["f1"] > best["f1"]):
                best = row

    return {"best": best, "grid": rows}

def main():
    X, y = load_val()
    clf = SBertClassifier()  # carrega modelo (ou treina se faltar)

    res = evaluate_grid(clf, X, y)
    best = res["best"]

    # Log estruturado
    metrics_logger.info({"event":"calibration", "best": best})

    # Salva CSV/JSON dos resultados
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    csv_path = OUT_DIR / f"calibration_{ts}.csv"
    json_path = OUT_DIR / f"calibration_{ts}.json"

    import pandas as pd
    pd.DataFrame(res["grid"]).to_csv(csv_path, index=False)
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)

    # Sugere atualizar a policy (você pode automatizar isso salvando em config/policy.json)
    print("Melhor configuração encontrada:")
    print(best)
    print(f"Relatórios salvos em: {csv_path} e {json_path}")

if __name__ == "__main__":
    main()

