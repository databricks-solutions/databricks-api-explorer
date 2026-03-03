"""
Databricks API Explorer
Ultra-modern Databricks workspace API explorer built with Dash.

Run modes:
  Local        → auth via Databricks CLI profile (SSO / OAuth / PAT)
  Databricks App → auth via OBO (x-forwarded-access-token header)
"""

import json
import re
from typing import Any, Dict, List, Optional

import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, dcc, html, no_update
from flask import request as flask_request

import subprocess

from api_catalog import API_CATALOG, ENDPOINT_MAP, TOTAL_CATEGORIES, TOTAL_ENDPOINTS, get_endpoint_by_id
from auth import (
    DATABRICKS_PROFILE,
    IS_DATABRICKS_APP,
    _get_local_config,
    get_current_user_info,
    get_host,
    get_local_token,
    make_api_call,
)
from version import VERSION

# ── Dash init ─────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.CYBORG,
        dbc.icons.BOOTSTRAP,
    ],
    title="Databricks API Explorer",
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server


# ── JSON Syntax Highlighter (Dash components — no HTML injection) ─────────────
_TOKEN_RE = re.compile(
    r'("(?:[^"\\]|\\.)*")(\s*:)'            # 1,2 → key + colon
    r'|("(?:[^"\\]|\\.)*")'                  # 3   → string value
    r'|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)'  # 4   → number
    r'|(true|false)'                          # 5   → boolean
    r'|(null)'                                # 6   → null
    r'|([{}\[\],])'                           # 7   → punctuation
    r'|(\s+)',                                # 8   → whitespace
)


def highlight_json_components(json_str: str) -> html.Pre:
    """Token-based JSON highlighter returning Dash html components."""
    parts = []
    for m in _TOKEN_RE.finditer(json_str):
        g = m.group
        if g(1):   parts += [html.Span(g(1), className="jk"), g(2)]
        elif g(3): parts.append(html.Span(g(3), className="jv"))
        elif g(4): parts.append(html.Span(g(4), className="jn"))
        elif g(5): parts.append(html.Span(g(5), className="jb"))
        elif g(6): parts.append(html.Span(g(6), className="jbn"))
        elif g(7): parts.append(html.Span(g(7), className="jp"))
        elif g(8): parts.append(g(8))
        else:      parts.append(m.group(0))
    return html.Pre(parts, className="json-viewer")


# ── UI Helpers ────────────────────────────────────────────────────────────────
METHOD_COLORS = {"GET": "info", "POST": "warning", "PUT": "primary", "DELETE": "danger", "PATCH": "success"}


def method_badge(method: str) -> dbc.Badge:
    return dbc.Badge(method, color=METHOD_COLORS.get(method, "secondary"), className="method-badge")


def build_response_panel(result: Dict[str, Any]) -> html.Div:
    code = result["status_code"]
    ms = result["elapsed_ms"]
    data = result["data"]

    if 200 <= code < 300:
        status_color, status_icon = "success", "bi-check-circle-fill"
    elif code == 0:
        status_color, status_icon = "danger", "bi-x-octagon-fill"
    elif 400 <= code < 500:
        status_color, status_icon = "danger", "bi-x-circle-fill"
    else:
        status_color, status_icon = "warning", "bi-exclamation-circle-fill"

    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    truncated = len(json_str) > 50_000
    if truncated:
        json_str = json_str[:50_000] + "\n\n... [truncated]"

    item_count = ""
    if isinstance(data, list):
        item_count = f" · {len(data)} items"
    elif isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                item_count = f" · {len(v)} items"
                break

    return html.Div([
        html.Div([
            dbc.Badge(
                [html.I(className=f"bi {status_icon} me-1"), str(code) if code else "Error"],
                color=status_color, className="status-badge",
            ),
            html.Span(f"{ms}ms", className="timing-label font-mono ms-2"),
            html.Span(item_count, className="timing-label") if item_count else None,
            html.Span(" [truncated]", className="truncation-notice") if truncated else None,
            html.Span(result.get("url", ""), className="response-url ms-auto"),
        ], className="response-meta"),
        html.Div(highlight_json_components(json_str), className="json-viewer-wrapper"),
    ], className="response-container")


