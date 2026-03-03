"""
Databricks Workspace API Catalog
Complete catalog of all major Databricks workspace REST APIs.
"""
from typing import Dict, Any, List

STR = "string"
INT = "integer"
BOOL = "boolean"


def _p(name: str, desc: str, required: bool = False, type_: str = STR, default: str = "") -> Dict:
    return {"name": name, "description": desc, "required": required, "type": type_, "default": default}


API_CATALOG: Dict[str, Any] = {
    "Clusters": {
        "icon": "bi-cpu",
        "color": "#00d4ff",
        "endpoints": [
            {
                "id": "clusters-list",
                "name": "List All Clusters",
                "method": "GET",
                "path": "/api/2.0/clusters/list",
                "description": "Returns information about all pinned clusters, active clusters, up to 200 recently terminated interactive clusters, and up to 30 recently terminated job clusters.",
                "params": [],
                "body": None,
            },
            {
                "id": "clusters-get",
                "name": "Get Cluster",
                "method": "GET",
                "path": "/api/2.0/clusters/get",
                "description": "Retrieves the information for a cluster given its identifier.",
                "params": [_p("cluster_id", "The cluster to retrieve information about.", required=True)],
                "body": None,
            },
            {
                "id": "clusters-list-node-types",
                "name": "List Node Types",
                "method": "GET",
                "path": "/api/2.0/clusters/list-node-types",
                "description": "Returns a list of supported Spark node types. These node types can be used to launch a cluster.",
                "params": [],
                "body": None,
            },
            {
                "id": "clusters-spark-versions",
                "name": "List Spark Versions",
                "method": "GET",
                "path": "/api/2.0/clusters/spark-versions",
                "description": "Returns the list of available Spark versions. These versions can be used to launch a cluster.",
                "params": [],
                "body": None,
            },
            {
                "id": "clusters-events",
                "name": "Get Cluster Events",
                "method": "POST",
                "path": "/api/2.0/clusters/events",
                "description": "Retrieves a list of events about the activity of a cluster.",
                "params": [],
                "body": '{\n  "cluster_id": "<cluster-id>",\n  "limit": 20\n}',
            },
        ],
    },
    "Jobs": {
        "icon": "bi-briefcase",
        "color": "#a855f7",
        "endpoints": [
            {
                "id": "jobs-list",
                "name": "List Jobs",
                "method": "GET",
                "path": "/api/2.1/jobs/list",
                "description": "Retrieves a list of jobs. Does not include deleted jobs.",
                "params": [
                    _p("limit", "Max number of jobs to return (1–100).", default="25", type_=INT),
                    _p("offset", "Offset of the first job to return.", default="0", type_=INT),
                    _p("expand_tasks", "Include task and cluster spec info (true/false).", default="false"),
                ],
                "body": None,
            },
            {
                "id": "jobs-get",
                "name": "Get Job",
                "method": "GET",
                "path": "/api/2.1/jobs/get",
                "description": "Retrieves the details for a single job.",
                "params": [_p("job_id", "The canonical identifier of the job.", required=True, type_=INT)],
                "body": None,
            },
            {
                "id": "jobs-runs-list",
                "name": "List Job Runs",
                "method": "GET",
                "path": "/api/2.1/jobs/runs/list",
                "description": "Lists runs in descending order by start time.",
                "params": [
                    _p("job_id", "Filter runs by job ID (optional).", type_=INT),
                    _p("limit", "Max number of runs to return (1–25).", default="25", type_=INT),
                    _p("offset", "Offset of the first run.", default="0", type_=INT),
                    _p("active_only", "Return only active runs (true/false).", default="false"),
                    _p("completed_only", "Return only completed runs (true/false).", default="false"),
                ],
                "body": None,
            },
            {
                "id": "jobs-runs-get",
                "name": "Get Run",
                "method": "GET",
                "path": "/api/2.1/jobs/runs/get",
                "description": "Retrieves the metadata of a run.",
                "params": [
                    _p("run_id", "The canonical identifier of the run.", required=True, type_=INT),
                    _p("include_history", "Include iteration history (true/false).", default="false"),
                ],
                "body": None,
            },
        ],
    },
    "Workspace": {
        "icon": "bi-folder2-open",
        "color": "#f59e0b",
        "endpoints": [
            {
                "id": "workspace-list",
                "name": "List Objects",
                "method": "GET",
                "path": "/api/2.0/workspace/list",
                "description": "Lists the contents of a directory, or the object if it is not a directory.",
                "params": [_p("path", "The absolute path of the directory.", required=True, default="/")],
                "body": None,
            },
            {
                "id": "workspace-get-status",
                "name": "Get Object Status",
                "method": "GET",
                "path": "/api/2.0/workspace/get-status",
                "description": "Gets the status of an object or a directory.",
                "params": [_p("path", "The absolute path of the notebook or directory.", required=True)],
                "body": None,
            },
            {
                "id": "workspace-search",
                "name": "Search Workspace",
                "method": "GET",
                "path": "/api/2.0/workspace/search",
                "description": "Searches for workspace objects by query string.",
                "params": [_p("query", "The search query string.", required=True)],
                "body": None,
            },
        ],
    },
    "DBFS": {
        "icon": "bi-hdd-network",
        "color": "#10b981",
        "endpoints": [
            {
                "id": "dbfs-list",
                "name": "List Files",
                "method": "GET",
                "path": "/api/2.0/dbfs/list",
                "description": "Lists the contents of a directory, or details of a file. If path is a file, returns a single-element list.",
                "params": [_p("path", "The path of the file or directory.", required=True, default="/")],
                "body": None,
            },
            {
                "id": "dbfs-get-status",
                "name": "Get File Status",
                "method": "GET",
                "path": "/api/2.0/dbfs/get-status",
                "description": "Gets the file information for a file or directory on DBFS.",
                "params": [_p("path", "The path of the file or directory.", required=True)],
                "body": None,
            },
        ],
    },
    "SQL Warehouses": {
        "icon": "bi-database",
        "color": "#ec4899",
        "endpoints": [
            {
                "id": "sql-warehouses-list",
                "name": "List Warehouses",
                "method": "GET",
                "path": "/api/2.0/sql/warehouses",
                "description": "Lists all SQL warehouses that a user has manager permissions on.",
                "params": [_p("run_as_user_id", "Filter by run-as user ID.", type_=INT)],
                "body": None,
            },
            {
                "id": "sql-warehouses-get",
                "name": "Get Warehouse",
                "method": "GET",
                "path": "/api/2.0/sql/warehouses/{id}",
                "description": "Gets the information for a single SQL warehouse.",
                "params": [_p("id", "Required ID of the warehouse.", required=True)],
                "body": None,
                "path_params": ["id"],
            },
            {
                "id": "sql-queries-list",
                "name": "List Saved Queries",
                "method": "GET",
                "path": "/api/2.0/sql/queries",
                "description": "Gets a list of saved SQL queries.",
                "params": [
                    _p("page_size", "Number of queries per page.", default="25", type_=INT),
                    _p("q", "Search query string."),
                    _p("order", "Sort field (e.g., name, created_at)."),
                ],
                "body": None,
            },
        ],
    },
    "Unity Catalog": {
        "icon": "bi-layers",
        "color": "#6366f1",
        "endpoints": [
            {
                "id": "uc-catalogs-list",
                "name": "List Catalogs",
                "method": "GET",
                "path": "/api/2.1/unity-catalog/catalogs",
                "description": "Lists the available catalogs. There is no guarantee of a specific ordering of the elements in the list.",
                "params": [_p("max_results", "Maximum number of catalogs to return.", type_=INT)],
                "body": None,
            },
            {
                "id": "uc-schemas-list",
                "name": "List Schemas",
                "method": "GET",
                "path": "/api/2.1/unity-catalog/schemas",
                "description": "Lists the schemas for a catalog.",
                "params": [
                    _p("catalog_name", "Parent catalog for schemas of interest.", required=True),
                    _p("max_results", "Maximum number of schemas to return.", type_=INT),
                ],
                "body": None,
            },
            {
                "id": "uc-tables-list",
                "name": "List Tables",
                "method": "GET",
                "path": "/api/2.1/unity-catalog/tables",
                "description": "Gets an array of all tables for the current metastore under the parent catalog and schema.",
                "params": [
                    _p("catalog_name", "Name of the catalog.", required=True),
                    _p("schema_name", "Name of the schema.", required=True),
                    _p("max_results", "Maximum number of tables to return.", type_=INT),
                ],
                "body": None,
            },
            {
                "id": "uc-tables-get",
                "name": "Get Table",
                "method": "GET",
                "path": "/api/2.1/unity-catalog/tables/{full_name}",
                "description": "Gets a table from Unity Catalog using its full name (catalog.schema.table).",
                "params": [_p("full_name", "Full name of the table: catalog.schema.table", required=True)],
                "body": None,
                "path_params": ["full_name"],
            },
            {
                "id": "uc-volumes-list",
                "name": "List Volumes",
                "method": "GET",
                "path": "/api/2.1/unity-catalog/volumes",
                "description": "Lists volumes from the specified catalog and schema.",
                "params": [
                    _p("catalog_name", "The identifier of the catalog.", required=True),
                    _p("schema_name", "The identifier of the schema.", required=True),
                    _p("max_results", "Maximum number of volumes to return.", type_=INT),
                ],
                "body": None,
            },
            {
                "id": "uc-metastore-get",
                "name": "Get Current Metastore",
                "method": "GET",
                "path": "/api/2.1/unity-catalog/metastore_summary",
                "description": "Gets the summary of the metastore assigned to the workspace.",
                "params": [],
                "body": None,
            },
        ],
    },
    "MLflow": {
        "icon": "bi-graph-up",
        "color": "#0ea5e9",
        "endpoints": [
            {
                "id": "mlflow-experiments-search",
                "name": "Search Experiments",
                "method": "GET",
                "path": "/api/2.0/mlflow/experiments/search",
                "description": "Gets a list of all experiments.",
                "params": [
                    _p("max_results", "Maximum number of experiments.", default="100", type_=INT),
                    _p("filter", "A filter expression over experiment attributes and tags."),
                    _p("order_by", "List of columns for ordering (e.g., last_update_time DESC)."),
                ],
                "body": None,
            },
            {
                "id": "mlflow-experiments-get",
                "name": "Get Experiment",
                "method": "GET",
                "path": "/api/2.0/mlflow/experiments/get",
                "description": "Gets metadata for an experiment. This method works on deleted experiments.",
                "params": [_p("experiment_id", "ID of the associated experiment.", required=True)],
                "body": None,
            },
            {
                "id": "mlflow-runs-search",
                "name": "Search Runs",
                "method": "POST",
                "path": "/api/2.0/mlflow/runs/search",
                "description": "Searches for runs that satisfy expressions. Search expressions can use Metric and Param keys.",
                "params": [],
                "body": '{\n  "experiment_ids": ["<experiment-id>"],\n  "max_results": 25,\n  "order_by": ["start_time DESC"]\n}',
            },
            {
                "id": "mlflow-registered-models-search",
                "name": "Search Registered Models",
                "method": "GET",
                "path": "/api/2.0/mlflow/registered-models/search",
                "description": "Searches for registered models based on the specified filters.",
                "params": [
                    _p("max_results", "Max number of registered models.", default="100", type_=INT),
                    _p("filter", "String filter condition for models."),
                    _p("order_by", "Columns for ordering results."),
                ],
                "body": None,
            },
        ],
    },
    "Model Serving": {
        "icon": "bi-lightning",
        "color": "#f97316",
        "endpoints": [
            {
                "id": "serving-endpoints-list",
                "name": "List Endpoints",
                "method": "GET",
                "path": "/api/2.0/serving-endpoints",
                "description": "Retrieves a list of serving endpoints.",
                "params": [],
                "body": None,
            },
            {
                "id": "serving-endpoints-get",
                "name": "Get Endpoint",
                "method": "GET",
                "path": "/api/2.0/serving-endpoints/{name}",
                "description": "Retrieves the object and model serving endpoint configuration.",
                "params": [_p("name", "The name of the serving endpoint.", required=True)],
                "body": None,
                "path_params": ["name"],
            },
        ],
    },
    "Pipelines (DLT)": {
        "icon": "bi-diagram-3",
        "color": "#38bdf8",
        "endpoints": [
            {
                "id": "pipelines-list",
                "name": "List Pipelines",
                "method": "GET",
                "path": "/api/2.0/pipelines",
                "description": "Returns a list of pipelines.",
                "params": [
                    _p("max_results", "Maximum number of entries to return.", default="25", type_=INT),
                    _p("filter", "Select a subset based on the specified criteria (e.g., state = 'RUNNING')."),
                ],
                "body": None,
            },
            {
                "id": "pipelines-get",
                "name": "Get Pipeline",
                "method": "GET",
                "path": "/api/2.0/pipelines/{pipeline_id}",
                "description": "Gets a pipeline by its ID.",
                "params": [_p("pipeline_id", "The pipeline ID.", required=True)],
                "body": None,
                "path_params": ["pipeline_id"],
            },
            {
                "id": "pipelines-events",
                "name": "List Pipeline Events",
                "method": "GET",
                "path": "/api/2.0/pipelines/{pipeline_id}/events",
                "description": "Retrieves events for a pipeline, ordered by timestamp descending.",
                "params": [
                    _p("pipeline_id", "The pipeline ID.", required=True),
                    _p("max_results", "Max number of results.", default="25", type_=INT),
                ],
                "body": None,
                "path_params": ["pipeline_id"],
            },
        ],
    },
    "Secrets": {
        "icon": "bi-key",
        "color": "#84cc16",
        "endpoints": [
            {
                "id": "secrets-list-scopes",
                "name": "List Secret Scopes",
                "method": "GET",
                "path": "/api/2.0/secrets/scopes/list",
                "description": "Lists all secret scopes available in the workspace.",
                "params": [],
                "body": None,
            },
            {
                "id": "secrets-list",
                "name": "List Secrets in Scope",
                "method": "GET",
                "path": "/api/2.0/secrets/list",
                "description": "Lists the secrets stored within a given scope.",
                "params": [_p("scope", "The name of the scope whose secrets to list.", required=True)],
                "body": None,
            },
        ],
    },
    "Identity (SCIM)": {
        "icon": "bi-people",
        "color": "#14b8a6",
        "endpoints": [
            {
                "id": "scim-me",
                "name": "Get Current User",
                "method": "GET",
                "path": "/api/2.0/preview/scim/v2/Me",
                "description": "Gets the current authenticated user's profile.",
                "params": [],
                "body": None,
            },
            {
                "id": "scim-users-list",
                "name": "List Users",
                "method": "GET",
                "path": "/api/2.0/preview/scim/v2/Users",
                "description": "Retrieves a list of users in the workspace.",
                "params": [
                    _p("startIndex", "Index of the first result (1-based).", default="1", type_=INT),
                    _p("count", "Max number of results per page.", default="20", type_=INT),
                    _p("filter", 'Filter expression, e.g.: displayName co "admin"'),
                ],
                "body": None,
            },
            {
                "id": "scim-groups-list",
                "name": "List Groups",
                "method": "GET",
                "path": "/api/2.0/preview/scim/v2/Groups",
                "description": "Retrieves a list of groups in the workspace.",
                "params": [
                    _p("startIndex", "Index of the first result.", default="1", type_=INT),
                    _p("count", "Max number of results per page.", default="20", type_=INT),
                    _p("filter", "Filter expression over group attributes."),
                ],
                "body": None,
            },
            {
                "id": "scim-service-principals-list",
                "name": "List Service Principals",
                "method": "GET",
                "path": "/api/2.0/preview/scim/v2/ServicePrincipals",
                "description": "Retrieves a list of service principals.",
                "params": [
                    _p("startIndex", "Index of the first result.", default="1", type_=INT),
                    _p("count", "Max number of results.", default="20", type_=INT),
                    _p("filter", "Filter expression."),
                ],
                "body": None,
            },
        ],
    },
    "Tokens": {
        "icon": "bi-shield-lock",
        "color": "#d946ef",
        "endpoints": [
            {
                "id": "tokens-list",
                "name": "List Tokens",
                "method": "GET",
                "path": "/api/2.0/token/list",
                "description": "Lists the public token information for all tokens in the workspace (admin-only).",
                "params": [],
                "body": None,
            },
        ],
    },
    "Instance Pools": {
        "icon": "bi-stack",
        "color": "#78716c",
        "endpoints": [
            {
                "id": "instance-pools-list",
                "name": "List Instance Pools",
                "method": "GET",
                "path": "/api/2.0/instance-pools/list",
                "description": "Returns a list of instance pools.",
                "params": [],
                "body": None,
            },
        ],
    },
    "Cluster Policies": {
        "icon": "bi-file-ruled",
        "color": "#94a3b8",
        "endpoints": [
            {
                "id": "policies-list",
                "name": "List Cluster Policies",
                "method": "GET",
                "path": "/api/2.0/policies/clusters/list",
                "description": "Returns a list of policies accessible by the requestor.",
                "params": [
                    _p("sort_by", "Sort field: NAME, CREATOR, or CREATION_TIME."),
                    _p("sort_order", "Sort order: ASC or DESC."),
                ],
                "body": None,
            },
        ],
    },
    "Repos": {
        "icon": "bi-git",
        "color": "#fb7185",
        "endpoints": [
            {
                "id": "repos-list",
                "name": "List Repos",
                "method": "GET",
                "path": "/api/2.0/repos",
                "description": "Returns repos that the calling user has Manage permissions on.",
                "params": [
                    _p("path_prefix", "Filter repos with paths beginning with this prefix."),
                    _p("next_page_token", "Token for the next page of results."),
                ],
                "body": None,
            },
        ],
    },
    "Permissions": {
        "icon": "bi-shield-check",
        "color": "#fbbf24",
        "endpoints": [
            {
                "id": "permissions-clusters-get",
                "name": "Get Cluster Permissions",
                "method": "GET",
                "path": "/api/2.0/permissions/clusters/{cluster_id}",
                "description": "Gets the permissions of a cluster. Clusters can inherit permissions from their root object.",
                "params": [_p("cluster_id", "The cluster ID.", required=True)],
                "body": None,
                "path_params": ["cluster_id"],
            },
            {
                "id": "permissions-jobs-get",
                "name": "Get Job Permissions",
                "method": "GET",
                "path": "/api/2.0/permissions/jobs/{job_id}",
                "description": "Gets the permissions of a job.",
                "params": [_p("job_id", "The job ID.", required=True, type_=INT)],
                "body": None,
                "path_params": ["job_id"],
            },
            {
                "id": "permissions-warehouses-get",
                "name": "Get Warehouse Permissions",
                "method": "GET",
                "path": "/api/2.0/permissions/sql/warehouses/{warehouse_id}",
                "description": "Gets the permissions of a SQL warehouse.",
                "params": [_p("warehouse_id", "The warehouse ID.", required=True)],
                "body": None,
                "path_params": ["warehouse_id"],
            },
        ],
    },
}


