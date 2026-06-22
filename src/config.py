import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── LLM ───────────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ── AWS ───────────────────────────────────────────────────────────────────────
AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_DEFAULT_REGION: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
AWS_S3_BUCKET: str = os.getenv("AWS_S3_BUCKET_NAME", "healthcare-claims-bucket")

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / "data" / "chroma_db"))
POLICY_DOCS_DIR: str = os.getenv("POLICY_DOCS_DIR", str(BASE_DIR / "data" / "policy_documents"))
CLAIMS_DIR: str = os.getenv("CLAIMS_DIR", str(BASE_DIR / "data" / "synthetic_claims"))
OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", str(BASE_DIR / "data" / "outputs"))

# ── Feature flags ─────────────────────────────────────────────────────────────
def aws_configured() -> bool:
    return bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)

def openai_configured() -> bool:
    return bool(OPENAI_API_KEY)
