# Databricks API Explorer

An interactive REST API explorer for Databricks — covering both **Workspace** and **Account-level** APIs. Built as a Databricks App with dual-mode authentication: runs locally via Databricks CLI SSO and in production as a Databricks App using On-Behalf-Of (OBO) authentication.

---

## Screenshot

![Databricks API Explorer](assets/DatabricksAPIexplorer%20Screenshot%200.3.816%20large.png)

---

## Features

### API Coverage

- **39 API categories** with **189 endpoints** across both Workspace and Account REST API surfaces
- **Scope switcher** in the sidebar toggles between Workspace and Account API views

#### Workspace APIs (23 categories, 158 endpoints)

| Category | Endpoints |
|---|---|
| Clusters | List, Get, Node Types, Spark Versions, Events |
| Lakeflow | Jobs (list/get/create/update/run/repair), Runs, Pipelines (DLT), Policy Compliance for Jobs |
| Workspace | List Objects, Get Status |
| DBFS | List, Get Status, Read, Create / Add Block / Close, Put, Mkdirs, Move, Delete |
| Files (UC Volumes) | List Directory Contents, Create / Delete Directory, Get Directory Metadata, Download / Upload / Delete File, Get File Metadata |
| SQL Warehouses | List, Get, List Saved Queries |
| Unity Catalog | List Catalogs, Schemas, Tables, Volumes, Get Table, Get Metastore |
| MLflow | Search Experiments, Get Experiment, Search Runs, Registered Models |
| Model Serving | List Endpoints, Get Endpoint |
| Secrets | List Scopes, List Secrets |
| Identity (SCIM) | Current User, List Users, List Groups, List Service Principals |
| Tokens | List Tokens |
| Instance Pools | List, Get, Create, Edit, Delete, Permissions |
| Instance Profiles | List, Add, Edit, Remove |
| Cluster Policies | List, Policy Compliance for Clusters, Policy Families |
| Libraries | All Cluster Statuses, Cluster Status, Install, Uninstall |
| Repos | List Repos |
| Git Credentials | List, Get, Create, Update, Delete |
| Global Init Scripts | List, Get, Create, Update, Delete |
| Permissions | Get Cluster, Job, and Warehouse Permissions |
| Data Quality Monitoring | Create / Get / Update / Delete Monitor, Run / List / Get / Cancel Refresh, Regenerate Dashboard |
| Lakebase Provisioned | Instances, Catalogs, Database / Table / Pipeline / Synced operations |
| Lakebase Autoscaling | Projects, Branches, Endpoints, Scale-to-zero controls |

#### Account APIs (16 categories, 31 endpoints, plus Command Execution legacy 1.2 API)

| Category | Endpoints |
|---|---|
| Account Users | List Users, Get User |
| Account Groups | List Groups, Get Group |
| Service Principals | List Service Principals, Get Service Principal |
| Workspaces | List Workspaces, Get Workspace |
| Credentials | List Credential Configs, Get Credential Config |
| Storage | List Storage Configs, Get Storage Config |
| Networks | List Network Configs, Get Network Config |
| Private Access | List Private Access Settings, Get Private Access Settings |
| VPC Endpoints | List VPC Endpoints, Get VPC Endpoint |
| Encryption Keys | List Encryption Key Configs, Get Encryption Key Config |
| Log Delivery | List Log Delivery Configs, Get Log Delivery Config |
| Budgets | List Budgets, Get Budget |
| Usage Download | Download Usage (CSV) |
| Account Metastores | List Metastores, Get Metastore, List Metastore Assignments |
| Account Access Control | Get Rule Set |
| Account Settings | Get Personal Compute Setting, List IP Access Lists |

### Authentication

- **Local mode** — authenticates via the Databricks CLI (`~/.databrickscfg`). Supports all CLI auth flows: OAuth/SSO (browser-based), PAT, Azure Service Principal, Azure Managed Identity, OAuth M2M.
- **Databricks App mode** — auto-detected at runtime. Uses On-Behalf-Of (OBO) authentication: the user's access token is forwarded via the `x-forwarded-access-token` HTTP header, so every API call runs as the logged-in user. No token configuration required.
- **Custom URL / PAT** — optionally specify any workspace URL and Personal Access Token directly in the UI, bypassing the CLI entirely.
- **Account API auth** — account-scope endpoints automatically derive the accounts console URL from the workspace host and obtain an account-level token.

### Connection Management

