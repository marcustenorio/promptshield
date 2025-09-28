#!/usr/bin/env python3
# =======================================================
# Script: merge_with_existing_dataset.py
# Objetivo: mesclar o harmbench_normalized.csv ao dataset_v0.1.csv
# - Lê:  data/processed/dataset_v0.1.csv   (se existir)
# - Lê:  data/interim/harmbench_normalized.csv
# - Faz deduplicação por (texto normalizado) para evitar duplicatas
# - Salva: data/processed/dataset_v0.1.csv (versão mais robusta)
#   -> Se quiser manter uma cópia anterior, também geramos um backup
# =======================================================

import csv
import hashlib
from pathlib import Path

PROCESSED_FILE = Path("data/processed/dataset_v0.1.csv")
#HARMBENCH_FILE = Path("data/interim/harmbench_normalized.csv")
#PINT_FILE = Path("data/interim/pint_normalized.csv")
JAILBREAKBENCH_FILE = Path("data/interim/jailbreakbench_normalized.csv") 
BACKUP_FILE = Path("data/processed/dataset_v0.1.backup.csv")

FIELDS = ["id","text","label","category","language","source"]

def text_key(text: str) -> str:
    """
    Gera uma chave de hash estável para deduplicação por conteúdo.
    Normalização simples: strip + lower.
    """
    norm = (text or "").strip().lower()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()

def read_csv_if_exists(path: Path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return [row for row in r]

def write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

def main():
    # 1) Carregar datasets
    base_rows = read_csv_if_exists(PROCESSED_FILE)
    #harm_rows = read_csv_if_exists(HARMBENCH_FILE)
    #pint_rows = read_csv_if_exists(PINT_FILE)
    jailbreakbench_rows = read_csv_if_exists(JAILBREAKBENCH_FILE)

    #if not harm_rows:
    #if not pint_rows:
    if not jailbreakbench_rows:
        #print("Não há harmbench_normalized.csv para mesclar. Rode o parser primeiro.")
        #print("Não há pint_normalized.csv para mesclar. Rode o parser primeiro.")
        print("Não há jailbreakbench_normalized.csv para mesclar. Rode o parser primeiro.")
        return

    # 2) Backup do dataset atual (se existir)
    if base_rows:
        write_csv(BACKUP_FILE, base_rows)
        print(f"Backup criado: {BACKUP_FILE} (linhas: {len(base_rows)})")

    # 3) Deduplicação por texto
    seen = {}
    merged = []

    # primeiro, coloca o que já existia
    for row in base_rows:
        k = text_key(row.get("text",""))
        if k not in seen:
            seen[k] = True
            merged.append({f: row.get(f, "") for f in FIELDS})

    # depois, adiciona harmbench
    for row in jailbreakbench_rows:
        k = text_key(row.get("text",""))
        if k not in seen:
            seen[k] = True
            merged.append({f: row.get(f, "") for f in FIELDS})

    # 4) Salvar de volta no mesmo nome (dataset_v0.1.csv)
    write_csv(PROCESSED_FILE, merged)
    print(f"Merge concluído: {PROCESSED_FILE} (linhas: {len(merged)})")

if __name__ == "__main__":
    main()

