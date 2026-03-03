"""
Databricks API Explorer
Ultra-modern Databricks workspace API explorer built with Dash.

Run modes:
  Local        → auth via Databricks CLI profile (SSO / OAuth / PAT) or custom URL
  Databricks App → auth via OBO (x-forwarded-access-token header)
"""

import json
import re
import subprocess
from typing import Any, Dict, List, Optional

import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, dcc, html, no_update
from flask import request as flask_request

from api_catalog import API_CATALOG, ENDPOINT_MAP, TOTAL_CATEGORIES, TOTAL_ENDPOINTS, extract_chips, get_endpoint_by_id
from auth import (
    DATABRICKS_PROFILE,
    IS_DATABRICKS_APP,
    _get_local_config,
    get_cli_profiles,
    get_current_user_info,
    get_host,
    get_local_token,
    get_workspace_name,
    make_api_call,
    resolve_local_connection,
)
from version import VERSION

# ── Dash init ─────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG, dbc.icons.BOOTSTRAP],
    title="Databricks API Explorer",
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server

# Default connection config
_DEFAULT_CONN = {"mode": "profile", "profile": DATABRICKS_PROFILE}


# ── JSON Syntax Highlighter ───────────────────────────────────────────────────
_TOKEN_RE = re.compile(
    r'("(?:[^"\\]|\\.)*")(\s*:)'
    r'|("(?:[^"\\]|\\.)*")'
    r'|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)'
    r'|(true|false)'
    r'|(null)'
    r'|([{}\[\],])'
    r'|(\s+)',
)


def highlight_json_components(json_str: str) -> html.Pre:
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


def _resolve_conn(conn_config):
    """Return (host, token) based on app mode or conn_config."""
    if IS_DATABRICKS_APP:
        return get_host(), flask_request.headers.get("x-forwarded-access-token")
    return resolve_local_connection(conn_config or _DEFAULT_CONN)


def build_response_panel(result: Dict[str, Any], chips: Optional[List] = None) -> html.Div:
    code, ms, data = result["status_code"], result["elapsed_ms"], result["data"]
    if 200 <= code < 300:   status_color, icon = "success", "bi-check-circle-fill"
    elif code == 0:         status_color, icon = "danger",  "bi-x-octagon-fill"
    elif 400 <= code < 500: status_color, icon = "danger",  "bi-x-circle-fill"
    else:                   status_color, icon = "warning", "bi-exclamation-circle-fill"

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

    chips_row = html.Div([
        html.Span([html.I(className="bi bi-cursor-fill me-1"), "Click to open:"], className="chips-label"),
        *[
            html.Button(
                chip["label"],
                id={"type": "id-chip", "idx": i},
                n_clicks=0,
                className="id-chip",
                title=chip["title"],
            )
            for i, chip in enumerate(chips)
        ],
    ], className="chips-row") if chips else None

    return html.Div([
        html.Div([
            dbc.Badge([html.I(className=f"bi {icon} me-1"), str(code) if code else "Error"],
                      color=status_color, className="status-badge"),
            html.Span(f"{ms}ms", className="timing-label font-mono ms-2"),
            html.Span(item_count, className="timing-label") if item_count else None,
            html.Span(" [truncated]", className="truncation-notice") if truncated else None,
            html.Span(result.get("url", ""), className="response-url ms-auto"),
        ], className="response-meta"),
        chips_row,
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
        rows.append(html.Div([label_row, html.Div(p.get("description", ""), className="param-desc"), inp], className="param-row"))

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
            dbc.Textarea(id="body-textarea", value=body_template or "{}", className="body-textarea font-mono mt-1", rows=8),
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
                [html.Span(ep["method"], className=f"ep-method ep-{ep['method'].lower()}"),
                 html.Span(ep["name"], className="ep-name")],
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
        items.append(dbc.AccordionItem(html.Div(btns, className="endpoint-list"), title=title_el))

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
            html.Div([
                html.Span(id="workspace-name-display", className="workspace-name"),
                html.Span(id="host-display", className="host-display"),
            ], className="workspace-info ms-3"),
            html.Button(
                html.Span(id="user-display"),
                id="user-btn",
                n_clicks=0,
                className="user-btn-trigger ms-3",
                title="Connection & identity",
            ),
        ], className="d-flex align-items-center"),
    ], fluid=True),
    color="dark", dark=True, className="topbar",
)


# ── User Dropdown Panel ───────────────────────────────────────────────────────
# Always in DOM, shown/hidden via style. Positioned fixed below topbar right edge.

