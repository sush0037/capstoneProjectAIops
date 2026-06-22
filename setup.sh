#!/usr/bin/env bash
set -e

echo "========================================"
echo " Healthcare Claim Review Assistant Setup"
echo "========================================"

# 1. Create .env
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env — Edit it and set OPENAI_API_KEY before continuing."
  echo "Press Enter when ready."
  read
fi

# 2. Python virtual env
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

# 3. Install dependencies
echo "Installing packages..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 4. Generate synthetic data
echo "Generating synthetic claim PDFs and policy documents..."
python scripts/generate_synthetic_data.py || echo "WARNING: Data generation failed — retry from the sidebar."

# 5. Ingest docs into ChromaDB
echo "Ingesting policy docs into ChromaDB (requires OPENAI_API_KEY)..."
python scripts/ingest_documents.py || echo "WARNING: RAG ingest failed — app will use built-in fallback rules."

# 6. Launch
echo ""
echo "Launching Streamlit app at http://localhost:8501"
streamlit run app.py
