#!/usr/bin/env bash
# ==========================================================
# Baixa o PINT Benchmark (Lakera) para data/raw/pint/
# Copia também arquivos .yaml/.yml (formato nativo do PINT)
# Ref: https://github.com/lakeraai/pint-benchmark
# ==========================================================

set -euo pipefail

# Comentário: define a pasta de destino dos dados "crus" do PINT
RAW_DIR="data/raw/pint"
mkdir -p "$RAW_DIR"

# Comentário: usa um diretório temporário para clonar o repo
TMP_DIR="$(mktemp -d)"

# Comentário: clona o repo oficial do PINT
git clone https://github.com/lakeraai/pint-benchmark.git "$TMP_DIR/pint-benchmark"

# Comentário: 1) Copiar TODOS os YAML/YML (formato do dataset PINT)
find "$TMP_DIR/pint-benchmark" -type f \( -iname "*.yaml" -o -iname "*.yml" \) -print -exec cp {} "$RAW_DIR"/ \;

# Comentário: 2) (Opcional) espelhar a pasta benchmark/data inteira
# Isso garante que você tenha os exemplos e estrutura usada pelo notebook
if [ -d "$TMP_DIR/pint-benchmark/benchmark/data" ]; then
  mkdir -p "$RAW_DIR/benchmark_data"
  cp -r "$TMP_DIR/pint-benchmark/benchmark/data/." "$RAW_DIR/benchmark_data/"
fi

# Comentário: 3) (Opcional) ainda copiamos CSV/JSON/TXT se aparecerem no futuro
find "$TMP_DIR/pint-benchmark" -type f \( -iname "*.csv" -o -iname "*.json" -o -iname "*.txt" \) -print -exec cp {} "$RAW_DIR"/ \; || true

# Comentário: remove a pasta temporária
rm -rf "$TMP_DIR"

# Comentário: lista de arquivos baixados
echo "PINT baixado em: $RAW_DIR"
echo "Arquivos:"
ls -lah "$RAW_DIR"