def _profile_section():
    # Options are populated dynamically via toggle_dropdown callback on each open
    return html.Div([
        html.Label("Profile", className="conn-label"),
        dbc.Select(
            id="profile-select",
            options=[],
            value="",
            className="conn-select",
        ),
        html.Div(id="profile-auth-type", className="conn-hint mt-1"),
        html.Button(
            [html.I(className="bi bi-arrow-repeat me-2"), "Re-authenticate with SSO"],
            id="reauth-btn",
            n_clicks=0,
            className="reauth-btn mt-2",
        ),
        html.Div(id="reauth-status", className="mt-2 small"),
    ], id="profile-section")


def _custom_section():
    return html.Div([
        html.Label("Workspace URL", className="conn-label"),
        dbc.Input(
            id="custom-host-input",
            type="url",
            placeholder="https://adb-xxxx.azuredatabricks.net",
            className="conn-input font-mono",
        ),
        html.Label("Personal Access Token", className="conn-label mt-2"),
        dbc.Input(
            id="custom-token-input",
            type="password",
            placeholder="dapi…",
            className="conn-input font-mono",
        ),
    ], id="custom-section", style={"display": "none"})


USER_DROPDOWN = html.Div([
    # ── Identity section ──────────────────────────────────────
    html.Div([
        html.Div(id="popup-avatar", className="auth-avatar"),
        html.Div([
            html.Div(id="popup-name", className="auth-display-name"),
            html.Div(id="popup-username", className="auth-username"),
            html.Div(id="popup-status"),
        ]),
    ], className="auth-profile-header px-4 pt-3 pb-2"),

    html.Div(id="popup-auth-details", className="px-4 pb-2"),

    html.Hr(className="divider mx-3"),

    # ── Connection section ────────────────────────────────────
    html.Div([
        html.Div("Connection", className="auth-section-title mb-2"),
        dbc.RadioItems(
            id="conn-mode-radio",
            options=[
                {"label": "CLI Profile", "value": "profile"},
                {"label": "Custom URL", "value": "custom"},
            ],
            value="profile",
            inline=True,
            className="conn-mode-radio mb-3",
            input_class_name="conn-radio-input",
            label_class_name="conn-radio-label",
        ),
        _profile_section(),
        _custom_section(),
        html.Button(
            [html.I(className="bi bi-plug-fill me-2"), "Connect"],
            id="apply-conn-btn",
            n_clicks=0,
            className="apply-btn mt-3",
        ),
        html.Div(id="conn-status", className="mt-2 small"),
    ], className="px-4 pb-3"),

    html.Hr(className="divider mx-3"),

    # ── Groups section ────────────────────────────────────────
    html.Div([
        html.Div("Groups", className="auth-section-title mb-2"),
        html.Div(id="popup-groups"),
    ], className="px-4 pb-4"),

], id="user-dropdown", style={"display": "none"}, className="user-dropdown")


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

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="selected-endpoint"),
    dcc.Store(id="conn-config", data=_DEFAULT_CONN),
    dcc.Store(id="chips-meta", data=[]),

    TOPBAR,
    USER_DROPDOWN,  # fixed dropdown, outside normal flow

    html.Div([
        build_sidebar(),
        html.Div([
            html.Div(WELCOME, id="endpoint-detail", className="form-panel"),
            html.Div([
                html.Div(_RESPONSE_EMPTY, id="response-container", className="response-container"),
            ], className="response-panel"),
        ], className="main-content"),
    ], className="app-body"),
], className="app-root")


# ── Callbacks ─────────────────────────────────────────────────────────────────

# 1. Init: populate topbar on page load or connection change
@app.callback(
    Output("user-display", "children"),
    Output("host-display", "children"),
    Output("workspace-name-display", "children"),
    Input("url", "pathname"),
    Input("conn-config", "data"),
)
def init_on_load(_, conn_config):
    host, token = _resolve_conn(conn_config)
    host_label = html.Span(
        (host or "").replace("https://", ""),
        className="text-muted",
    ) if host else html.Span("(not connected)", className="text-warning")

    ws_name = None
    if token and host:
        info = get_current_user_info(token, host)
        name = info.get("display_name") or info.get("user_name") or "Unknown"
        user_el = html.Span([
            html.I(className="bi bi-person-circle me-1"),
            name,
            html.I(className="bi bi-chevron-down ms-1 small"),
        ], className="user-chip")
        ws_name = get_workspace_name(token, host)
    else:
        user_el = html.Span([
            html.I(className="bi bi-person-circle me-1"),
            "Not connected",
            html.I(className="bi bi-chevron-down ms-1 small"),
        ], className="user-chip text-warning")

    ws_name_el = html.Span(
        [html.I(className="bi bi-building me-1"), ws_name],
        className="workspace-name-text"
    ) if ws_name else None

    return user_el, host_label, ws_name_el


