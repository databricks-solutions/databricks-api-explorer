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

from api_catalog import API_CATALOG, ENDPOINT_MAP, TOTAL_CATEGORIES, TOTAL_ENDPOINTS, get_endpoint_by_id
from auth import IS_DATABRICKS_APP, get_current_user_info, get_host, get_local_token, make_api_call
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
            html.Span(id="user-display", className="user-chip ms-3"),
        ], className="d-flex align-items-center"),
    ], fluid=True),
    color="dark", dark=True, className="topbar",
)

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

# Static layout — both panels always in DOM for reliable callback targeting.
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="selected-endpoint"),

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
        user_el = html.Span([html.I(className="bi bi-person-circle me-1"), name], className="user-chip")
    else:
        user_el = html.Span("Not authenticated", className="text-warning small")

    return user_el, host_label


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
