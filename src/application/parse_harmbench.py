#!/usr/bin/env python3
# =======================================================
# Script: parse_harmbench.py (versão robusta)
# Lê CSV/JSON/TXT de data/raw/harmbench e normaliza para:
#   data/interim/harmbench_normalized.csv
#
# Saída: id,text,label,category,language,source
# =======================================================

import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

RAW_DIR = Path("data/raw/harmbench")
OUT_DIR = Path("data/interim")
OUT_FILE = OUT_DIR / "harmbench_normalized.csv"

# Candidatos de campo que podem conter o texto do prompt/behavior
TEXT_CANDIDATES = [
    "text", "prompt", "behavior", "goal", "instruction", "input",
    "attack", "message", "query", "task", "request"
]

def guess_language(text: str) -> str:
    pt_chars = "ãõáéíóúâêôçÃÕÁÉÍÓÚÂÊÔÇ"
    return "pt" if any(ch in text for ch in pt_chars) else "en"

def infer_category(text: str, filename_hint: str = "") -> str:
    t = (text or "").lower()
    hint = filename_hint.lower()

    # (quase tudo do HarmBench é malicioso; ainda assim mantemos heurísticas)
    if "benign" in hint:
        return "benign"

    if any(x in t for x in ["api key", "secret", "secrets", "senha", "password", "token", "leak"]):
        return "exfiltration"

    if any(x in t for x in ["jailbreak", "roleplay", "ignore safety", "devmode", "dan mode", "pretend to be"]):
        return "jailbreak"

    if any(x in t for x in ["hidden instruction", "instrução escondida", "when you process this text", "indirect"]):
        return "indirect"

    if any(x in t for x in ["ignore previous instructions", "ignore all rules", "ignore as regras"]):
        return "override"

    # fallback padrão
    return "override"

def normalize_headers(row: Dict) -> Dict:
    """Normaliza chaves: lowercase + strip."""
    return { (k or "").strip().lower(): v for k, v in row.items() }

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

def normalize_rows(raw_iter: Iterable[Tuple[Dict, str]]) -> Iterable[Dict]:
    total = 0
    for idx, (item, fname) in enumerate(raw_iter, start=1):
        item = normalize_headers(item)
        text = first_nonempty(item, TEXT_CANDIDATES)
        if not text:
            # alguns CSVs podem ter 'behavior' com outro nome ou primeira coluna útil
            text = first_textual_value(item)
        if not text:
            continue

        category = infer_category(text, filename_hint=fname)
        label = "benign" if category == "benign" else "malicious"
        language = guess_language(text)

        total += 1
        yield {
            "id": f"harmbench-{idx}",
            "text": text,
            "label": label,
            "category": category,
            "language": language,
            "source": "harmbench",
        }

def load_csv_rows(path: Path) -> Iterable[Dict]:
    """Lê CSV com sniff de delimitador e normaliza cabeçalho."""
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

def load_raw_files() -> Iterable[Tuple[Dict, str]]:
    # CSV
    for path in RAW_DIR.rglob("*.csv"):
        if str(path).endswith(":Zone.Identifier"):
            continue
        try:
            for row in load_csv_rows(path):
                yield row, path.name
        except Exception as e:
            print(f"[WARN] Erro lendo CSV {path}: {e}")

    # JSON
    for path in RAW_DIR.rglob("*.json"):
        if str(path).endswith(":Zone.Identifier"):
            continue
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

    # TXT
    for path in RAW_DIR.rglob("*.txt"):
        if str(path).endswith(":Zone.Identifier"):
            continue
        try:
            with path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    yield {"text": line}, path.name
        except Exception as e:
            print(f"[WARN] Erro lendo TXT {path}: {e}")

def summarize_csv_headers():
    """Imprime as colunas de cada CSV para debug."""
    print("🔎 Inspecionando cabeçalhos dos CSVs...")
    for path in RAW_DIR.rglob("*.csv"):
        if str(path).endswith(":Zone.Identifier"):
            continue
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
                headers = [ (h or "").strip().lower() for h in headers ]
                print(f"   - {path.name}: {headers}")
        except Exception as e:
            print(f"[WARN] Falha ao inspecionar {path}: {e}")

def main():
    print("🔧 Lendo dados crus do HarmBench em data/raw/harmbench ...")
    # Relatório rápido de arquivos e colunas
    print("📄 Arquivos CSV detectados:")
    for p in RAW_DIR.rglob("*.csv"):
        if not str(p).endswith(":Zone.Identifier"):
            print(f"   - {p.name}")
    summarize_csv_headers()

    raw_iter = load_raw_files()
    rows = list(normalize_rows(raw_iter))

    if not rows:
        print("⚠️  Nenhum dado normalizado. Verifique os cabeçalhos acima e, se preciso,")
        print("    acrescente o nome da coluna ao TEXT_CANDIDATES.")
        return

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id","text","label","category","language","source"])
        w.writeheader()
        w.writerows(rows)

    print(f"✅ Normalização concluída: {OUT_FILE} (linhas: {len(rows)})")

if __name__ == "__main__":
    main()

