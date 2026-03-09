# Databricks API Explorer

An ultra-modern, interactive REST API explorer for Databricks workspaces. Built as a Databricks App with dual-mode authentication — runs locally via Databricks CLI SSO and in production as a Databricks App using On-Behalf-Of (OBO) authentication.

---

## Screenshot

![Databricks API Explorer](assets/screenshot.png)

---

## Features

### API Coverage

- **15 API categories** with **45+ endpoints** across the full Databricks REST API surface:

| Category | Endpoints |
|---|---|
| Clusters | List, Get, Node Types, Spark Versions, Events |
| Jobs | List Jobs, Get Job, List Runs, Get Run |
| Workspace | List Objects, Get Status, Search |
| DBFS | List Files, Get File Status |
| SQL Warehouses | List, Get, List Saved Queries |
| Unity Catalog | List Catalogs, Schemas, Tables, Volumes, Get Metastore |
| MLflow | Search Experiments, Get Experiment, Search Runs, Registered Models |
| Model Serving | List Endpoints, Get Endpoint |
| Pipelines (DLT) | List, Get, List Events |
| Secrets | List Scopes, List Secrets |
| Identity (SCIM) | Current User, List Users, List Groups, List Service Principals |
| Tokens | List Tokens |
| Instance Pools | List Instance Pools |
| Cluster Policies | List Cluster Policies |
| Repos | List Repos |
| Permissions | Get Cluster, Job, and Warehouse Permissions |

### Authentication

- **Local mode** — authenticates via the Databricks CLI (`~/.databrickscfg`). Supports all CLI auth flows: OAuth/SSO (browser-based), PAT, Azure Service Principal, Azure Managed Identity, OAuth M2M.
- **Databricks App mode** — auto-detected at runtime. Uses On-Behalf-Of (OBO) authentication: the user's access token is forwarded via the `x-forwarded-access-token` HTTP header, so every API call runs as the logged-in user. No token configuration required.
- **Custom URL / PAT** — optionally specify any workspace URL and Personal Access Token directly in the UI, bypassing the CLI entirely.

### Connection Management

- **User identity panel** — click the username chip in the top bar to open a slide-down panel showing:
  - Display name, username, active status
  - Auth type (OBO, OAuth/SSO, PAT, Azure SP, etc.)
  - Workspace host
  - User ID and primary email
  - Group memberships (up to 20, with overflow count)
- **CLI profile switcher** — all profiles from `~/.databrickscfg` are listed and refreshed on every panel open. Switch profiles without restarting the app.
- **Re-authenticate** — triggers `databricks auth login` for SSO re-auth directly from the UI.
- **Live connection validation** — the Connect button tests the connection before saving it to state.

### Request Builder

- **Parameter forms** — each endpoint renders a type-aware form with required/optional badges and inline descriptions
- **Path parameter interpolation** — path parameters (e.g. `{cluster_id}`) are extracted from the URL and shown as dedicated fields
- **JSON body editor** — POST endpoints show a pre-populated JSON textarea with the correct request schema
- **Real-time search** — filter endpoints across all categories by name, path, method, or category

### Response Viewer

- **Syntax-highlighted JSON** — token-level syntax coloring using Dash `html.Span` components (no `dangerousHTML` injection)
- **Response metadata bar** — HTTP status code (color-coded), latency in ms, item count for list responses, full request URL
- **Large response handling** — responses over 50 000 characters are truncated with a clear notice
- **Side-by-side layout** — fixed 360 px parameter panel on the left, full-height response panel on the right

### UI & UX

- **Glassmorphism dark theme** — custom CSS with CSS variables, neon accent colors, backdrop-filter blur effects
- **CYBORG Bootstrap theme** via `dash-bootstrap-components`
- **Mode badge** in the top bar shows whether running as `Local Mode` or `Databricks App`
- **Workspace host display** in the top bar
- **Auto-incrementing build version** — `version.py` bumps a counter on every app start, displayed as `v<N>` in the topbar
- **Accordion sidebar** with category icons, per-category endpoint counts, and method color badges (GET/POST/PUT/DELETE/PATCH)
- **Active endpoint highlighting** — selected endpoint button is highlighted in the sidebar

---

## Architecture

![Architecture Diagram](assets/Architecture1.png)

```
┌─────────────────────────────────────────────────────────┐
│                      Browser / User                     │
└────────────────────────────┬────────────────────────────┘
                             │ HTTP
┌────────────────────────────▼────────────────────────────┐
│                    Dash / Flask (app.py)                 │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │   TOPBAR    │  │   SIDEBAR    │  │  MAIN CONTENT │  │
│  │  user chip  │  │  accordion   │  │               │  │
│  │  host label │  │  search      │  │  ┌──────────┐ │  │
│  │  mode badge │  │  endpoints   │  │  │  form    │ │  │
│  └──────┬──────┘  └──────┬───────┘  │  │  panel   │ │  │
│         │                │          │  └──────────┘ │  │
│  ┌──────▼──────┐         │          │  ┌──────────┐ │  │
│  │ USER        │         │          │  │ response │ │  │
│  │ DROPDOWN    │         │          │  │ panel    │ │  │
│  │ (fixed pos) │         │          │  └──────────┘ │  │
│  └─────────────┘         │          └───────────────┘  │
│                           │                             │
│  ┌────────────────────────▼────────────────────────┐   │
│  │              dcc.Store (conn-config)             │   │
│  │   {"mode": "profile"|"custom",                  │   │
│  │    "profile": "<name>" | "host": "...",          │   │
│  │    "token": "..."}                               │   │
│  └────────────────────────┬────────────────────────┘   │
└───────────────────────────│─────────────────────────────┘
                            │
         ┌──────────────────▼──────────────────┐
         │             auth.py                 │
         │                                     │
         │  _resolve_conn()                    │
         │    ├─ IS_DATABRICKS_APP?             │
         │    │   └─ host from DATABRICKS_HOST  │
         │    │      token from x-forwarded-   │
         │    │      access-token header        │
         │    └─ local mode                    │
         │        ├─ profile → SDK Config()    │
         │        └─ custom → host + PAT        │
         │                                     │
         │  make_api_call()                    │
         │    └─ requests.request()            │
         └──────────────────┬──────────────────┘
                            │
         ┌──────────────────▼──────────────────┐
         │        Databricks REST API          │
         │        (workspace host)             │
         └─────────────────────────────────────┘
```

