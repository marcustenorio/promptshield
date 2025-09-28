#!/usr/bin/env python3
"""
EDA rápido para dataset_v0.1.csv
Saída: impressões no terminal com counts, distribuição de idioma,
comprimento médio dos prompts e amostras por categoria.
"""
import csv
from pathlib import Path
from collections import Counter, defaultdict
import statistics

IN = Path("data/processed/dataset_v0.1.csv")

def read_rows(path):
    with path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            yield row

def main():
    if not IN.exists():
        print("Arquivo não encontrado:", IN)
        return

    rows = list(read_rows(IN))
    n = len(rows)
    print(f"Total de linhas: {n}")

    labels = Counter(row["label"] for row in rows)
    cats = Counter(row["category"] for row in rows)
    sources = Counter(row["source"] for row in rows)
    langs = Counter(row["language"] for row in rows)

    lengths = [len(row["text"].split()) for row in rows if row.get("text")]
    print("\nDistribuição de rótulos (label):")
    for k,v in labels.items():
        print(f"  {k}: {v}")

    print("\nDistribuição por categoria (category):")
    for k,v in cats.most_common():
        print(f"  {k}: {v}")

    print("\nDistribuição por source:")
    for k,v in sources.most_common():
        print(f"  {k}: {v}")

    print("\nDistribuição de idiomas:")
    for k,v in langs.items():
        print(f"  {k}: {v}")

    print(f"\nComprimento (palavras): média={statistics.mean(lengths):.1f}, mediana={statistics.median(lengths)}")
    print(f"Min/Max comprimento: {min(lengths)} / {max(lengths)}")

    # mostrar 3 amostras por categoria (se existirem)
    sample_by_cat = defaultdict(list)
    for r in rows:
        if len(sample_by_cat[r["category"]]) < 3:
            sample_by_cat[r["category"]].append(r["text"])

    print("\nAmostras por categoria (até 3 cada):")
    for cat, examples in sample_by_cat.items():
        print(f"--- {cat} ({len(examples)}) ---")
        for e in examples:
            print("  >", e)
    print("\nFim do EDA.")

if __name__ == "__main__":
    main()