def build_error_panel(message: str) -> html.Div:
    return html.Div([
        html.Div([
            html.I(className="bi bi-exclamation-triangle-fill me-2 text-danger"),
            html.Span(message, className="text-danger"),
        ], className="error-panel"),
    ], className="response-container")


def build_param_form(endpoint: Dict) -> html.Div:
    params: List[Dict] = endpoint.get("params", [])
    method: str = endpoint.get("method", "GET")
    body_template: Optional[str] = endpoint.get("body")
    rows = []

    for p in params:
        label_row = html.Div([
            html.Span(p["name"], className="param-name"),
            dbc.Badge("required", color="danger", className="param-badge") if p.get("required")
            else dbc.Badge("optional", color="secondary", className="param-badge"),
        ], className="param-label")

        inp = dbc.Input(
            id={"type": "param-input", "name": p["name"]},
            type="number" if p["type"] == "integer" else "text",
            placeholder=p.get("description", ""),
            value=p.get("default", "") or "",
            className="param-input font-mono",
        )
        rows.append(html.Div([
            label_row,
            html.Div(p.get("description", ""), className="param-desc"),
            inp,
        ], className="param-row"))

    if not params and not body_template:
        rows.append(html.Div([
            html.I(className="bi bi-check-circle-fill me-2 text-success"),
            "No parameters required — click Execute to call this endpoint.",
        ], className="no-params"))

    show_body = body_template is not None or method == "POST"
    if show_body:
        rows.append(html.Hr(className="divider"))
        rows.append(html.Div([
            html.Div([
                html.Span("Request Body", className="param-name"),
                dbc.Badge("JSON", color="info", className="param-badge ms-2"),
            ], className="param-label mb-1"),
            dbc.Textarea(
                id="body-textarea",
                value=body_template or "{}",
                className="body-textarea font-mono mt-1",
                rows=8,
            ),
        ], className="param-row"))
    else:
        rows.append(dbc.Textarea(id="body-textarea", value="", style={"display": "none"}))

    return html.Div(rows, className="param-form")


# ── Sidebar ───────────────────────────────────────────────────────────────────
def build_sidebar() -> html.Div:
    items = []
    for cat_name, cat in API_CATALOG.items():
        btns = [
            html.Button(
                [
                    html.Span(ep["method"], className=f"ep-method ep-{ep['method'].lower()}"),
                    html.Span(ep["name"], className="ep-name"),
                ],
                id={"type": "endpoint-btn", "id": ep["id"]},
                n_clicks=0,
                className="endpoint-btn",
                title=ep.get("description", ""),
            )
            for ep in cat["endpoints"]
        ]
        title_el = html.Span([
            html.I(className=f"bi {cat['icon']} me-2", style={"color": cat["color"]}),
            cat_name,
            dbc.Badge(str(len(cat["endpoints"])), color="secondary", className="ms-auto endpoint-count"),
        ], className="cat-header d-flex align-items-center w-100")

        items.append(dbc.AccordionItem(
            html.Div(btns, className="endpoint-list"),
            title=title_el,
        ))

    return html.Div([
        html.Div([
            html.I(className="bi bi-search"),
            dbc.Input(id="search-input", placeholder="Search APIs…", type="text", className="sidebar-search"),
        ], className="search-wrapper"),
        dbc.Accordion(items, start_collapsed=True, id="api-accordion", className="api-accordion"),
    ], id="sidebar", className="sidebar")


# ── Top Bar ───────────────────────────────────────────────────────────────────
_MODE_BADGE = (
    dbc.Badge([html.I(className="bi bi-cloud-fill me-1"), "Databricks App"], color="info", className="mode-badge")
    if IS_DATABRICKS_APP else
    dbc.Badge([html.I(className="bi bi-laptop me-1"), "Local Mode"], color="warning", className="mode-badge")
)

TOPBAR = dbc.Navbar(
    dbc.Container([
        html.A([
            html.Span("Databricks", className="brand-db"),
            html.Span(" API Explorer", className="brand-rest"),
        ], href="/", className="navbar-brand d-flex align-items-center text-decoration-none"),
        html.Div([
            html.Span(VERSION, className="version-badge me-2"),
            _MODE_BADGE,
            html.Span(id="host-display", className="host-display ms-3"),
            # Clickable user chip — opens auth modal
            html.Button(
                html.Span(id="user-display"),
                id="user-btn",
                n_clicks=0,
                className="user-btn-trigger ms-3",
                title="Click to view auth details",
            ),
        ], className="d-flex align-items-center"),
    ], fluid=True),
    color="dark", dark=True, className="topbar",
)

