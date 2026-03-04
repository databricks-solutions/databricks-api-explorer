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
import time
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

app.index_string = '''<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 300 331'><path d='M283.923 136.449L150.144 213.624L6.88995 131.168L0 134.982V194.844L150.144 281.115L283.923 204.234V235.926L150.144 313.1L6.88995 230.644L0 234.458V244.729L150.144 331L300 244.729V184.867L293.11 181.052L150.144 263.215L16.0766 186.334V154.643L150.144 231.524L300 145.253V86.2713L292.536 81.8697L150.144 163.739L22.9665 90.9663L150.144 17.8998L254.641 78.055L263.828 72.773V65.4371L150.144 0L0 86.2713V95.6613L150.144 181.933L283.923 104.758V136.449Z' fill='%23FF3621'/></svg>">
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>'''

# Default connection config
_DEFAULT_CONN = {"mode": "profile", "profile": DATABRICKS_PROFILE}


# ── JSON Syntax Highlighter ───────────────────────────────────────────────────
# ── Pagination helpers ────────────────────────────────────────────────────────
_SKIP_LIST_KEYS = frozenset({"schemas"})


def _detect_next_page_token(data: Any) -> Optional[str]:
    """Return next_page_token if the response has more pages, else None."""
    if not isinstance(data, dict):
        return None
    token = data.get("next_page_token")
    return token if token and isinstance(token, str) else None


def _find_list_key(data: dict) -> Optional[str]:
    """Find the key holding the main item list in a paginated response."""
    for k, v in data.items():
        if isinstance(v, list) and k not in _SKIP_LIST_KEYS:
            return k
    return None


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


def highlight_json_components(json_str: str, id_link_data: Optional[List[Dict]] = None) -> html.Pre:
    """Syntax-highlight JSON. id_link_data chips make matching ID values inline-clickable."""
    # Build lookup: (id_field_name, str_value) → chip
    link_lookup: Dict = {}
    if id_link_data:
        for chip in id_link_data:
            link_lookup[(chip["id_field"], str(chip["value"]))] = chip

    link_counter = [0]   # mutable for closure; ensures unique button idx
    parts: List = []
    prev_key: Optional[str] = None

    for m in _TOKEN_RE.finditer(json_str):
        g = m.group
        if g(1):
            # key + colon consumed together by regex group 1+2
            prev_key = g(1)[1:-1]          # strip quotes to get bare field name
            parts += [html.Span(g(1), className="jk"), g(2)]
        elif g(3):
            raw = g(3)
            val_str = g(3)[1:-1]           # strip surrounding quotes
            chip = link_lookup.get((prev_key, val_str)) if prev_key else None
            if chip:
                idx = link_counter[0]; link_counter[0] += 1
                parts.append(html.Button(
                    raw,
                    id={"type": "id-link", "idx": idx,
                        "gid": chip["get_id"][:40],
                        "par": chip["param"][:40],
                        "val": val_str[:200]},
                    n_clicks=0, className="id-link-btn jv",
                ))
            else:
                parts.append(html.Span(raw, className="jv"))
            prev_key = None
        elif g(4):
            num_str = g(4)
            chip = link_lookup.get((prev_key, num_str)) if prev_key else None
            if chip:
                idx = link_counter[0]; link_counter[0] += 1
                parts.append(html.Button(
                    num_str,
                    id={"type": "id-link", "idx": idx,
                        "gid": chip["get_id"][:40],
                        "par": chip["param"][:40],
                        "val": num_str[:200]},
                    n_clicks=0, className="id-link-btn jn",
                ))
            else:
                parts.append(html.Span(num_str, className="jn"))
            prev_key = None
        elif g(5): parts.append(html.Span(g(5), className="jb"));  prev_key = None
        elif g(6): parts.append(html.Span(g(6), className="jbn")); prev_key = None
        elif g(7): parts.append(html.Span(g(7), className="jp")); prev_key = None  # punctuation resets context
        elif g(8): parts.append(g(8))                        # whitespace: keep prev_key
        else:      parts.append(m.group(0)); prev_key = None
    return html.Pre(parts, className="json-viewer")


