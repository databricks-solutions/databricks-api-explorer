"""
Authentication module for Databricks API Explorer.

Two modes:
  Local  → Databricks CLI profile (SSO / OAuth / PAT) or custom URL + token
  App    → On-Behalf-Of (OBO) via x-forwarded-access-token header
"""
import configparser
import os
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import requests

# ── Detection ─────────────────────────────────────────────────────────────────
IS_DATABRICKS_APP: bool = bool(os.getenv("DATABRICKS_CLIENT_SECRET"))

DATABRICKS_PROFILE = "guido-demo-azure"


# ── CLI Profile discovery ──────────────────────────────────────────────────────

def get_cli_profiles() -> List[str]:
    """Read all Databricks CLI profile names from ~/.databrickscfg.

    Parses section headers directly so that ALL profiles (including DEFAULT
    and any that configparser would otherwise merge/skip) are returned.
    """
    path = os.path.expanduser("~/.databrickscfg")
    if not os.path.exists(path):
        return [DATABRICKS_PROFILE]

    profiles: List[str] = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped.startswith("[") and stripped.endswith("]"):
                    name = stripped[1:-1].strip()
                    if name:
                        profiles.append(name)
    except Exception:
        pass

    return profiles if profiles else [DATABRICKS_PROFILE]


# ── Connection resolution ──────────────────────────────────────────────────────

def resolve_local_connection(conn_config: Optional[Dict]) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve (host, token) from a connection config dict for local mode.

    conn_config shapes:
      {"mode": "profile", "profile": "<name>"}
      {"mode": "custom",  "host": "https://...", "token": "dapi..."}
    """
    if not conn_config:
        conn_config = {"mode": "profile", "profile": DATABRICKS_PROFILE}

    mode = conn_config.get("mode", "profile")

    if mode == "custom":
        host = (conn_config.get("host") or "").rstrip("/")
        token = (conn_config.get("token") or "")
        return (host or None), (token or None)

    # Profile mode
    profile = conn_config.get("profile") or DATABRICKS_PROFILE
    try:
        from databricks.sdk.core import Config  # noqa: PLC0415
        cfg = Config(profile=profile)
        host = (cfg.host or "").rstrip("/")
        auth_val = cfg.authenticate().get("Authorization", "")
        token = auth_val[7:] if auth_val.startswith("Bearer ") else None
        return host or None, token
    except Exception:
        return None, None


# ── Legacy helpers (used when no conn_config is needed) ───────────────────────

@lru_cache(maxsize=1)
def _get_local_config():
    """Lazy-load SDK Config for the default profile (exported for auth modal)."""
    from databricks.sdk.core import Config  # noqa: PLC0415
    return Config(profile=DATABRICKS_PROFILE)


def get_host() -> str:
    """Return workspace host for the default profile (app-mode aware)."""
    if IS_DATABRICKS_APP:
        return os.getenv("DATABRICKS_HOST", "").rstrip("/")
    try:
        return (_get_local_config().host or "").rstrip("/")
    except Exception:
        return ""


def get_local_token() -> Optional[str]:
    """Return token for the default local profile."""
    try:
        auth_val = _get_local_config().authenticate().get("Authorization", "")
        return auth_val[7:] if auth_val.startswith("Bearer ") else None
    except Exception:
        return None


# ── Workspace Info ────────────────────────────────────────────────────────────

def get_workspace_name(token: str, host: str) -> Optional[str]:
    """Return the human-readable workspace name via the best available API.

    Tries, in order:
      1. GET /api/2.0/workspace-conf?keys=workspaceName  (may be set by admins)
      2. GET /api/2.1/unity-catalog/metastore_summary    (metastore name ≈ workspace)
      3. Parse the hostname for a display-friendly label
    """
    # 1 — workspace conf
    r = make_api_call("GET", "/api/2.0/workspace-conf", token, host,
                      query_params={"keys": "workspaceName"})
    if r["success"]:
        name = (r["data"] or {}).get("workspaceName", "")
        if name:
            return name

    # 2 — Unity Catalog metastore summary
    r = make_api_call("GET", "/api/2.1/unity-catalog/metastore_summary", token, host)
    if r["success"]:
        name = (r["data"] or {}).get("name", "")
        if name:
            return name

    # 3 — parse hostname: "adb-123.azuredatabricks.net" → "adb-123"
    #     custom domains:  "myco.databricks.com"        → "myco"
    import re as _re
    m = _re.match(r"https?://([^./]+)", host)
    return m.group(1) if m else None


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
    """Execute a Databricks REST API call."""
    url = f"{host}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "DatabricksAPIExplorer/1.0",
    }

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