# 2. Toggle dropdown and populate identity info
@app.callback(
    Output("user-dropdown", "style"),
    Output("popup-avatar", "children"),
    Output("popup-name", "children"),
    Output("popup-username", "children"),
    Output("popup-status", "children"),
    Output("popup-auth-details", "children"),
    Output("popup-groups", "children"),
    Output("conn-mode-radio", "value"),
    Output("profile-select", "value"),
    Output("profile-select", "options"),
    Input("user-btn", "n_clicks"),
    State("user-dropdown", "style"),
    State("conn-config", "data"),
    prevent_initial_call=True,
)
def toggle_dropdown(n_clicks, current_style, conn_config):
    # Close if already open
    if current_style and current_style.get("display") != "none":
        return {"display": "none"}, *([no_update] * 9)

    conn_config = conn_config or _DEFAULT_CONN
    host, token = _resolve_conn(conn_config)

    # Refresh profile list from disk every time the dropdown opens
    profiles = get_cli_profiles()
    profile_options = [{"label": p, "value": p} for p in profiles]
    current_profile = conn_config.get("profile", DATABRICKS_PROFILE)
    if current_profile not in profiles and profiles:
        current_profile = profiles[0]

    scim: Dict = {}
    if token and host:
        r = make_api_call("GET", "/api/2.0/preview/scim/v2/Me", token, host)
        if r["success"]:
            scim = r["data"]

    display_name = scim.get("displayName", "Unknown")
    username = scim.get("userName", "")
    active = scim.get("active", True)
    groups: List[Dict] = scim.get("groups", [])
    entitlements: List[Dict] = scim.get("entitlements", [])
    emails: List[Dict] = scim.get("emails", [])
    primary_email = next((e["value"] for e in emails if e.get("primary")), emails[0]["value"] if emails else "")
    user_id = scim.get("id", "")

    letter = (display_name[0] if display_name not in ("", "Unknown") else username[0] if username else "?").upper()

    # Auth type
    if IS_DATABRICKS_APP:
        auth_type_display = "On-Behalf-Of (OBO)"
    elif conn_config.get("mode") == "custom":
        auth_type_display = "Personal Access Token"
    else:
        try:
            cfg = _get_local_config()
            raw = getattr(cfg, "auth_type", None) or "unknown"
            auth_type_display = {
                "pat": "Personal Access Token",
                "oauth-m2m": "OAuth M2M",
                "external-browser": "OAuth (Browser / SSO)",
                "azure-client-secret": "Azure Service Principal",
                "azure-msi": "Azure Managed Identity",
            }.get(raw, raw)
        except Exception:
            auth_type_display = "Unknown"

    auth_details = html.Div([
        html.Div([html.Span("Auth", className="auth-info-label"), html.Span(auth_type_display, className="auth-info-value font-mono")], className="auth-info-row"),
        html.Div([html.Span("Host", className="auth-info-label"), html.Span((host or "—").replace("https://", ""), className="auth-info-value font-mono small")], className="auth-info-row"),
        html.Div([html.Span("Email", className="auth-info-label"), html.Span(primary_email or "—", className="auth-info-value small")], className="auth-info-row") if primary_email else None,
        html.Div([html.Span("User ID", className="auth-info-label"), html.Span(user_id or "—", className="auth-info-value font-mono small")], className="auth-info-row") if user_id else None,
    ], className="auth-info-table")

    groups_el = html.Div([
        dbc.Badge(g.get("display", g.get("value", "?")), color="secondary", className="me-1 mb-1 auth-group-badge")
        for g in groups[:20]
    ] + ([html.Span(f"+{len(groups)-20} more", className="text-muted small")] if len(groups) > 20 else [])
    ) if groups else html.Span("No groups", className="text-muted small")

    status_el = dbc.Badge(
        [html.I(className="bi bi-circle-fill me-1"), "Active" if active else "Inactive"],
        color="success" if active else "danger", className="auth-active-badge mt-1",
    )

    return (
        {"display": "block"},
        letter,
        display_name,
        username,
        status_el,
        auth_details,
        groups_el,
        conn_config.get("mode", "profile"),
        current_profile,
        profile_options,
    )


