"""AWS S3 helpers — all operations gracefully degrade when AWS is not configured."""

import os
import json
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def _client():
    """Return a boto3 S3 client or None if boto3/credentials unavailable."""
    try:
        import boto3
        from src.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
        if not (AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY):
            return None
        return boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_DEFAULT_REGION,
        )
    except Exception as e:
        logger.warning(f"S3 client unavailable: {e}")
        return None


def upload_file(local_path: str, s3_key: str, bucket: Optional[str] = None) -> Optional[str]:
    """Upload a local file to S3. Returns the S3 URL or None."""
    from src.config import AWS_S3_BUCKET, AWS_DEFAULT_REGION
    bucket = bucket or AWS_S3_BUCKET
    client = _client()
    if not client:
        logger.info("S3 not configured — skipping upload")
        return None
    try:
        client.upload_file(local_path, bucket, s3_key)
        url = f"https://{bucket}.s3.{AWS_DEFAULT_REGION}.amazonaws.com/{s3_key}"
        logger.info(f"Uploaded {local_path} → s3://{bucket}/{s3_key}")
        return url
    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        return None


def upload_json(data: dict, s3_key: str, bucket: Optional[str] = None) -> Optional[str]:
    """Upload a JSON object directly to S3."""
    import tempfile
    from src.config import AWS_S3_BUCKET, AWS_DEFAULT_REGION
    bucket = bucket or AWS_S3_BUCKET
    client = _client()
    if not client:
        return None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f, indent=2, default=str)
            tmp = f.name
        client.upload_file(tmp, bucket, s3_key, ExtraArgs={"ContentType": "application/json"})
        os.unlink(tmp)
        url = f"https://{bucket}.s3.{AWS_DEFAULT_REGION}.amazonaws.com/{s3_key}"
        return url
    except Exception as e:
        logger.error(f"S3 JSON upload failed: {e}")
        return None


def save_claim_result(claim_id: str, result: dict, pdf_path: Optional[str] = None) -> dict:
    """
    Save a completed claim review to S3 (PDF + JSON summary).
    Falls back to local storage when S3 is unavailable.
    Returns a dict with storage locations.
    """
    from src.config import OUTPUT_DIR
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"claims/{timestamp}_{claim_id}"

    locations = {"local_json": None, "s3_pdf": None, "s3_json": None}

    # Always save locally
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    local_json = os.path.join(OUTPUT_DIR, f"{claim_id}_{timestamp}.json")
    with open(local_json, "w") as f:
        json.dump(result, f, indent=2, default=str)
    locations["local_json"] = local_json

    # Optional S3 upload
    if pdf_path and os.path.exists(pdf_path):
        locations["s3_pdf"] = upload_file(pdf_path, f"{prefix}/claim.pdf")
    locations["s3_json"] = upload_json(result, f"{prefix}/review_result.json")

    return locations


def check_s3_connection() -> bool:
    """Return True if we can successfully list S3 buckets."""
    client = _client()
    if not client:
        return False
    try:
        client.list_buckets()
        return True
    except Exception:
        return False