### Key Components

| File | Responsibility |
|---|---|
| `app.py` | Dash app, layout, all callbacks |
| `auth.py` | Auth resolution, profile discovery, `make_api_call()` |
| `api_catalog.py` | All endpoint definitions (15 categories, 45+ endpoints) |
| `version.py` | Auto-incrementing build version counter |
| `assets/style.css` | Full dark glassmorphism CSS theme |
| `app.yaml` | Databricks Apps runtime config (command + env) |
| `databricks.yml` | Asset Bundle config for DABs deployment |
| `resources/api_explorer.app.yml` | DABs app resource definition |

### Auth Flow

```
                ┌─────────────────────────────────┐
                │         App Startup              │
                │  IS_DATABRICKS_APP =             │
                │  bool(DATABRICKS_CLIENT_SECRET)  │
                └──────────┬──────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           │ False (local)                 │ True (Databricks App)
           ▼                               ▼
  conn-config store               x-forwarded-access-token
  (profile | custom)              header from Databricks
           │                      platform (OBO)
           ▼                               │
  SDK Config(profile=...)                  │
  or custom host + PAT                     │
           │                               │
           └───────────────┬───────────────┘
                           ▼
                  make_api_call(method, path,
                                token, host)
```

### Callback Graph

```
url / conn-config ──► init_on_load ──► user-display, host-display
user-btn ──────────► toggle_dropdown ──► user-dropdown (open/close)
                                      ► popup-* (identity)
                                      ► profile-select options (refreshed)
conn-mode-radio ───► toggle_conn_mode ──► profile-section / custom-section
profile-select ────► show_profile_hint ──► profile-auth-type hint
apply-conn-btn ────► apply_connection ──► conn-config store
reauth-btn ────────► reauth ──► reauth-status
endpoint-btn[ALL] ─► select_endpoint ──► selected-endpoint store
selected-endpoint ─► render_endpoint_detail ──► endpoint-detail, param form
execute-btn ───────► execute_api_call ──► response-container
search-input ──────► filter_endpoints ──► endpoint-btn[ALL] styles
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Framework** | [Dash 2.x](https://dash.plotly.com/) (Plotly) |
| **UI Components** | [dash-bootstrap-components](https://dash-bootstrap-components.opensource.faculty.ai/) — CYBORG theme |
| **Icons** | Bootstrap Icons (via CDN) |
| **HTTP Client** | [requests](https://requests.readthedocs.io/) |
| **Databricks SDK** | [databricks-sdk](https://github.com/databricks/databricks-sdk-py) — profile-based auth |
| **Web Server** | Flask (embedded in Dash) |
| **Styling** | Custom CSS — glassmorphism dark theme with CSS variables |
| **Deployment** | [Databricks Asset Bundles (DABs)](https://docs.databricks.com/dev-tools/bundles/) |
| **Auth (local)** | Databricks CLI (`~/.databrickscfg`) — OAuth/SSO, PAT, Azure SP |
| **Auth (app)** | OBO via `x-forwarded-access-token` header |
| **Runtime** | Python 3.11+, Ubuntu 22.04 (on Databricks Apps) |

---

## Local Development

### Prerequisites

- Python 3.11+
- [Databricks CLI](https://docs.databricks.com/dev-tools/cli/index.html) configured with at least one profile
- `pip install -r requirements.txt`

### Run

```bash
python app.py
```

Open [http://localhost:8050](http://localhost:8050).

The app auto-detects local mode (no `DATABRICKS_CLIENT_SECRET` env var) and uses the first CLI profile from `~/.databrickscfg` by default.

---

## Deployment to Databricks Apps

### Deploy via Asset Bundle (recommended)

```bash
# Deploy to dev target (uses guido-demo-azure profile)
databricks bundle deploy

# Start the app
databricks bundle run api_explorer
```

### Deploy via CLI

```bash
databricks apps deploy databricks-api-explorer \
  --source-code-path . \
  --profile guido-demo-azure
```

### View Logs

```bash
databricks apps logs databricks-api-explorer --profile guido-demo-azure
```

---

## Project Structure

```
DatabricksAPIexplorer/
├── app.py                        # Main Dash app + all callbacks
├── auth.py                       # Auth resolution + API call helper
├── api_catalog.py                # Endpoint catalog (15 categories)
├── version.py                    # Auto-incrementing build version
├── version.txt                   # Current build number (auto-updated)
├── requirements.txt              # Python dependencies
├── app.yaml                      # Databricks Apps runtime config
├── databricks.yml                # Asset Bundle main config
├── resources/
│   └── api_explorer.app.yml      # DABs app resource definition
└── assets/
    ├── style.css                 # Dark glassmorphism CSS theme
    └── screenshot.png            # App screenshot
```
