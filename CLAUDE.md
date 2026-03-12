# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run locally (debug mode, port 8050)
python app.py

# Deploy to Databricks Apps via Asset Bundle (dev target, guido-demo-azure profile)
databricks bundle deploy
databricks bundle run api_explorer

# Deploy directly via CLI
databricks apps deploy databricks-api-explorer --source-code-path . --profile guido-demo-azure

# View production logs
databricks apps logs databricks-api-explorer --profile guido-demo-azure
```

There are no tests, linters, or build steps.

## Architecture

Three Python files do all the work. There is no database, no state beyond in-memory Dash stores, and no background tasks.

### `app.py` — Dash layout + all callbacks
The entire UI and all server-side logic live here. Key sections:
- `highlight_json_components()` — pure-Python JSON tokenizer that builds `html.Span`/`html.Button` trees (no `dangerouslySetInnerHTML`). Accepts optional `id_link_data` (chip list from `extract_chips`) to render ID field values as inline clickable `html.Button` elements.
- `build_response_panel()` — assembles the response view; passes chips to the JSON renderer.
- `build_param_form(endpoint, prefill=None)` — generates type-aware parameter inputs; `prefill` dict overrides the default value for named params (used when navigating via inline ID link).
- Callbacks are numbered 1–12 (with 8b inserted between 8 and 9).

### `api_catalog.py` — endpoint definitions + chip extraction
- Two catalogs: `API_CATALOG` (workspace APIs) and `ACCOUNT_API_CATALOG` (account-level APIs targeting `accounts.cloud.databricks.com`).
- Each endpoint has `id`, `method`, `path`, `params`, optional `path_params`, optional `body`. Account endpoints also carry `scope: "account"` when looked up via `get_endpoint_by_id`/`ENDPOINT_MAP`.
- `LIST_TO_GET` / `ACCOUNT_LIST_TO_GET` dicts: map list-endpoint IDs to `(get_endpoint_id, list_key, id_field, param_name, label_field)`. `list_key=None` means the response is a bare JSON array.
- `extract_chips()` — reads both link maps, walks the API response, returns chip dicts. The `id_field` key is what the JSON tree viewer uses to match keys by name.
- Adding a new endpoint: add it to the appropriate `*_CATALOG` and, if it's a list with a corresponding get, add it to the matching `*_LIST_TO_GET`.
- A scope switcher in the sidebar toggles between Workspace and Account views. Account API calls route through `_accounts_host()` which derives the accounts console URL from the workspace host.

### `auth.py` — dual-mode authentication
- `IS_DATABRICKS_APP = bool(os.getenv("DATABRICKS_CLIENT_SECRET"))` — this flag switches the entire app between local and Databricks App mode at startup.
- `_resolve_conn(conn_config)` in `app.py` is the central dispatcher: when `IS_DATABRICKS_APP` is true it reads `DATABRICKS_HOST` env var and the `x-forwarded-access-token` request header; otherwise it calls `resolve_local_connection(conn_config)`.
- `resolve_local_connection()` uses `databricks.sdk.core.Config(profile=...)` to resolve host + token for profile mode, or reads host/token directly for custom mode.
- `make_api_call()` returns a consistent dict: `{status_code, elapsed_ms, data, success, error, url}`.

## Key Patterns

**`conn-config` store** is the single source of truth for local connection state. Shape: `{"mode": "profile"|"custom", "profile": "<name>"}` or `{"mode": "custom", "host": "...", "token": "..."}`. Callbacks that make API calls read it as a State and pass it to `_resolve_conn()`.

**`version.txt` auto-increments** on every `import app` (via `version.py`). Don't be surprised when it bumps during development; it's intentional.

**Dash 4.0.0 `allow_duplicate` constraint**: `allow_duplicate=True` only works when the target output is the *primary* (first) output of another callback. Never add `allow_duplicate=True` to a secondary output — this causes a `KeyError: "Callback function not found for output '...'"` at runtime. `handle_id_link_click` uses `allow_duplicate=True` on `selected-endpoint.data` (first output of `select_endpoint`) and `response-container.children` (first output of `execute_api_call`), both safe.

**Sidebar button highlighting is decoupled from `select_endpoint`**: `select_endpoint` (callback 8) only writes `selected-endpoint.data`. A separate `sync_active_button` callback (8b) watches `selected-endpoint` and derives `endpoint-btn.className` from it. This means any callback that updates `selected-endpoint` with `allow_duplicate=True` automatically gets correct sidebar highlighting for free, without needing `allow_duplicate` on the pattern-matching className output.

**Inline ID links + `_prefill` flow**: When a list API succeeds, `extract_chips()` builds a chip list. `highlight_json_components()` renders matching field values as `html.Button` elements with component IDs embedding `gid`, `par`, `val`. Clicking one fires `handle_id_link_click`, which: (1) calls the Get API and updates `response-container`; (2) writes `{...endpoint, "_prefill": {param_name: value}}` to `selected-endpoint`. That store change triggers both `sync_active_button` (highlights the Get button) and `render_endpoint_detail` (reads `_prefill`, calls `build_param_form(endpoint, prefill)` with the ID pre-filled).

**Default CLI profile** is resolved at startup in `auth.py` as the first profile found in `~/.databrickscfg` (falls back to `"DEFAULT"` if the file is absent or empty). No hardcoding needed.

## Assets

- `assets/style.css` — all styling; uses CSS custom properties defined in `:root`. JSON syntax colors: `.jk` (keys, blue), `.jv` (strings, green), `.jn` (numbers, amber), `.jb` (booleans, purple), `.jbn` (null, muted).
- `assets/devtools_patch.js` — MutationObserver that removes the Plotly Cloud button from the Dash debug bar and injects workspace URL links. Watches `#host-display` for connection changes.