# ── Auth Info Modal ───────────────────────────────────────────────────────────

def _auth_info_row(label: str, value: str) -> html.Div:
    return html.Div([
        html.Span(label, className="auth-info-label"),
        html.Span(value or "—", className="auth-info-value font-mono"),
    ], className="auth-info-row")


def build_auth_modal_body() -> html.Div:
    """Fetch live auth info and render the modal body."""
    host = get_host()

    if IS_DATABRICKS_APP:
        token = flask_request.headers.get("x-forwarded-access-token")
        auth_mode = "Databricks App (OBO)"
        auth_type = "on-behalf-of"
        profile_name = "N/A (managed by platform)"
    else:
        token = get_local_token()
        auth_mode = "Local (CLI profile)"
        profile_name = DATABRICKS_PROFILE
        try:
            cfg = _get_local_config()
            auth_type = getattr(cfg, "auth_type", None) or "unknown"
        except Exception:
            auth_type = "unknown"

    # Fetch full SCIM /Me profile
    scim_data: Dict = {}
    if token and host:
        r = make_api_call("GET", "/api/2.0/preview/scim/v2/Me", token, host)
        if r["success"]:
            scim_data = r["data"]

    display_name = scim_data.get("displayName", "Unknown")
    username = scim_data.get("userName", "")
    active = scim_data.get("active", True)
    emails: List[Dict] = scim_data.get("emails", [])
    groups: List[Dict] = scim_data.get("groups", [])
    entitlements: List[Dict] = scim_data.get("entitlements", [])
    roles: List[Dict] = scim_data.get("roles", [])
    user_id = scim_data.get("id", "")

    primary_email = next((e["value"] for e in emails if e.get("primary")), emails[0]["value"] if emails else "")
    avatar_letter = (display_name[0] if display_name and display_name != "Unknown" else username[0] if username else "?").upper()

    auth_type_labels = {
        "pat": "Personal Access Token",
        "oauth-m2m": "OAuth M2M (Client Credentials)",
        "external-browser": "OAuth (Browser / SSO)",
        "azure-client-secret": "Azure Service Principal",
        "azure-msi": "Azure Managed Identity",
        "on-behalf-of": "On-Behalf-Of (OBO)",
        "unknown": "Unknown",
    }
    auth_type_display = auth_type_labels.get(auth_type, auth_type)

    return html.Div([
        # ── Profile header ────────────────────────────────────────────
        html.Div([
            html.Div(avatar_letter, className="auth-avatar"),
            html.Div([
                html.Div(display_name, className="auth-display-name"),
                html.Div(username, className="auth-username"),
                html.Div([
                    dbc.Badge(
                        [html.I(className="bi bi-circle-fill me-1"), "Active" if active else "Inactive"],
                        color="success" if active else "danger",
                        className="auth-active-badge",
                    ),
                ], className="mt-1"),
            ]),
        ], className="auth-profile-header"),

        html.Hr(className="divider"),

        # ── Auth details ─────────────────────────────────────────────
        html.Div("Authentication", className="auth-section-title"),
        html.Div([
            _auth_info_row("Mode", auth_mode),
            _auth_info_row("Auth type", auth_type_display),
            _auth_info_row("Workspace", host.replace("https://", "")),
            _auth_info_row("Profile", profile_name),
            _auth_info_row("User ID", user_id),
            _auth_info_row("Username", username),
            _auth_info_row("Email", primary_email),
        ], className="auth-info-table"),

        # ── All emails ────────────────────────────────────────────────
        html.Div([
            html.Hr(className="divider"),
            html.Div("Email Addresses", className="auth-section-title"),
            html.Div([
                html.Div([
                    html.Span(e.get("value", ""), className="font-mono small"),
                    dbc.Badge(e.get("type", ""), color="secondary", className="ms-2 small"),
                    dbc.Badge("primary", color="info", className="ms-1 small") if e.get("primary") else None,
                ], className="mb-1")
                for e in emails
            ]) if emails else html.Div("—", className="text-muted small"),
        ]) if emails else None,

        # ── Groups ───────────────────────────────────────────────────
        html.Div([
            html.Hr(className="divider"),
            html.Div(f"Groups ({len(groups)})", className="auth-section-title"),
            html.Div([
                dbc.Badge(g.get("display", g.get("value", "?")), color="secondary", className="me-1 mb-1 auth-group-badge")
                for g in groups[:30]
            ]) if groups else html.Div("No groups", className="text-muted small"),
            html.Div(f"… and {len(groups) - 30} more", className="text-muted small mt-1") if len(groups) > 30 else None,
        ]),

        # ── Entitlements & roles ──────────────────────────────────────
        html.Div([
            html.Hr(className="divider"),
            html.Div("Entitlements & Roles", className="auth-section-title"),
            html.Div([
                dbc.Badge(e.get("value", "?"), color="info", className="me-1 mb-1")
                for e in entitlements + roles
            ]) if (entitlements or roles) else html.Div("None", className="text-muted small"),
        ]),

        # ── Re-auth (local only) ──────────────────────────────────────
        html.Div([
            html.Hr(className="divider"),
            html.Div("Re-authenticate", className="auth-section-title"),
            html.P(
                f"Trigger a new SSO login for profile '{DATABRICKS_PROFILE}'. "
                "A browser window will open — complete the login, then refresh.",
                className="text-muted small mb-3",
            ),
            html.Div([
                html.Button(
                    [html.I(className="bi bi-arrow-repeat me-2"), "Re-authenticate with SSO"],
                    id="reauth-btn",
                    n_clicks=0,
                    className="reauth-btn",
                ),
                html.Div(id="reauth-status", className="mt-2"),
            ]),
            html.Div([
                html.Span("Manual command:", className="text-muted small me-2"),
                html.Code(
                    f"databricks auth login --profile {DATABRICKS_PROFILE}",
                    className="font-mono small auth-cmd",
                ),
            ], className="mt-3"),
        ]) if not IS_DATABRICKS_APP else html.Div([
            html.Hr(className="divider"),
            html.Div("Re-authenticate", className="auth-section-title"),
            html.P(
                "Token refresh is managed automatically by Databricks Apps via OBO. "
                "No manual re-authentication is required.",
                className="text-muted small",
            ),
        ]),
    ], className="auth-modal-body")

