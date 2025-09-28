#!/usr/bin/env bash
# ==========================================================
# Script: download_jailbreakbench.sh
# Objetivo: Baixar JailbreakBench para data/raw/jailbreakbench/
#
# Opções:
#  A) Clonar o repositório oficial (útil para a lib/avaliação)
#  B) Baixar o dataset "JBB-Behaviors" (config 'behaviors') do Hugging Face e exportar CSVs
#
# Fontes:
# - Repo:   https://github.com/JailbreakBench/jailbreakbench
# - HF ds:  https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors
# - Site:   https://jailbreakbench.github.io/
# ==========================================================

# Comentário: encerra o script se ocorrer erro, variável não definida ou pipe quebrar
set -euo pipefail

# Comentário: define a pasta de destino dos dados "crus" do JailbreakBench
RAW_DIR="data/raw/jailbreakbench"

# Comentário: cria a pasta de destino (se não existir)
mkdir -p "$RAW_DIR"

echo "▶️ Destino: $RAW_DIR"

# --------------------------
# Opção A) Clonar o repositório oficial (código/avaliação)
# --------------------------
echo "🔹 Opção A: Clonando o repositório oficial (útil para a lib de avaliação)..."

# Comentário: cria diretório temporário para o clone
TMP_DIR_A="$(mktemp -d)"

# Comentário: clona o repositório oficial do JailbreakBench
git clone https://github.com/JailbreakBench/jailbreakbench.git "$TMP_DIR_A/jbb"

# Comentário: copia arquivos de dados (se existirem) para sua pasta RAW
# Observação: os dados principais ficam no Hugging Face; no repo podem existir exemplos
find "$TMP_DIR_A/jbb" -type f \( -iname "*.csv" -o -iname "*.json" -o -iname "*.txt" -o -iname "*.yaml" -o -iname "*.yml" \) -print -exec cp {} "$RAW_DIR"/ \; || true

# Comentário: remove a pasta temporária (limpeza)
rm -rf "$TMP_DIR_A"

echo "✅ Repositório clonado (se havia artefatos de dados, foram copiados)."

# --------------------------
# Opção B) Baixar dataset do Hugging Face (config 'behaviors')
# --------------------------
echo "🔹 Opção B: Baixando o dataset 'JBB-Behaviors' (config 'behaviors') do Hugging Face e exportando CSV..."

# Comentário: cria diretório temporário para rodar o exportador Python
TMP_DIR_B="$(mktemp -d)"

# Comentário: caminho do script Python temporário
PY="$TMP_DIR_B/export_jbb_hf.py"

# Comentário: gera script Python que baixa a config 'behaviors' e exporta os splits para CSV
cat > "$PY" << 'PYCODE'
import os
from datasets import load_dataset

# Comentário: carrega a CONFIG correta do dataset (behaviors)
ds = load_dataset("JailbreakBench/JBB-Behaviors", "behaviors")

# Comentário: pasta de saída (vai receber via env RAW_DIR do shell)
out_dir = os.environ.get("RAW_DIR", "data/raw/jailbreakbench")
os.makedirs(out_dir, exist_ok=True)

# Comentário: exporta cada split disponível (geralmente 'train') para CSV
for split in ds.keys():
    path = os.path.join(out_dir, f"jbb_behaviors_{split}.csv")
    df = ds[split].to_pandas()
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"✅ Exportado: {path}  ({len(df)} linhas)")
PYCODE

# Comentário: verifica/instala a lib 'datasets' do Hugging Face (sem warn depreciação)
python - <<'PYCHECK'
import importlib.util, sys, subprocess
def installed(name): return importlib.util.find_spec(name) is not None
if not installed("datasets"):
    print("📦 Instalando 'datasets' (Hugging Face)...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "datasets"])
else:
    print("✅ 'datasets' já está instalado.")
PYCHECK

# Comentário: executa o exportador Python passando RAW_DIR como variável de ambiente
RAW_DIR="$RAW_DIR" python "$PY"

# Comentário: remove a pasta temporária (limpeza)
rm -rf "$TMP_DIR_B"

# Comentário: lista os arquivos finais gravados em RAW_DIR
echo "✅ JailbreakBench salvo em: $RAW_DIR"
echo "📄 Conteúdo atual da pasta:"
ls -lah "$RAW_DIR"

# Comentário: dica de próximos passos (parser + merge)
echo "ℹ️ Próximo: rode seu parser e depois o merge:"
echo "   python src/application/parse_jailbreakbench.py   (quando criar)"
echo "   python src/application/merge_with_existing_dataset.py"