# 3. Close dropdown when clicking user-btn again (handled above) or via ESC key not supported,
#    so provide close by clicking user-btn (toggle) — already handled in callback 2.

# 4. Show/hide profile vs custom section
@app.callback(
    Output("profile-section", "style"),
    Output("custom-section", "style"),
    Input("conn-mode-radio", "value"),
)
def toggle_conn_mode(mode):
    if mode == "profile":
        return {}, {"display": "none"}
    return {"display": "none"}, {}


# 5. Show auth type hint when profile changes
@app.callback(
    Output("profile-auth-type", "children"),
    Input("profile-select", "value"),
)
def show_profile_hint(profile):
    if not profile:
        return ""
    try:
        from databricks.sdk.core import Config
        cfg = Config(profile=profile)
        raw = getattr(cfg, "auth_type", None) or "?"
        label = {
            "pat": "Personal Access Token",
            "oauth-m2m": "OAuth M2M",
            "external-browser": "OAuth (Browser / SSO)",
            "azure-client-secret": "Azure Service Principal",
            "azure-msi": "Azure Managed Identity",
        }.get(raw, raw)
        host = (cfg.host or "").replace("https://", "")
        return html.Span(f"{label} · {host}", className="text-muted")
    except Exception as e:
        return html.Span(str(e), className="text-danger small")


# 6. Apply connection
@app.callback(
    Output("conn-config", "data"),
    Output("conn-status", "children"),
    Input("apply-conn-btn", "n_clicks"),
    State("conn-mode-radio", "value"),
    State("profile-select", "value"),
    State("custom-host-input", "value"),
    State("custom-token-input", "value"),
    prevent_initial_call=True,
)
def apply_connection(n_clicks, mode, profile, custom_host, custom_token):
    if not n_clicks:
        return no_update, no_update

    if mode == "profile":
        if not profile:
            return no_update, html.Span("No profile selected.", className="text-danger")
        new_config = {"mode": "profile", "profile": profile}
        # Quick validation
        host, token = resolve_local_connection(new_config)
        if not host or not token:
            return no_update, html.Span("Could not connect with this profile — check CLI auth.", className="text-danger")
        return new_config, html.Span([html.I(className="bi bi-check-circle-fill me-1 text-success"), f"Connected via profile '{profile}'"])

    else:  # custom
        host = (custom_host or "").strip().rstrip("/")
        token = (custom_token or "").strip()
        if not host:
            return no_update, html.Span("Workspace URL is required.", className="text-danger")
        if not token:
            return no_update, html.Span("Token is required.", className="text-danger")
        if not host.startswith("https://"):
            host = "https://" + host
        # Quick validation
        r = make_api_call("GET", "/api/2.0/preview/scim/v2/Me", token, host)
        if not r["success"]:
            return no_update, html.Span(f"Connection failed: {r['status_code']} {r.get('error','')}", className="text-danger")
        return {"mode": "custom", "host": host, "token": token}, html.Span([html.I(className="bi bi-check-circle-fill me-1 text-success"), f"Connected to {host.replace('https://','')}"])


# 7. Re-auth (profile mode only)
@app.callback(
    Output("reauth-status", "children"),
    Input("reauth-btn", "n_clicks"),
    State("profile-select", "value"),
    prevent_initial_call=True,
)
def reauth(n_clicks, profile):
    if not n_clicks:
        return no_update
    p = profile or DATABRICKS_PROFILE
    try:
        subprocess.Popen(
            ["databricks", "auth", "login", "--profile", p],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return html.Span([
            html.I(className="bi bi-check-circle-fill me-1 text-success"),
            "Browser opened — complete SSO, then click Connect.",
        ])
    except FileNotFoundError:
        return html.Span("Databricks CLI not found.", className="text-danger")
    except Exception as e:
        return html.Span(str(e), className="text-danger")


# 8. Select endpoint
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
    try:
        clicked_id = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])["id"]
    except (json.JSONDecodeError, KeyError):
        return no_update, no_update
    endpoint = get_endpoint_by_id(clicked_id)
    if not endpoint:
        return no_update, no_update
    classnames = ["endpoint-btn active" if b["id"] == clicked_id else "endpoint-btn" for b in btn_ids]
    return endpoint, classnames


