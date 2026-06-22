"""Generate synthetic claim PDFs and policy documents."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import CLAIMS_DIR, POLICY_DOCS_DIR
from src.utils.pdf_generator import generate_all_synthetic_data


def main():
    print("Generating synthetic data...")
    result = generate_all_synthetic_data(CLAIMS_DIR, POLICY_DOCS_DIR)
    print(f"Created {result['claims_generated']} claim PDFs in: {CLAIMS_DIR}")
    print(f"Created {result['policies_generated']} policy PDFs in: {POLICY_DOCS_DIR}")
    print("\nClaim files:")
    for f in result["claim_files"]:
        print(f"  {f}")
    print("\nPolicy files:")
    for f in result["policy_files"]:
        print(f"  {f}")
    print("\nDone.")


if __name__ == "__main__":
    main()
