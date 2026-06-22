@echo off
echo ========================================
echo  Healthcare Claim Review Assistant Setup
echo ========================================
echo.

REM 1. Create .env from example
if not exist .env (
    copy .env.example .env
    echo Created .env — EDIT IT and add your OPENAI_API_KEY before continuing.
    echo.
    pause
)

REM 2. Install dependencies
echo Installing Python packages...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: pip install failed. Make sure Python 3.10+ is installed.
    pause
    exit /b 1
)

REM 3. Generate synthetic data
echo.
echo Generating synthetic claim PDFs and policy documents...
python scripts\generate_synthetic_data.py
if errorlevel 1 (
    echo WARNING: Data generation failed. You can retry later from the sidebar.
)

REM 4. Ingest policy docs into ChromaDB
echo.
echo Ingesting policy documents into ChromaDB (requires OPENAI_API_KEY)...
python scripts\ingest_documents.py
if errorlevel 1 (
    echo WARNING: RAG ingestion failed. The app will use built-in policy rules as fallback.
)

REM 5. Launch app
echo.
echo Launching Streamlit app...
echo Open http://localhost:8501 in your browser.
echo.
streamlit run app.py