- **User identity panel** — click the username chip in the top bar to open a slide-down panel showing:
  - Display name, username, active status
  - Auth type (OBO, OAuth/SSO, PAT, Azure SP, etc.)
  - Workspace host and account ID
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
- **Configurable timeout** — per-request timeout control with a spinner input next to the Execute button (defaults vary by endpoint, e.g. 120 s for Usage Download)
- **Auto-fill account ID** — account-scope endpoints automatically populate the `account_id` field from the current CLI profile

### Response Viewer

- **Collapsible JSON tree** — interactive tree viewer rendered in an iframe with expand/collapse toggles, inline syntax highlighting, and compact previews for collapsed nodes
- **Inline ID links** — list API responses render clickable ID chips on matching fields; clicking one fires the corresponding Get API and pre-fills the parameter form
- **Side panel with chip list** — list responses show a scrollable side panel of result chips with labels, allowing quick drill-down into individual items
- **Action buttons on chips** — some list endpoints expose secondary actions (e.g. "List workspace assignments" on metastores) directly on each chip
- **Response metadata bar** — HTTP status code (color-coded), latency in ms, item count for list responses, full request URL
- **CSV viewer** — endpoints that return CSV data (e.g. Usage Download) are rendered as a scrollable HTML table
- **curl command** — every executed request generates a ready-to-copy `curl` command displayed below the Execute button, with a one-click copy button

### Files & DBFS Browsing

- **Volume drill-down** — in **Unity Catalog → List Volumes**, the volume name is a clickable link that opens **Files → List Directory Contents** with `directory_path` pre-filled to `/Volumes/<catalog>/<schema>/<volume>`
- **Recursive directory navigation** — in a directory listing, sub-directories (`is_directory: true`) are clickable and recurse into the same endpoint with the new path; files become a single click that downloads them
- **Per-file action button** — each file row has a secondary action button that opens **Get File Metadata** for that file
- **Pretty-print viewer** — on the **Download File** response, a *Pretty-print* button parses content based on the file extension and renders it inline:
  - `.json` → indented JSON
  - `.csv` / `.tsv` → HTML table (first 1,000 rows)
  - `.parquet` → table via `pyarrow.parquet` (first 1,000 rows)
  - other text → raw text preview (first 200 KB)
- **Save-to-disk** — a *Download* button on the same response streams the raw bytes to the browser via `dcc.Download`, using the filename from the path. Re-fetches with auth so binary content (e.g. Parquet) isn't lossy-decoded
- **Browser back/forward** — drilling into directories pushes browser history; the back button replays the original click and re-fetches the previous directory listing rather than showing a stale cached response

### SQL Statement Execution

- **Dedicated SQL panel** — a standalone SQL execution interface accessible from the sidebar, separate from the REST API explorer
- **Warehouse selector** — auto-discovers available SQL warehouses from the connected workspace, defaulting to a running warehouse
- **Inline results** — query results are rendered directly in the response viewer with the same collapsible JSON tree
- **Optional catalog/schema context** — set default catalog and schema for unqualified table names
- **Row limit control** — configurable row limit (default 1,000) to cap result size
- **curl command** — generates a ready-to-copy `curl` command for the executed SQL statement

### Pagination

- **Automatic pagination** — when a response contains a `next_page_token`, the app automatically fetches subsequent pages and merges them into a single result
- **"Load All" button** — for APIs with `has_more`-style pagination, a "Load All" button in the side panel fetches all remaining pages in a background thread with live progress updates
- **Abort controls** — both automatic pagination and Load All can be cancelled mid-flight; Load All auto-cancels when switching to a different endpoint

### Resizable Side Panel

- **Drag-to-resize** — the side panel has a left-edge resize handle; drag to adjust width between 20% and 80% of the viewport
- **Persistent width** — panel width is saved to `localStorage` and restored across page reloads

### UI & UX

