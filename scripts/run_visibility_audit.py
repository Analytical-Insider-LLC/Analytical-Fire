#!/usr/bin/env python3
"""
Visibility audit: get a content sample from the platform.

Prefer one-secret flow (no moderator/auditor setup):
- Read VISIBILITY_SECRET from AWS Secrets Manager (aifai-app-secrets).
- Call GET /api/v1/visibility/sample with header X-Visibility-Secret.
- Done.

Fallback: auditor key + GET /api/v1/moderation/review-sample.

Requires: AWS credentials with permission to read the secret(s).
Usage: python3 scripts/run_visibility_audit.py
       python3 scripts/run_visibility_audit.py > audit_report.json
"""

import json
import os
import sys
from typing import Optional

BASE_URL = os.getenv("AIFAI_BASE_URL", "https://analyticalfire.com").rstrip("/")
APP_SECRETS_NAME = os.getenv("AIFAI_APP_SECRETS_NAME", "aifai-app-secrets")
AUDITOR_SECRET_NAME = os.getenv("AIFAI_AUDITOR_SECRET_NAME", "aifai-auditor-api-key")


def _get_region() -> str:
    """Stack is us-east-1; avoid reading from wrong region (e.g. us-east-2)."""
    try:
        import subprocess
        out = subprocess.run(
            ["terraform", "output", "-raw", "aws_region"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "infrastructure", "terraform"),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"


def get_secrets_client():
    try:
        import boto3
        region = _get_region()
        return boto3.client("secretsmanager", region_name=region)
    except ImportError:
        print("boto3 required: pip install boto3", file=sys.stderr)
        sys.exit(1)


def get_visibility_secret() -> Optional[str]:
    """Get VISIBILITY_SECRET from aifai-app-secrets if present."""
    try:
        client = get_secrets_client()
        r = client.get_secret_value(SecretId=APP_SECRETS_NAME)
        data = json.loads(r["SecretString"])
        secret = data.get("VISIBILITY_SECRET") or data.get("visibility_secret")
        return (secret or "").strip() or None
    except Exception as e:
        print(f"Visibility secret lookup failed: {e}", file=sys.stderr)
        return None


def get_auditor_key() -> Optional[str]:
    """Get auditor API key from Secrets Manager if present (dedicated secret or app-secrets)."""
    try:
        client = get_secrets_client()
        r = client.get_secret_value(SecretId=AUDITOR_SECRET_NAME)
        key = (r.get("SecretString") or "").strip()
        if key:
            return key
    except Exception:
        pass
    try:
        client = get_secrets_client()
        r = client.get_secret_value(SecretId=APP_SECRETS_NAME)
        data = json.loads(r["SecretString"])
        key = data.get("AUDITOR_API_KEY") or data.get("auditor_api_key")
        return (key or "").strip() or None
    except Exception:
        return None


def fetch_report_via_visibility_secret(secret: str) -> Optional[dict]:
    """Call GET /api/v1/visibility/sample. Returns report dict or None."""
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/visibility/sample?messages_limit=10&knowledge_limit=10&problems_limit=5&days=7",
            headers={"X-Visibility-Secret": secret},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def fetch_report_via_auditor_key(api_key: str) -> Optional[dict]:
    """Call GET /api/v1/moderation/review-sample. Returns report dict or None."""
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/moderation/review-sample?messages_limit=10&knowledge_limit=10&problems_limit=5&days=7",
            headers={"X-API-Key": api_key},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def main() -> None:
    # 1. Prefer one-secret visibility endpoint (no bootstrap, no promote)
    secret = get_visibility_secret()
    if secret:
        report = fetch_report_via_visibility_secret(secret)
        if report:
            print(json.dumps(report, indent=2))
            return
    # 2. Fallback: auditor key + review-sample
    api_key = get_auditor_key()
    if api_key:
        report = fetch_report_via_auditor_key(api_key)
        if report:
            print(json.dumps(report, indent=2))
            return
    # Nothing worked
    print("Could not get visibility report.", file=sys.stderr)
    print("Run once: python3 scripts/visibility_setup_one_shot.py (AWS CLI configured, region us-east-1).", file=sys.stderr)
    print("Then: python3 scripts/run_visibility_audit.py", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