# ── Welcome Panel ─────────────────────────────────────────────────────────────
WELCOME = html.Div([
    html.Div([
        html.Div("◈", className="welcome-icon"),
        html.H3("Select an API Endpoint", className="welcome-title"),
        html.P(
            "Choose a category from the sidebar, then click any endpoint to explore "
            "Databricks workspace APIs in real-time.",
            className="welcome-subtitle",
        ),
        html.Hr(className="welcome-divider"),
        html.Div([
            html.Div([html.I(className="bi bi-lightning-fill me-2", style={"color": "#00d4ff"}), f"{TOTAL_ENDPOINTS} endpoints"], className="stat-pill"),
            html.Div([html.I(className="bi bi-collection-fill me-2", style={"color": "#00d4ff"}), f"{TOTAL_CATEGORIES} categories"], className="stat-pill"),
            html.Div([html.I(className="bi bi-shield-check-fill me-2", style={"color": "#00d4ff"}), "OBO + SSO auth"], className="stat-pill"),
        ], className="welcome-stats"),
    ], className="welcome-content"),
], className="welcome-panel")


# ── App Layout ────────────────────────────────────────────────────────────────
_RESPONSE_EMPTY = html.Div([
    html.I(className="bi bi-terminal"),
    html.Div("Select an endpoint and click Execute"),
], className="response-empty")

# ── Auth Modal component ──────────────────────────────────────────────────────
AUTH_MODAL = dbc.Modal([
    dbc.ModalHeader(
        html.Div([
            html.Div([html.I(className="bi bi-shield-lock me-2"), "Identity & Auth"], className="modal-title-text"),
        ]),
        close_button=True,
        className="auth-modal-header",
    ),
    dbc.ModalBody(html.Div(id="auth-modal-body"), className="auth-modal-body-wrap"),
], id="auth-modal", is_open=False, size="lg", scrollable=True, className="auth-modal")