- **Glassmorphism dark theme** — custom CSS with CSS variables, neon accent colors, backdrop-filter blur effects
- **CYBORG Bootstrap theme** via `dash-bootstrap-components`
- **Scope switcher** — toggle between Workspace and Account API catalogs in the sidebar
- **Mode badge** in the top bar shows whether running as `Local Mode` or `Databricks App`
- **Workspace host display** in the top bar with a clickable link to the workspace
- **Auto-incrementing build version** — `version.py` bumps a counter on every app start, displayed as `v<N>` in the topbar
- **Accordion sidebar** with category icons, per-category endpoint counts, and method color badges (GET/POST/PUT/DELETE/PATCH)
- **Active endpoint highlighting** — selected endpoint button is highlighted in the sidebar
- **Debug bar patches** — MutationObserver removes the Plotly Cloud button and injects workspace URL links into the Dash debug bar

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
│  │  user chip  │  │  scope switch│  │               │  │
│  │  host label │  │  accordion   │  │  ┌──────────┐ │  │
│  │  mode badge │  │  search      │  │  │  form    │ │  │
│  └──────┬──────┘  │  endpoints   │  │  │  panel   │ │  │
│         │         └──────┬───────┘  │  └──────────┘ │  │
│  ┌──────▼──────┐         │          │  ┌──────────┐ │  │
│  │ USER        │         │          │  │ response │ │  │
│  │ DROPDOWN    │         │          │  │ tree +   │ │  │
│  │ (fixed pos) │         │          │  │ side     │ │  │
│  └─────────────┘         │          │  │ panel    │ │  │
│                           │          │  └──────────┘ │  │
│  ┌────────────────────────▼──────────┴───────────┐   │
│  │              dcc.Store (conn-config)            │   │
│  │   {"mode": "profile"|"custom",                 │   │
│  │    "profile": "<name>" | "host": "...",         │   │
│  │    "token": "..."}                              │   │
│  └────────────────────────┬──────────────────────┘   │
└───────────────────────────│───────────────────────────┘
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
         └──────┬───────────────────┬──────────┘
                │                   │
 ┌──────────────▼───────┐ ┌────────▼──────────────────┐
 │  Databricks REST API │ │  Databricks Accounts API  │
 │  (workspace host)    │ │  (accounts console host)  │
 └──────────────────────┘ └───────────────────────────┘
```

### Key Components

| File | Responsibility |
|---|---|
| `app.py` | Dash app, layout, all callbacks (19+ callbacks) |
| `auth.py` | Auth resolution, profile discovery, account token exchange, `make_api_call()` |
| `api_catalog.py` | Endpoint catalog (39 categories, 189 endpoints), chip extraction, list-to-get linking |
| `version.py` | Auto-incrementing build version counter |
| `assets/style.css` | Full dark glassmorphism CSS theme |
| `assets/devtools_patch.js` | Debug bar patches + resizable side panel |
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
                           │
              ┌────────────┴────────────┐
              │ scope == "workspace"    │ scope == "account"
              ▼                         ▼
     workspace host            _accounts_host() derives
                               accounts console URL
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
scope-switch ──────► switch_scope ──► sidebar categories (workspace/account)
endpoint-btn[ALL] ─► select_endpoint ──► selected-endpoint store
selected-endpoint ─► sync_active_button ──► endpoint-btn[ALL] className
selected-endpoint ─► render_endpoint_detail ──► endpoint-detail, param form
execute-btn ───────► execute_api_call ──► response-container, curl command
                   ► start_pagination ──► auto-fetch next pages
search-input ──────► filter_endpoints ──► endpoint-btn[ALL] styles
id-link-btn ───────► handle_id_link_click ──► selected-endpoint, response
load-all-btn ──────► start_load_all ──► background thread + ticker
last-req ──────────► update_curl_display ──► curl-text, curl-display
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Framework** | [Dash 4.x](https://dash.plotly.com/) (Plotly) |
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
# Deploy to dev target (uses your configured profile)
databricks bundle deploy

# Start the app
databricks bundle run api_explorer
```

### Deploy via CLI

```bash
databricks apps deploy databricks-api-explorer \
  --source-code-path . \
  --profile <your-profile>
```

### View Logs

```bash
databricks apps logs databricks-api-explorer --profile <your-profile>
```

---

## Project Structure

```
DatabricksAPIexplorer/
├── app.py                        # Main Dash app + all callbacks
├── auth.py                       # Auth resolution + API call helper
├── api_catalog.py                # Endpoint catalog (39 categories, 189 endpoints)
├── version.py                    # Auto-incrementing build version
├── version.txt                   # Current build number (auto-updated)
├── requirements.txt              # Python dependencies
├── app.yaml                      # Databricks Apps runtime config
├── databricks.yml                # Asset Bundle main config
├── resources/
│   └── api_explorer.app.yml      # DABs app resource definition
└── assets/
    ├── style.css                 # Dark glassmorphism CSS theme
    ├── devtools_patch.js         # Debug bar patches + resizable side panel
    └── DatabricksAPIexplorer Screenshot 0.3.816 large.png  # App screenshot
```

DISCLAIMER: This application and accompanying source code are provided
solely for demonstration and proof-of-concept purposes. They are not
intended for production use. Databricks, Inc. makes no warranties,
express or implied, regarding the functionality, completeness,
reliability, or suitability of this software. Databricks assumes no
liability for any damages, data loss, or other issues arising from the
use of this demonstration material. Any deployment to production
environments is the sole responsibility of the implementing party.
