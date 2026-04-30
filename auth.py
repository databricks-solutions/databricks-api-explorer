"""Authentication module for Databricks API Explorer.

Supports two runtime modes selected at import time:

* **Local** -- Databricks CLI profile (SSO / OAuth / PAT) or a custom
  workspace URL + personal access token.
* **Databricks App** -- On-Behalf-Of (OBO) authentication via the
  ``x-forwarded-access-token`` request header injected by the Databricks
  Apps proxy.

The active mode is exposed through the module-level constant
:data:`IS_DATABRICKS_APP`.

Attributes:
    IS_DATABRICKS_APP: ``True`` when running inside a managed Databricks
        App (detected via the ``DATABRICKS_CLIENT_SECRET`` env var).
    DATABRICKS_PROFILE: Default CLI profile name resolved from
        ``~/.databrickscfg`` at import time.
"""
import os
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import requests

# ── Detection ─────────────────────────────────────────────────────────────────
IS_DATABRICKS_APP: bool = bool(os.getenv("DATABRICKS_CLIENT_SECRET"))


def _ensure_host_scheme(host: str) -> str:
    """Ensure the host URL has an https:// scheme."""
    host = host.strip().rstrip("/")
    if host and not host.startswith("https://"):
        host = "https://" + host
    return host


def get_sp_token() -> Optional[str]:
    """Obtain an OAuth token using the Service Principal client credentials.

    Uses the Databricks SDK ``Config`` which reads ``DATABRICKS_HOST``,
    ``DATABRICKS_CLIENT_ID``, and ``DATABRICKS_CLIENT_SECRET`` env vars
    auto-injected in Databricks Apps.  The SDK handles the correct OIDC
    endpoint for each cloud provider (AWS, Azure, GCP).

    Returns:
        The access token string, or ``None`` on failure.
    """
    try:
        from databricks.sdk.core import Config
        cfg = Config(
            host=_ensure_host_scheme(os.getenv("DATABRICKS_HOST", "")),
            client_id=os.getenv("DATABRICKS_CLIENT_ID", ""),
            client_secret=os.getenv("DATABRICKS_CLIENT_SECRET", ""),
        )
        auth_val = cfg.authenticate().get("Authorization", "")
        return auth_val[7:] if auth_val.startswith("Bearer ") else None
    except Exception:
        return None




# ── CLI Profile discovery ──────────────────────────────────────────────────────

def get_cli_profiles() -> List[str]:
    """Read all Databricks CLI profile names from ``~/.databrickscfg``.

    Parses INI section headers directly (rather than via
    :mod:`configparser`) so that **all** profiles -- including ``DEFAULT``
    and any that ``configparser`` would merge or skip -- are returned.

    Returns:
        A list of profile name strings.  Falls back to ``["DEFAULT"]``
        when the config file is missing or contains no sections.
    """
    path = os.path.expanduser("~/.databrickscfg")
    if not os.path.exists(path):
        return ["DEFAULT"]

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

    return profiles if profiles else ["DEFAULT"]


# Default to the first profile found in ~/.databrickscfg
DATABRICKS_PROFILE: str = get_cli_profiles()[0]


# ── Connection resolution ──────────────────────────────────────────────────────

def get_account_id(profile: Optional[str] = None) -> Optional[str]:
    """Read the ``account_id`` from a CLI profile's SDK Config.

    Args:
        profile: Profile name to inspect.  Defaults to
            :data:`DATABRICKS_PROFILE`.

    Returns:
        The account ID string, or ``None`` if not configured or on
        error.
    """
    try:
        from databricks.sdk.core import Config  # noqa: PLC0415
        cfg = Config(profile=profile or DATABRICKS_PROFILE)
        return getattr(cfg, "account_id", None) or None
    except Exception:
        return None


def _find_account_profile(account_id: str) -> Optional[str]:
    """Find a CLI profile whose host is an accounts console URL.

    Scans all profiles in ``~/.databrickscfg`` for one that has
    ``host = https://accounts.*`` and the matching ``account_id``.

    Args:
        account_id: The Databricks account ID to match.

    Returns:
        The profile name, or ``None`` if no account-level profile
        exists.
    """
    from databricks.sdk.core import Config  # noqa: PLC0415
    for profile in get_cli_profiles():
        try:
            cfg = Config(profile=profile)
            h = (cfg.host or "").lower()
            if "accounts." in h and getattr(cfg, "account_id", None) == account_id:
                return profile
        except Exception:
            continue
    return None


