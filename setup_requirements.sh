#!/bin/bash
# =======================================================
# Script para gerar arquivo requirements.txt
# do projeto PromptShield (com comentários explicativos)
# =======================================================

REQ_FILE="requirements.txt"

# Comentário: usamos cat <<EOL para escrever o conteúdo no arquivo
cat <<EOL > $REQ_FILE
# =============================
# Bibliotecas de manipulação de dados
# =============================

# Pandas: leitura/escrita de CSV, manipulação tabular (dataset_v0.1)
pandas

# NumPy: operações numéricas, arrays vetorizados (base dos embeddings)
numpy

# =============================
# Machine Learning (modelos clássicos)
# =============================

# Scikit-learn: modelos baseline (LogReg, SVM, XGBoost), métricas de avaliação
scikit-learn

# =============================
# Deep Learning / NLP (embeddings e transformers)
# =============================

# PyTorch: backend de deep learning necessário para transformers e SBERT
torch

# Sentence-Transformers: geração de embeddings semânticos (SBERT/BERT)
sentence-transformers

# Transformers (Hugging Face): uso de modelos pré-treinados (BERT, RoBERTa, DistilBERT)
transformers

# =============================
# Web framework para expor o firewall como API
# =============================

# FastAPI: framework web leve para criar o firewall semântico como serviço REST
fastapi

# Uvicorn: servidor ASGI rápido para rodar a API FastAPI
uvicorn[standard]

# =============================
# Utilitários adicionais
# =============================

# Langdetect: detectar idioma do prompt (pt/en), útil no dataset e pré-processamento
langdetect

# Python-dotenv: carregar variáveis de ambiente (.env) como chaves de API, configs
python-dotenv
EOL

echo "Arquivo $REQ_FILE criado com sucesso!"