# ── List → Get link map ────────────────────────────────────────────────────────
# Format: list_endpoint_id → (get_endpoint_id, list_key, id_field, param_name, label_field)
#   list_key   — top-level key in the response that holds the array of items
#   id_field   — field within each item that contains the primary identifier
#   param_name — parameter name expected by the get endpoint (None if no get endpoint)
#   label_field — optional field for a human-friendly chip label (dotted path supported)
LIST_TO_GET: Dict[str, Any] = {
    "clusters-list":              ("clusters-get",           "clusters",       "cluster_id",    "cluster_id",    "cluster_name"),
    "jobs-list":                  ("jobs-get",               "jobs",           "job_id",        "job_id",        "settings.name"),
    "jobs-runs-list":             ("jobs-runs-get",          "runs",           "run_id",        "run_id",        None),
    "sql-warehouses-list":        ("sql-warehouses-get",     "warehouses",     "id",            "id",            "name"),
    "uc-tables-list":             ("uc-tables-get",          "tables",         "full_name",     "full_name",     None),
    "mlflow-experiments-search":  ("mlflow-experiments-get", "experiments",    "experiment_id", "experiment_id", "name"),
    "serving-endpoints-list":     ("serving-endpoints-get",  "endpoints",      "name",          "name",          None),
    "pipelines-list":             ("pipelines-get",          "statuses",       "pipeline_id",   "pipeline_id",   "name"),
    "dbfs-list":                  ("dbfs-get-status",        "files",          "path",          "path",          None),
    "workspace-list":             ("workspace-get-status",   "objects",        "path",          "path",          None),
}