# ── UI Helpers ────────────────────────────────────────────────────────────────
METHOD_COLORS = {"GET": "info", "POST": "warning", "PUT": "primary", "DELETE": "danger", "PATCH": "success"}

# Above this size syntax-highlight creates too many Dash components to serialize
_HIGHLIGHT_LIMIT = 100_000


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

    item_count = ""
    if isinstance(data, list):
        item_count = f" · {len(data)} items"
    elif isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                item_count = f" · {len(v)} items"
                break

    if len(json_str) <= _HIGHLIGHT_LIMIT:
        viewer = highlight_json_components(json_str, chips)
    else:
        viewer = html.Pre(json_str, className="json-viewer")

    return html.Div([
        html.Div([
            dbc.Badge([html.I(className=f"bi {icon} me-1"), str(code) if code else "Error"],
                      color=status_color, className="status-badge"),
            html.Span(f"{ms}ms", className="timing-label font-mono ms-2"),
            html.Span(item_count, className="timing-label") if item_count else None,
            html.Span(result.get("url", ""), className="response-url ms-auto"),
        ], className="response-meta"),
        html.Div(viewer, className="json-viewer-wrapper"),
    ], className="response-container")


def build_error_panel(message: str) -> html.Div:
    return html.Div([
        html.Div([
            html.I(className="bi bi-exclamation-triangle-fill me-2 text-danger"),
            html.Span(message, className="text-danger"),
        ], className="error-panel"),
    ], className="response-container")