# Static layout — both panels always in DOM for reliable callback targeting.
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="selected-endpoint"),
    AUTH_MODAL,

    TOPBAR,

    html.Div([
        build_sidebar(),

        html.Div([
            # Left: form panel (scrollable, fixed width)
            html.Div(WELCOME, id="endpoint-detail", className="form-panel"),

            # Right: response fills ALL remaining space
            html.Div([
                html.Div(_RESPONSE_EMPTY, id="response-container", className="response-container"),
            ], className="response-panel"),
        ], className="main-content"),
    ], className="app-body"),
], className="app-root")


# ── Callbacks ─────────────────────────────────────────────────────────────────

@app.callback(
    Output("user-display", "children"),
    Output("host-display", "children"),
    Input("url", "pathname"),
)
def init_on_load(_):
    host = get_host()
    host_label = html.Span(
        host.replace("https://", "").replace("http://", ""),
        className="text-muted",
    ) if host else html.Span("(no host)", className="text-warning")

    token = flask_request.headers.get("x-forwarded-access-token") if IS_DATABRICKS_APP else get_local_token()

    if token and host:
        info = get_current_user_info(token, host)
        name = info.get("display_name") or info.get("user_name") or "Unknown"
        user_el = html.Span([
            html.I(className="bi bi-person-circle me-1"),
            name,
            html.I(className="bi bi-chevron-down ms-1 small"),
        ], className="user-chip")
    else:
        user_el = html.Span([
            html.I(className="bi bi-person-circle me-1"),
            "Not authenticated",
        ], className="user-chip text-warning")

    return user_el, host_label


