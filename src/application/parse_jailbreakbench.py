#!/usr/bin/env python3
# =======================================================
# Script: parse_jailbreakbench.py (com suporte a YAML/YML)
# Normaliza para: data/interim/jailbreakbench_normalized.csv
# Campos: id,text,label,category,language,source
# =======================================================

import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Any

import yaml  # pip install pyyaml

RAW_DIR = Path("data/raw/jailbreakbench")
OUT_DIR = Path("data/interim")
OUT_FILE = OUT_DIR / "jailbreakbench_normalized.csv"

TEXT_CANDIDATES = [
    "text", "prompt", "behavior", "goal", "instruction",
    "query", "input", "message", "task", "request"
]

def normalize_headers(d: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza chaves: lowercase + strip (robustez a variações)."""
    return {(k or "").strip().lower(): v for k, v in d.items()}

def coerce_to_dict(item: Any) -> Dict[str, Any]:
    """
    Garante que o item seja um dict.
    - Se já for dict -> normaliza cabeçalhos.
    - Se for string/num/list/etc -> vira {"text": str(item)}.
    """
    if isinstance(item, dict):
        return normalize_headers(item)
    return {"text": str(item)}

def first_nonempty(d: Dict, keys: List[str]) -> str:
    for k in keys:
        if k in d and d[k] is not None:
            val = str(d[k]).strip()
            if val:
                return val
    return ""

def first_textual_value(d: Dict) -> str:
    for v in d.values():
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return ""

def guess_language(text: str) -> str:
    pt_chars = "ãõáéíóúâêôçÃÕÁÉÍÓÚÂÊÔÇ"
    return "pt" if any(ch in text for ch in pt_chars) else "en"

def map_category_from_fields(d: Dict, filename_hint: str = "") -> str:
    """
    1) Usa 'category' do dataset se existir (JBB traz 'benign'/'harmful').
    2) Caso contrário, usa heurísticas por palavras-chave.
    3) Fallback: 'jailbreak'.
    """
    # 1) Campo explícito
    cat = str(d.get("category", "")).lower()
    if cat:
        if "benign" in cat:
            return "benign"
        # Muitos CSVs do JBB usam 'harmful' para comportamentos nocivos
        if "harmful" in cat:
            return "jailbreak"

        # Se o arquivo já trouxer 'exfiltration', 'override', etc.
        if "exfil" in cat:
            return "exfiltration"
        if "override" in cat:
            return "override"
        if "indirect" in cat:
            return "indirect"
        if "jailbreak" in cat:
            return "jailbreak"

    # 2) Heurística pelo conteúdo
    text = (d.get("text") or d.get("behavior") or d.get("prompt") or "").lower()
    hint = filename_hint.lower()

    if "benign" in hint:
        return "benign"

    if any(x in text for x in ["api key", "secret", "secrets", "senha", "password", "token", "leak data"]):
        return "exfiltration"

    if any(x in text for x in ["ignore previous instructions", "ignore all rules", "ignore as regras"]):
        return "override"

    if any(x in text for x in ["hidden instruction", "instrução escondida", "when you process this text", "indirect"]):
        return "indirect"

    if any(x in text for x in ["jailbreak", "roleplay", "ignore safety", "devmode", "dan mode", "pretend to be"]):
        return "jailbreak"

    # 3) Fallback
    return "jailbreak"

def normalize_rows(raw_iter: Iterable[Tuple[Any, str]]) -> Iterable[Dict]:
    """
    Converte cada item cru para nosso esquema. Aceita item não-dict.
    raw_iter: tuplas (item, filename_hint)
    """
    for idx, (item, fname) in enumerate(raw_iter, start=1):
        d = coerce_to_dict(item)

        text = first_nonempty(d, TEXT_CANDIDATES) or first_textual_value(d)
        if not text:
            continue

        # Anexamos 'text' ao dict coerced para o mapeador de categoria poder usar
        d["text"] = text

        category = map_category_from_fields(d, filename_hint=fname)
        label = "benign" if category == "benign" else "malicious"
        language = guess_language(text)

        yield {
            "id": f"jbb-{idx}",
            "text": text,
            "label": label,
            "category": category,
            "language": language,
            "source": "jailbreakbench",
        }

# -----------------------------
# Leitores de cada tipo
# -----------------------------

def load_csv_rows(path: Path) -> Iterable[Dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except Exception:
            dialect = csv.excel
            dialect.delimiter = ","
        reader = csv.DictReader(f, dialect=dialect)
        for row in reader:
            yield row

def load_json_rows(path: Path) -> Iterable[Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        for obj in data:
            yield obj
    elif isinstance(data, dict):
        for key in ("data", "items", "records", "examples", "behaviors"):
            if isinstance(data.get(key), list):
                for obj in data[key]:
                    yield obj
                break

def load_yaml_rows(path: Path) -> Iterable[Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if isinstance(data, list):
        for obj in data:
            yield obj
    elif isinstance(data, dict):
        for key in ("examples", "items", "data", "behaviors"):
            if isinstance(data.get(key), list):
                for obj in data[key]:
                    yield obj
                break

def load_txt_rows(path: Path) -> Iterable[Dict]:
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield {"text": line}

def load_raw_files() -> Iterable[Tuple[Any, str]]:
    # CSV (HF)
    for path in RAW_DIR.rglob("*.csv"):
        try:
            for row in load_csv_rows(path):
                yield row, path.name
        except Exception as e:
            print(f"[WARN] Erro lendo CSV {path}: {e}")

    # JSON (repo)
    for path in RAW_DIR.rglob("*.json"):
        try:
            for row in load_json_rows(path):
                yield row, path.name
        except Exception as e:
            print(f"[WARN] Erro lendo JSON {path}: {e}")

    # YAML / YML (repo)
    for path in RAW_DIR.rglob("*.yaml"):
        try:
            for row in load_yaml_rows(path):
                yield row, path.name
        except Exception as e:
            print(f"[WARN] Erro lendo YAML {path}: {e}")

    for path in RAW_DIR.rglob("*.yml"):
        try:
            for row in load_yaml_rows(path):
                yield row, path.name
        except Exception as e:
            print(f"[WARN] Erro lendo YML {path}: {e}")

    # TXT (fallback)
    for path in RAW_DIR.rglob("*.txt"):
        try:
            for row in load_txt_rows(path):
                yield row, path.name
        except Exception as e:
            print(f"[WARN] Erro lendo TXT {path}: {e}")

def summarize_csv_headers():
    print("🔎 Cabeçalhos detectados nos CSVs de data/raw/jailbreakbench:")
    for path in RAW_DIR.rglob("*.csv"):
        try:
            with path.open("r", encoding="utf-8", newline="") as f:
                sample = f.read(4096)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                except Exception:
                    dialect = csv.excel
                    dialect.delimiter = ","
                reader = csv.reader(f, dialect=dialect)
                headers = next(reader, [])
                headers = [(h or "").strip().lower() for h in headers]
                print(f"   - {path.name}: {headers}")
        except Exception as e:
            print(f"[WARN] Falha ao inspecionar {path}: {e}")

def main():
    print("🔧 Lendo dados crus do JailbreakBench em data/raw/jailbreakbench ...")
    summarize_csv_headers()

    raw_iter = load_raw_files()
    rows = list(normalize_rows(raw_iter))

    if not rows:
        print("⚠️  Nenhum dado normalizado. Verifique os arquivos (CSV/JSON/YAML/TXT) e cabeçalhos acima.")
        return

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id","text","label","category","language","source"])
        w.writeheader()
        w.writerows(rows)

    print(f"✅ Normalização concluída: {OUT_FILE} (linhas: {len(rows)})")

if __name__ == "__main__":
    main()