def resolve_account_connection(
    conn_config: Optional[Dict],
    accounts_host: str,
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve host and token for the Databricks **accounts console**.

    Account-level APIs require a token issued for the accounts
    console, not the workspace.  This function first checks whether
    the active profile already points to an accounts host; if not, it
    searches for another profile that does (matching by
    ``account_id``).

    Args:
        conn_config: The ``conn-config`` Dash store value.
        accounts_host: The accounts console URL (e.g.
            ``https://accounts.cloud.databricks.com``).

    Returns:
        A ``(accounts_host, token)`` tuple.  Either element may be
        ``None`` on failure.
    """
    if not conn_config:
        conn_config = {"mode": "profile", "profile": DATABRICKS_PROFILE}

    mode = conn_config.get("mode", "profile")

    # For custom / SSO modes the user provides their own token — pass it
    # through and hope it's account-scoped.
    if mode in ("custom", "sso"):
        token = (conn_config.get("token") or "")
        return accounts_host, (token or None)

    # Profile mode — find a profile that targets the accounts console
    profile = conn_config.get("profile") or DATABRICKS_PROFILE
    try:
        from databricks.sdk.core import Config  # noqa: PLC0415

        # Check if the active profile itself already points to accounts.*
        cfg = Config(profile=profile)
        h = (cfg.host or "").lower()
        if "accounts." in h and getattr(cfg, "account_id", None):
            auth_val = cfg.authenticate().get("Authorization", "")
            token = auth_val[7:] if auth_val.startswith("Bearer ") else None
            return cfg.host.rstrip("/"), token

        # Otherwise, look up the account_id and find another profile
        account_id = getattr(cfg, "account_id", None) or None
        if not account_id:
            return accounts_host, None

        acct_profile = _find_account_profile(account_id)
        if not acct_profile:
            return accounts_host, None

        acct_cfg = Config(profile=acct_profile)
        auth_val = acct_cfg.authenticate().get("Authorization", "")
        token = auth_val[7:] if auth_val.startswith("Bearer ") else None
        return (acct_cfg.host or accounts_host).rstrip("/"), token
    except Exception:
        return accounts_host, None


def resolve_local_connection(
    conn_config: Optional[Dict],
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve workspace host and token from a connection config dict.

    This is the local-mode counterpart of the OBO path.  It interprets
    the ``conn-config`` Dash store and returns credentials suitable for
    passing to :func:`make_api_call`.

    Args:
        conn_config: Connection configuration dictionary.  Expected
            shapes::

                {"mode": "profile", "profile": "<name>"}
                {"mode": "custom",  "host": "https://...", "token": "dapi..."}
                {"mode": "sso",     "host": "https://...", "token": "..."}

            When ``None``, falls back to the default CLI profile.

    Returns:
        A ``(host, token)`` tuple.  Either element may be ``None`` if
        resolution fails (e.g. expired credentials or missing profile).
    """
    if not conn_config:
        conn_config = {"mode": "profile", "profile": DATABRICKS_PROFILE}

    mode = conn_config.get("mode", "profile")

    if mode == "custom":
        host = (conn_config.get("host") or "").rstrip("/")
        token = (conn_config.get("token") or "")
        return (host or None), (token or None)

    if mode == "sso":
        host = (conn_config.get("host") or "").rstrip("/")
        token = conn_config.get("token") or ""
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
    """Lazy-load a :class:`databricks.sdk.core.Config` for the default profile.

    The result is cached (via :func:`functools.lru_cache`) so that
    repeated calls during a single process lifetime reuse the same
    ``Config`` object.

    Returns:
        A :class:`~databricks.sdk.core.Config` instance for
        :data:`DATABRICKS_PROFILE`.
    """
    from databricks.sdk.core import Config  # noqa: PLC0415
    return Config(profile=DATABRICKS_PROFILE)


def get_host() -> str:
    """Return the workspace host URL for the default profile.

    In Databricks App mode the host is read from the
    ``DATABRICKS_HOST`` environment variable; in local mode it is
    resolved via the cached SDK ``Config``.

    Returns:
        The workspace URL (without trailing slash), or an empty string
        on failure.
    """
    if IS_DATABRICKS_APP:
        host = os.getenv("DATABRICKS_HOST", "").rstrip("/")
        if host and not host.startswith("https://"):
            host = "https://" + host
        return host
    try:
        return (_get_local_config().host or "").rstrip("/")
    except Exception:
        return ""


def get_local_token() -> Optional[str]:
    """Return the bearer token for the default local CLI profile.

    Returns:
        The access token string, or ``None`` if authentication fails.
    """
    try:
        auth_val = _get_local_config().authenticate().get("Authorization", "")
        return auth_val[7:] if auth_val.startswith("Bearer ") else None
    except Exception:
        return None


# ── Workspace Info ────────────────────────────────────────────────────────────

def get_workspace_name(token: str, host: str) -> Optional[str]:
    """Return a human-readable workspace name via the best available API.

    Resolution strategy (first success wins):

    1. ``GET /api/2.0/workspace-conf?keys=workspaceName`` -- admin-set
       workspace display name.
    2. Parse the hostname (e.g. ``adb-123.azuredatabricks.net`` →
       ``adb-123``).

    Note: the metastore name fallback was removed because
    :func:`get_metastore_name` is now displayed separately.

    Args:
        token: Bearer token for the workspace.
        host: Full workspace URL including scheme.

    Returns:
        A display-friendly workspace name, or ``None`` if all
        strategies fail.
    """
    # 1 — workspace conf
    r = make_api_call("GET", "/api/2.0/workspace-conf", token, host,
                      query_params={"keys": "workspaceName"})
    if r["success"]:
        name = (r["data"] or {}).get("workspaceName", "")
        if name:
            return name

    # 2 — parse hostname: "adb-123.azuredatabricks.net" → "adb-123"
    #     custom domains:  "myco.databricks.com"        → "myco"
    import re as _re
    m = _re.match(r"https?://([^./]+)", host)
    return m.group(1) if m else None


def get_metastore_name(token: str, host: str) -> Optional[str]:
    """Return the name of the Unity Catalog metastore attached to this workspace.

    Args:
        token: Bearer token for the workspace.
        host: Full workspace URL including scheme.

    Returns:
        The metastore display name, or ``None`` if not available.
    """
    r = make_api_call("GET", "/api/2.1/unity-catalog/metastore_summary", token, host)
    if r["success"]:
        name = (r["data"] or {}).get("name", "")
        if name:
            return name
    return None


# ── User Info ─────────────────────────────────────────────────────────────────

def get_current_user_info(token: str, host: str) -> Dict[str, Any]:
    """Fetch the authenticated user's identity via the SCIM ``/Me`` endpoint.

    Args:
        token: Bearer token for the workspace.
        host: Full workspace URL including scheme.

    Returns:
        A dict with ``display_name`` and ``user_name`` keys.  Values
        default to ``"Unknown"`` / ``""`` on failure.
    """
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
    """Execute a Databricks REST API call and return a normalised result.

    Handles both read (``GET`` / ``DELETE``) and write (``POST`` /
    ``PUT`` / ``PATCH``) methods, automatically routing parameters to
    query string or JSON body as appropriate.

    Args:
        method: HTTP method (case-insensitive).
        path: API path relative to the workspace host
            (e.g. ``/api/2.0/clusters/list``).
        token: Bearer token for authorisation.
        host: Full workspace URL including scheme.
        query_params: Optional mapping of query-string parameters.
            ``None`` and empty-string values are stripped.
        body: Optional JSON-serialisable request body (used for
            non-read methods).
        timeout: Request timeout in seconds.

    Returns:
        A dict with the following keys:

        * ``status_code`` (int) -- HTTP status, or ``0`` on network
          errors.
        * ``elapsed_ms`` (int) -- Wall-clock time of the request.
        * ``data`` (dict | list) -- Parsed JSON response, or
          ``{"error": "<message>"}`` / ``{"_raw": "<text>"}`` on
          failure.
        * ``success`` (bool) -- ``True`` when the status code is 2xx.
        * ``error`` (str | None) -- Reason phrase or exception message
          on failure.
        * ``url`` (str) -- The fully-qualified URL that was called.
    """
    url = f"{host}{path}"
    # Legacy 1.2 Command Execution API uses form-encoded bodies, not JSON.
    is_legacy_form = path.startswith("/api/1.2/")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded" if is_legacy_form else "application/json",
        "User-Agent": "DatabricksAPIExplorer/1.0",
    }

    if query_params:
        query_params = {k: v for k, v in query_params.items() if v not in (None, "")}

    t0 = time.perf_counter()
    try:
        is_read = method.upper() in ("GET", "DELETE", "HEAD")
        if is_read:
            post_kwargs = {}
        elif is_legacy_form:
            form_body = body if isinstance(body, dict) else {}
            form_body = {k: v for k, v in form_body.items() if v not in (None, "")}
            post_kwargs = {"data": form_body}
        else:
            post_kwargs = {"json": body}
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            params=query_params if is_read else None,
            timeout=timeout,
            **post_kwargs,
        )
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        # Detect HTML login/sign-in pages returned instead of JSON —
        # this happens when the token is invalid, expired, or the host
        # requires browser-based authentication.
        content_type = response.headers.get("Content-Type", "")
        if "text/html" in content_type:
            return {
                "status_code": 401,
                "elapsed_ms": elapsed_ms,
                "data": {"error": "Authentication failed — the server returned a sign-in page instead of JSON. "
                         "Check that your token is valid and has not expired."},
                "success": False,
                "error": "Authentication required",
                "url": url,
            }

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
            "data": {"error": f"Request timed out after {timeout} seconds."},
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