@app.callback(
    Output("auth-modal", "is_open"),
    Output("auth-modal-body", "children"),
    Input("user-btn", "n_clicks"),
    State("auth-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_auth_modal(n_clicks, is_open):
    if not n_clicks:
        return no_update, no_update
    if is_open:
        return False, no_update
    return True, build_auth_modal_body()


@app.callback(
    Output("reauth-status", "children"),
    Input("reauth-btn", "n_clicks"),
    prevent_initial_call=True,
)
def reauth(n_clicks):
    if not n_clicks:
        return no_update
    try:
        subprocess.Popen(
            ["databricks", "auth", "login", "--profile", DATABRICKS_PROFILE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return html.Div([
            html.I(className="bi bi-check-circle-fill me-2 text-success"),
            "Browser opened — complete the SSO login, then ",
            html.A("refresh the page", href="/", className="text-info"),
            " to apply the new token.",
        ], className="small")
    except FileNotFoundError:
        return html.Div([
            html.I(className="bi bi-x-circle-fill me-2 text-danger"),
            "Databricks CLI not found. Install it and run the command below manually.",
        ], className="small text-danger")
    except Exception as exc:
        return html.Div(str(exc), className="small text-danger")


@app.callback(
    Output("selected-endpoint", "data"),
    Output({"type": "endpoint-btn", "id": ALL}, "className"),
    Input({"type": "endpoint-btn", "id": ALL}, "n_clicks"),
    State({"type": "endpoint-btn", "id": ALL}, "id"),
    prevent_initial_call=True,
)
def select_endpoint(n_clicks_list, btn_ids):
    from dash import callback_context as ctx
    if not ctx.triggered:
        return no_update, no_update

    triggered_prop = ctx.triggered[0]["prop_id"].split(".")[0]
    try:
        clicked_id = json.loads(triggered_prop)["id"]
    except (json.JSONDecodeError, KeyError):
        return no_update, no_update

    endpoint = get_endpoint_by_id(clicked_id)
    if not endpoint:
        return no_update, no_update

    classnames = [
        "endpoint-btn active" if btn["id"] == clicked_id else "endpoint-btn"
        for btn in btn_ids
    ]
    return endpoint, classnames


@app.callback(
    Output("endpoint-detail", "children"),
    Output("endpoint-detail", "className"),
    Input("selected-endpoint", "data"),
    prevent_initial_call=True,
)
def render_endpoint_detail(endpoint: Optional[Dict]):
    if not endpoint:
        return WELCOME, "form-panel"

    method = endpoint.get("method", "GET")
    cat_color = endpoint.get("category_color", "#00d4ff")

    content = html.Div([
        html.Div([
            method_badge(method),
            html.Div([
                html.Div(endpoint["name"], className="endpoint-name"),
                html.Div(html.Span(endpoint.get("category", ""), style={"color": cat_color}), className="endpoint-category"),
            ], className="endpoint-meta"),
        ], className="endpoint-header"),

        html.Div(endpoint["path"], className="endpoint-path font-mono"),
        html.Div(endpoint.get("description", ""), className="endpoint-desc"),
        html.Hr(className="divider"),
        html.Div("Parameters", className="param-section-title"),
        build_param_form(endpoint),
        html.Hr(className="divider"),

        html.Button(
            [html.I(className="bi bi-play-fill me-2"), "Execute"],
            id="execute-btn",
            n_clicks=0,
            className="execute-btn",
        ),
    ], className="endpoint-card")

    return content, "form-panel"


@app.callback(
    Output("response-container", "children"),
    Input("execute-btn", "n_clicks"),
    State("selected-endpoint", "data"),
    State({"type": "param-input", "name": ALL}, "value"),
    State({"type": "param-input", "name": ALL}, "id"),
    State("body-textarea", "value"),
    prevent_initial_call=True,
)
def execute_api_call(n_clicks, endpoint, param_values, param_ids, body_text):
    if not n_clicks or not endpoint:
        return no_update

    # Build query params dict
    params: Dict[str, Any] = {}
    ep_param_map = {p["name"]: p for p in endpoint.get("params", [])}
    for pid, pval in zip(param_ids, param_values):
        name = pid["name"]
        if pval in (None, ""):
            continue
        if ep_param_map.get(name, {}).get("type") == "integer":
            try:
                params[name] = int(float(pval))
            except (ValueError, TypeError):
                params[name] = pval
        else:
            params[name] = pval

    # Substitute path parameters
    path: str = endpoint["path"]
    for pp in endpoint.get("path_params", []):
        val = params.pop(pp, "")
        if not val:
            return build_error_panel(f"Path parameter '{pp}' is required.")
        path = path.replace(f"{{{pp}}}", str(val))

    # Parse JSON body for POST
    method = endpoint.get("method", "GET")
    body = None
    if method == "POST" and body_text and body_text.strip():
        try:
            body = json.loads(body_text)
        except json.JSONDecodeError as e:
            return build_error_panel(f"Invalid JSON body: {e}")

    # Resolve auth token
    if IS_DATABRICKS_APP:
        token = flask_request.headers.get("x-forwarded-access-token")
        if not token:
            return build_error_panel(
                "No user token found. Ensure 'User authorization' (OBO) is enabled for this app."
            )
    else:
        token = get_local_token()
        from auth import DATABRICKS_PROFILE
        if not token:
            return build_error_panel(
                f"Could not get token from CLI profile '{DATABRICKS_PROFILE}'. "
                "Ensure you are authenticated: databricks auth login --profile " + DATABRICKS_PROFILE
            )

    host = get_host()
    if not host:
        return build_error_panel("Workspace host not configured.")

    result = make_api_call(
        method=method,
        path=path,
        token=token,
        host=host,
        query_params=params if method == "GET" else None,
        body=body,
    )
    return build_response_panel(result)


@app.callback(
    Output({"type": "endpoint-btn", "id": ALL}, "style"),
    Input("search-input", "value"),
    State({"type": "endpoint-btn", "id": ALL}, "id"),
)
def filter_endpoints(query, btn_ids):
    if not query or not query.strip():
        return [{"display": "flex"} for _ in btn_ids]
    q = query.strip().lower()
    return [
        {"display": "flex"} if (
            q in ENDPOINT_MAP.get(b["id"], {}).get("name", "").lower()
            or q in ENDPOINT_MAP.get(b["id"], {}).get("path", "").lower()
            or q in ENDPOINT_MAP.get(b["id"], {}).get("category", "").lower()
            or q in ENDPOINT_MAP.get(b["id"], {}).get("method", "").lower()
        ) else {"display": "none"}
        for b in btn_ids
    ]


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    port = int(os.getenv("DATABRICKS_APP_PORT", "8050"))
    app.run(debug=not IS_DATABRICKS_APP, host="0.0.0.0", port=port)
