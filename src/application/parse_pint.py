#!/usr/bin/env python3
# =======================================================
# Script: parse_pint.py
# Objetivo:
#   - Ler datasets do PINT em formato YAML (e também CSV/JSON/TXT se houver)
#   - Normalizar para o nosso formato padrão:
#       id,text,label,category,language,source
#
# Entrada: arquivos em data/raw/pint/ (ex.: example-dataset.yaml)
# Saída:   data/interim/pint_normalized.csv
#
# Observações:
# - PINT define ataques em YAML (cada item com campos como "id", "prompt", "attack_type").
# - O script detecta automaticamente o campo de texto (prompt).
# =======================================================

import csv
import json
import yaml   # precisa de PyYAML (pip install pyyaml)
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

RAW_DIR = Path("data/raw/pint")
OUT_DIR = Path("data/interim")
OUT_FILE = OUT_DIR / "pint_normalized.csv"

# Candidatos de campo que podem conter o texto do prompt
TEXT_CANDIDATES = [
    "text", "prompt", "instruction", "query", "input", "message"
]

def guess_language(text: str) -> str:
    """Heurística simples para PT/EN (troque depois por langdetect)."""
    pt_chars = "ãõáéíóúâêôçÃÕÁÉÍÓÚÂÊÔÇ"
    return "pt" if any(ch in text for ch in pt_chars) else "en"

def normalize_headers(d: Dict) -> Dict:
    """Normaliza chaves do dict: lowercase + strip."""
    return {(k or "").strip().lower(): v for k, v in d.items()}

def first_nonempty(d: Dict, keys: List[str]) -> str:
    for k in keys:
        if k in d and d[k] is not None:
            val = str(d[k]).strip()
            if val:
                return val
    return ""

def first_textual_value(d: Dict) -> str:
    """Fallback: pega o primeiro valor textual não-vazio do dict."""
    for v in d.values():
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return ""

def map_category(item: Dict, fname: str = "") -> str:
    """
    Mapeia a categoria do ataque no PINT para nossa taxonomia.
    PINT geralmente classifica injeções em tipos.
    """
    t = str(item.get("attack_type", "")).lower()
    if "exfil" in t:
        return "exfiltration"
    if "jailbreak" in t:
        return "jailbreak"
    if "override" in t:
        return "override"
    if "indirect" in t:
        return "indirect"
    if "benign" in t or "harmless" in t:
        return "benign"

    # fallback pelo nome do arquivo
    if "benign" in fname.lower():
        return "benign"

    return "override"  # default para ataques PINT

def normalize_rows(raw_iter: Iterable[Tuple[Dict, str]]) -> Iterable[Dict]:
    for idx, (item, fname) in enumerate(raw_iter, start=1):
        item = normalize_headers(item)

        text = first_nonempty(item, TEXT_CANDIDATES)
        if not text:
            text = first_textual_value(item)
        if not text:
            continue

        category = map_category(item, fname)
        label = "benign" if category == "benign" else "malicious"
        language = guess_language(text)

        yield {
            "id": f"pint-{idx}",
            "text": text,
            "label": label,
            "category": category,
            "language": language,
            "source": "pint",
        }

def load_yaml(path: Path) -> Iterable[Dict]:
    """Carrega listas de objetos a partir de YAML."""
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if isinstance(data, list):
                for obj in data:
                    yield obj
            elif isinstance(data, dict):
                # alguns arquivos podem ter "examples" ou "items"
                for key in ("examples", "items", "data"):
                    if isinstance(data.get(key), list):
                        for obj in data[key]:
                            yield obj
                        break
    except Exception as e:
        print(f"[WARN] Erro lendo YAML {path}: {e}")

def load_raw_files() -> Iterable[Tuple[Dict, str]]:
    # YAML
    for path in RAW_DIR.rglob("*.yaml"):
        for row in load_yaml(path):
            yield row, path.name
    for path in RAW_DIR.rglob("*.yml"):
        for row in load_yaml(path):
            yield row, path.name

    # JSON
    for path in RAW_DIR.rglob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for obj in data:
                    yield obj, path.name
            elif isinstance(data, dict):
                for key in ("data", "items", "records"):
                    if isinstance(data.get(key), list):
                        for obj in data[key]:
                            yield obj, path.name
                        break
        except Exception as e:
            print(f"[WARN] Erro lendo JSON {path}: {e}")

    # CSV
    for path in RAW_DIR.rglob("*.csv"):
        try:
            with path.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield row, path.name
        except Exception as e:
            print(f"[WARN] Erro lendo CSV {path}: {e}")

    # TXT
    for path in RAW_DIR.rglob("*.txt"):
        try:
            with path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    yield {"text": line}, path.name
        except Exception as e:
            print(f"[WARN] Erro lendo TXT {path}: {e}")

def main():
    print("Lendo dados crus do PINT em data/raw/pint ...")
    raw_iter = load_raw_files()
    rows = list(normalize_rows(raw_iter))

    if not rows:
        print("Nenhum dado normalizado. Verifique os arquivos YAML em data/raw/pint.")
        return

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id","text","label","category","language","source"])
        w.writeheader()
        w.writerows(rows)

    print(f"Normalização concluída: {OUT_FILE} (linhas: {len(rows)})")

if __name__ == "__main__":
    main()