def _nested_get(obj: Dict, dotted_key: str):
    """Get a value from a dict using a dotted key like 'settings.name'."""
    for part in dotted_key.split("."):
        if not isinstance(obj, dict):
            return None
        obj = obj.get(part)
    return obj


def extract_chips(endpoint_id: str, data: Any) -> List[Dict]:
    """Extract clickable ID chips from a list API response."""
    mapping = LIST_TO_GET.get(endpoint_id)
    if not mapping:
        return []
    get_id, list_key, id_field, param_name, label_field = mapping
    if not get_id or not param_name:
        return []
    items = data.get(list_key, []) if isinstance(data, dict) else []
    if not isinstance(items, list):
        return []
    chips = []
    for item in items[:60]:
        value = item.get(id_field)
        if value is None:
            continue
        label = _nested_get(item, label_field) if label_field else None
        label = str(label) if label else str(value)
        if label != str(value):
            label = f"{label}"   # show name only; value accessible via title
        chips.append({
            "get_id":  get_id,
            "param":   param_name,
            "value":   str(value),
            "label":   label[:60],
            "title":   str(value),
        })
    return chips


def get_endpoint_by_id(endpoint_id: str) -> Dict[str, Any]:
    """Find an endpoint by its ID across all categories."""
    for category_name, category in API_CATALOG.items():
        for endpoint in category["endpoints"]:
            if endpoint["id"] == endpoint_id:
                return {**endpoint, "category": category_name, "category_color": category["color"]}
    return None


def build_endpoint_map() -> Dict[str, Dict]:
    """Build a flat map of all endpoints keyed by ID."""
    return {
        endpoint["id"]: {**endpoint, "category": cat_name, "category_color": cat["color"]}
        for cat_name, cat in API_CATALOG.items()
        for endpoint in cat["endpoints"]
    }


ENDPOINT_MAP = build_endpoint_map()

TOTAL_ENDPOINTS = sum(len(c["endpoints"]) for c in API_CATALOG.values())
TOTAL_CATEGORIES = len(API_CATALOG)