# 9. Render endpoint detail
@app.callback(
    Output("endpoint-detail", "children"),
    Output("endpoint-detail", "className"),
    Input("selected-endpoint", "data"),
    prevent_initial_call=True,
)
def render_endpoint_detail(endpoint: Optional[Dict]):
    if not endpoint:
        return WELCOME, "form-panel"
    cat_color = endpoint.get("category_color", "#00d4ff")
    content = html.Div([
        html.Div([
            method_badge(endpoint.get("method", "GET")),
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
            id="execute-btn", n_clicks=0, className="execute-btn",
        ),
    ], className="endpoint-card")
    return content, "form-panel"


# 10. Execute API call
@app.callback(
    Output("response-container", "children"),
    Output("chips-meta", "data"),
    Input("execute-btn", "n_clicks"),
    State("selected-endpoint", "data"),
    State({"type": "param-input", "name": ALL}, "value"),
    State({"type": "param-input", "name": ALL}, "id"),
    State("body-textarea", "value"),
    State("conn-config", "data"),
    prevent_initial_call=True,
)
def execute_api_call(n_clicks, endpoint, param_values, param_ids, body_text, conn_config):
    if not n_clicks or not endpoint:
        return no_update, no_update

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

    path: str = endpoint["path"]
    for pp in endpoint.get("path_params", []):
        val = params.pop(pp, "")
        if not val:
            return build_error_panel(f"Path parameter '{pp}' is required."), []
        path = path.replace(f"{{{pp}}}", str(val))

    method = endpoint.get("method", "GET")
    body = None
    if method == "POST" and body_text and body_text.strip():
        try:
            body = json.loads(body_text)
        except json.JSONDecodeError as e:
            return build_error_panel(f"Invalid JSON body: {e}"), []

    host, token = _resolve_conn(conn_config)
    if not token:
        return build_error_panel("No auth token. Configure a connection in the user menu."), []
    if not host:
        return build_error_panel("No workspace host. Configure a connection in the user menu."), []

    result = make_api_call(
        method=method, path=path, token=token, host=host,
        query_params=params if method == "GET" else None, body=body,
    )
    chips = extract_chips(endpoint.get("id", ""), result["data"]) if result["success"] else []
    return build_response_panel(result, chips), chips


# 11. ID chip click — select the get endpoint and immediately execute it
@app.callback(
    Output("selected-endpoint", "data", allow_duplicate=True),
    Output({"type": "endpoint-btn", "id": ALL}, "className", allow_duplicate=True),
    Output("response-container", "children", allow_duplicate=True),
    Output("chips-meta", "data", allow_duplicate=True),
    Input({"type": "id-chip", "idx": ALL}, "n_clicks"),
    State("chips-meta", "data"),
    State({"type": "endpoint-btn", "id": ALL}, "id"),
    State("conn-config", "data"),
    prevent_initial_call=True,
)
def handle_chip_click(n_clicks_list, chips_meta, btn_ids, conn_config):
    from dash import callback_context as ctx
    if not ctx.triggered or not chips_meta or not any(n_clicks_list):
        return no_update, no_update, no_update, no_update
    try:
        idx = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])["idx"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return no_update, no_update, no_update, no_update
    if idx >= len(chips_meta):
        return no_update, no_update, no_update, no_update

    chip = chips_meta[idx]
    endpoint = get_endpoint_by_id(chip["get_id"])
    if not endpoint:
        return no_update, no_update, no_update, no_update

    # Highlight the get endpoint in the sidebar
    classnames = [
        "endpoint-btn active" if b["id"] == chip["get_id"] else "endpoint-btn"
        for b in btn_ids
    ]

    # Build path (handle path params vs query params)
    path = endpoint["path"]
    query_params: Dict[str, Any] = {}
    param_name, value = chip["param"], chip["value"]
    if param_name in endpoint.get("path_params", []):
        path = path.replace(f"{{{param_name}}}", value)
    else:
        query_params[param_name] = value

    host, token = _resolve_conn(conn_config)
    if not token:
        return endpoint, classnames, build_error_panel("No auth token."), []
    if not host:
        return endpoint, classnames, build_error_panel("No workspace host."), []

    result = make_api_call(
        method=endpoint.get("method", "GET"),
        path=path, token=token, host=host,
        query_params=query_params or None,
    )
    return endpoint, classnames, build_response_panel(result), []


# 12. Search filter
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
        {"display": "flex"} if any(
            q in ENDPOINT_MAP.get(b["id"], {}).get(k, "").lower()
            for k in ("name", "path", "category", "method")
        ) else {"display": "none"}
        for b in btn_ids
    ]


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os as _os
    port = int(_os.getenv("DATABRICKS_APP_PORT", "8050"))
    app.run(debug=not IS_DATABRICKS_APP, host="0.0.0.0", port=port)
