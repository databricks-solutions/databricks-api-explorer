"""
Authentication module for Databricks API Explorer.

Two modes:
  Local  → Databricks CLI profile 'guido-demo-azure' (SSO / OAuth / PAT)
  App    → On-Behalf-Of (OBO) via x-forwarded-access-token header
"""
import os
import time
from functools import lru_cache
from typing import Any, Dict, Optional

import requests

# ── Detection ─────────────────────────────────────────────────────────────────
# Databricks Apps auto-injects DATABRICKS_CLIENT_SECRET for the app SP.
IS_DATABRICKS_APP: bool = bool(os.getenv("DATABRICKS_CLIENT_SECRET"))

DATABRICKS_PROFILE = "guido-demo-azure"


# ── Config / SDK ──────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_local_config():
    """Lazy-load local SDK Config using the CLI profile."""
    from databricks.sdk.core import Config  # noqa: PLC0415
    return Config(profile=DATABRICKS_PROFILE)


def get_host() -> str:
    """Return the Databricks workspace host URL (without trailing slash)."""
    if IS_DATABRICKS_APP:
        return os.getenv("DATABRICKS_HOST", "").rstrip("/")
    try:
        cfg = _get_local_config()
        return (cfg.host or "").rstrip("/")
    except Exception:
        return ""


def get_local_token() -> Optional[str]:
    """
    Extract bearer token from the local SDK Config.
    Supports PAT, OAuth M2M, and browser-based OAuth (SSO).
    """
    try:
        cfg = _get_local_config()
        auth_headers = cfg.authenticate()
        auth_val = auth_headers.get("Authorization", "")
        if auth_val.startswith("Bearer "):
            return auth_val[7:]
    except Exception:
        pass
    return None


# ── User Info ─────────────────────────────────────────────────────────────────

def get_current_user_info(token: str, host: str) -> Dict[str, Any]:
    """Fetch current user info via SCIM /Me endpoint."""
    result = make_api_call("GET", "/api/2.0/preview/scim/v2/Me", token, host)
    if result["success"]:
        data = result["data"]
        return {
            "display_name": data.get("displayName", ""),
            "user_name": data.get("userName", ""),
        }
    return {"display_name": "Unknown", "user_name": ""}


# ── API Calls ─────────────────────────────────────────────────────────────────

def make_api_call(
    method: str,
    path: str,
    token: str,
    host: str,
    query_params: Optional[Dict] = None,
    body: Optional[Any] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    Execute a Databricks REST API call.

    Returns:
        status_code : int   — HTTP status code (0 on network error)
        elapsed_ms  : int   — round-trip time in milliseconds
        data        : any   — parsed JSON response body
        success     : bool  — True for 2xx responses
        error       : str|None
        url         : str   — full request URL
    """
    url = f"{host}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "DatabricksAPIExplorer/1.0",
    }

    # Strip empty/None query params
    if query_params:
        query_params = {k: v for k, v in query_params.items() if v not in (None, "")}

    t0 = time.perf_counter()
    try:
        is_read = method.upper() in ("GET", "DELETE")
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            params=query_params if is_read else None,
            json=body if not is_read else None,
            timeout=timeout,
        )
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        try:
            data = response.json()
        except Exception:
            data = {"_raw": response.text}

        return {
            "status_code": response.status_code,
            "elapsed_ms": elapsed_ms,
            "data": data,
            "success": response.ok,
            "error": None if response.ok else response.reason,
            "url": url,
        }

    except requests.exceptions.Timeout:
        return {
            "status_code": 0,
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
            "data": {"error": "Request timed out after 30 seconds."},
            "success": False,
            "error": "Timeout",
            "url": url,
        }
    except Exception as exc:
        return {
            "status_code": 0,
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
            "data": {"error": str(exc)},
            "success": False,
            "error": str(exc),
            "url": url,
        }