def build_param_form(endpoint: Dict, prefill: Optional[Dict] = None) -> html.Div:
    params: List[Dict] = endpoint.get("params", [])
    method: str = endpoint.get("method", "GET")
    body_template: Optional[str] = endpoint.get("body")
    prefill = prefill or {}
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
            value=str(prefill[p["name"]]) if p["name"] in prefill else (p.get("default", "") or ""),
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
            html.Img(src="/assets/databricks.svg", className="brand-logo me-2"),
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
    dcc.Store(id="last-request", data=None),
    dcc.Store(id="page-state", data={"running": False}),
    dcc.Interval(id="page-ticker", interval=500, disabled=False, n_intervals=0),

    TOPBAR,
    USER_DROPDOWN,  # fixed dropdown, outside normal flow

    html.Div([
        build_sidebar(),
        html.Div([
            html.Div(WELCOME, id="endpoint-detail", className="form-panel"),
            html.Div([
                html.Div(id="fetch-status-bar", className="fetch-status-bar"),
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


# 8. Select endpoint (sidebar button click → store)
@app.callback(
    Output("selected-endpoint", "data"),
    Input({"type": "endpoint-btn", "id": ALL}, "n_clicks"),
    State({"type": "endpoint-btn", "id": ALL}, "id"),
    prevent_initial_call=True,
)
def select_endpoint(n_clicks_list, btn_ids):
    from dash import callback_context as ctx
    if not ctx.triggered:
        return no_update
    try:
        clicked_id = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])["id"]
    except (json.JSONDecodeError, KeyError):
        return no_update
    endpoint = get_endpoint_by_id(clicked_id)
    if not endpoint:
        return no_update
    return endpoint


# 8b. Sync sidebar button highlight whenever selected-endpoint changes
@app.callback(
    Output({"type": "endpoint-btn", "id": ALL}, "className"),
    Input("selected-endpoint", "data"),
    State({"type": "endpoint-btn", "id": ALL}, "id"),
    prevent_initial_call=True,
)
def sync_active_button(endpoint, btn_ids):
    active_id = (endpoint or {}).get("id", "")
    return ["endpoint-btn active" if b["id"] == active_id else "endpoint-btn" for b in btn_ids]


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
    prefill = endpoint.get("_prefill", {})
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
        build_param_form(endpoint, prefill),
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
    Output("last-request", "data"),
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
            return build_error_panel(f"Path parameter '{pp}' is required."), no_update
        path = path.replace(f"{{{pp}}}", str(val))

    method = endpoint.get("method", "GET")
    body = None
    if method == "POST" and body_text and body_text.strip():
        try:
            body = json.loads(body_text)
        except json.JSONDecodeError as e:
            return build_error_panel(f"Invalid JSON body: {e}"), no_update

    host, token = _resolve_conn(conn_config)
    if not token:
        return build_error_panel("No auth token. Configure a connection in the user menu."), no_update
    if not host:
        return build_error_panel("No workspace host. Configure a connection in the user menu."), no_update

    result = make_api_call(
        method=method, path=path, token=token, host=host,
        query_params=params if method == "GET" else None, body=body,
    )
    chips = extract_chips(endpoint.get("id", ""), result["data"]) if result["success"] else []
    last_req = {
        "path": path,
        "method": method,
        "query_params": params if method == "GET" else None,
        "body": body,
        "endpoint_id": endpoint.get("id", ""),
        "initial_data": result["data"],
        "elapsed_ms": result["elapsed_ms"],
        "status_code": result["status_code"],
        "url": result.get("url", ""),
    }
    return build_response_panel(result, chips), last_req


# 11. Auto-start pagination whenever last-request changes (fires after every execute)
@app.callback(
    Output("page-state", "data"),
    Input("last-request", "data"),
    prevent_initial_call=True,
)
def start_pagination(last_req):
    if not last_req:
        return {"running": False}
    initial_data = last_req.get("initial_data", {})
    next_token = _detect_next_page_token(initial_data)
    if not next_token:
        return {"running": False}
    list_key = _find_list_key(initial_data)
    if not list_key:
        return {"running": False}
    items = list(initial_data.get(list_key, []))
    return {
        "running": True,
        "pages_done": 0,
        "total_items": len(items),
        "items": items,
        "next_token": next_token,
        "list_key": list_key,
        "elapsed_ms": 0,
        "endpoint_id": last_req.get("endpoint_id", ""),
        "status_code": last_req.get("status_code", 200),
        "url": last_req.get("url", ""),
        "initial_data": initial_data,
        "path": last_req.get("path", ""),
        "method": last_req.get("method", "GET"),
        "query_params": last_req.get("query_params"),
        "body": last_req.get("body"),
        "error": None,
    }


# 11b. Fetch one page per interval tick (allow_duplicate — start_pagination is primary writer)
@app.callback(
    Output("page-state", "data", allow_duplicate=True),
    Input("page-ticker", "n_intervals"),
    State("page-state", "data"),
    State("conn-config", "data"),
    prevent_initial_call=True,
)
def tick_fetch(n_intervals, page_state, conn_config):
    state = page_state or {}
    if not state.get("running") or not state.get("next_token"):
        return no_update
    if state.get("pages_done", 0) >= 50:
        return {**state, "running": False, "error": "Reached 50-page limit"}

    host, token = _resolve_conn(conn_config)
    if not token or not host:
        return {**state, "running": False, "error": "No auth token"}

    t0 = time.perf_counter()
    r = make_api_call(
        state["method"], state["path"], token, host,
        query_params={**(state.get("query_params") or {}), "page_token": state["next_token"]},
        body=state.get("body"),
    )
    elapsed = int((time.perf_counter() - t0) * 1000)

    if not r["success"]:
        return {**state, "running": False, "error": r.get("error", "API error"), "elapsed_ms": state["elapsed_ms"] + elapsed}

    page_data = r["data"]
    new_items = list(state["items"]) + list(page_data.get(state["list_key"], []))
    next_token = _detect_next_page_token(page_data)
    return {
        **state,
        "running": next_token is not None,
        "pages_done": state["pages_done"] + 1,
        "total_items": len(new_items),
        "items": new_items,
        "next_token": next_token,
        "elapsed_ms": state["elapsed_ms"] + elapsed,
        "error": None,
    }


# 11c. Update status bar from page-state
@app.callback(
    Output("fetch-status-bar", "children"),
    Input("page-state", "data"),
    prevent_initial_call=True,
)
def sync_status_bar(page_state):
    state = page_state or {}
    total = state.get("total_items", 0)
    elapsed = state.get("elapsed_ms", 0)

    if not state.get("running") and not total:
        return None

    if state.get("error") == "Cancelled":
        return html.Div([
            html.I(className="bi bi-slash-circle me-2"),
            f"Cancelled — {total:,} items loaded",
        ], className="fetch-status-inner cancelled")

    if state.get("error"):
        return html.Div([
            html.I(className="bi bi-x-circle-fill me-2"),
            f"Error: {state['error']} — {total:,} items loaded",
        ], className="fetch-status-inner error")

    if state.get("running"):
        next_page = state.get("pages_done", 0) + 2   # page 1 = initial, next = pages_done+2
        return html.Div([
            html.Span(className="status-spinner me-2"),
            f"Fetching page {next_page}… {total:,} items so far",
            html.Button(
                [html.I(className="bi bi-x-lg me-1"), "Abort"],
                id="abort-btn", n_clicks=0, className="abort-btn ms-3",
            ),
        ], className="fetch-status-inner loading")

    return html.Div([
        html.I(className="bi bi-check-circle-fill me-2"),
        f"All pages loaded — {total:,} items · {elapsed}ms",
    ], className="fetch-status-inner done")


# 11c. Render final merged result when pagination completes
@app.callback(
    Output("response-container", "children", allow_duplicate=True),
    Input("page-state", "data"),
    prevent_initial_call=True,
)
def render_when_done(page_state):
    state = page_state or {}
    if state.get("running") or not state.get("items"):
        return no_update
    initial_data = state.get("initial_data", {})
    list_key = state.get("list_key")
    if not list_key:
        return no_update
    merged_data = {**initial_data, list_key: state["items"]}
    merged_data.pop("next_page_token", None)
    merged_data.pop("has_more", None)
    merged_result = {
        "status_code": state.get("status_code", 200),
        "elapsed_ms": state.get("elapsed_ms", 0),
        "data": merged_data,
        "success": True,
        "error": None,
        "url": state.get("url", ""),
    }
    chips = extract_chips(state.get("endpoint_id", ""), merged_data)
    return build_response_panel(merged_result, chips)


# 11g. Abort button — cancel in-flight pagination
@app.callback(
    Output("page-state", "data", allow_duplicate=True),
    Input("abort-btn", "n_clicks"),
    State("page-state", "data"),
    prevent_initial_call=True,
)
def abort_pagination(n_clicks, page_state):
    if not n_clicks:
        return no_update
    state = page_state or {}
    return {**state, "running": False, "error": "Cancelled"}


# 12. Inline ID link click — switch to Get endpoint, pre-fill form, execute
@app.callback(
    Output("selected-endpoint", "data", allow_duplicate=True),
    Output("response-container", "children", allow_duplicate=True),
    Input({"type": "id-link", "idx": ALL, "gid": ALL, "par": ALL, "val": ALL}, "n_clicks"),
    State("conn-config", "data"),
    prevent_initial_call=True,
)
def handle_id_link_click(n_clicks_list, conn_config):
    from dash import callback_context as ctx
    if not ctx.triggered or not any(n for n in n_clicks_list if n):
        return no_update, no_update
    try:
        comp_id = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
    except (json.JSONDecodeError, KeyError, TypeError):
        return no_update, no_update

    get_id = comp_id.get("gid", "")
    param_name = comp_id.get("par", "")
    value = comp_id.get("val", "")
    if not get_id or not param_name or value == "":
        return no_update, no_update

    endpoint = get_endpoint_by_id(get_id)
    if not endpoint:
        return no_update, no_update

    path = endpoint["path"]
    query_params: Dict[str, Any] = {}
    if param_name in endpoint.get("path_params", []):
        path = path.replace(f"{{{param_name}}}", value)
    else:
        query_params[param_name] = value

    host, token = _resolve_conn(conn_config)
    if not token:
        return no_update, build_error_panel("No auth token.")
    if not host:
        return no_update, build_error_panel("No workspace host.")

    result = make_api_call(
        method=endpoint.get("method", "GET"),
        path=path, token=token, host=host,
        query_params=query_params or None,
    )
    # Embed prefill so render_endpoint_detail pre-populates the param field
    endpoint_with_prefill = {**endpoint, "_prefill": {param_name: value}}
    return endpoint_with_prefill, build_response_panel(result)


# 13. Search filter
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
