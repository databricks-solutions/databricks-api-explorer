"""Databricks API Catalog -- Workspace and Account endpoints.

Declarative registry of every Databricks REST API endpoint exposed by
the explorer UI, organised by scope and category.

Two top-level catalogs:

* :data:`API_CATALOG` -- **Workspace** APIs (target: workspace URL).
* :data:`ACCOUNT_API_CATALOG` -- **Account** APIs (target:
  ``accounts.cloud.databricks.com`` or ``accounts.azuredatabricks.net``).

Each catalog is a nested dict of categories → endpoint definitions.
:data:`LIST_TO_GET` / :data:`ACCOUNT_LIST_TO_GET` drive inline
navigation links from list responses to their corresponding *get*
endpoints.

Attributes:
    API_CATALOG: Workspace endpoint registry keyed by category name.
    ACCOUNT_API_CATALOG: Account endpoint registry keyed by category.
    LIST_TO_GET: Workspace list→get link map.
    ACCOUNT_LIST_TO_GET: Account list→get link map.
    ENDPOINT_MAP: Flat map of *all* endpoints (both scopes) keyed by ID.
    TOTAL_ENDPOINTS: Total number of workspace endpoints.
    TOTAL_CATEGORIES: Total number of workspace categories.
    TOTAL_ACCOUNT_ENDPOINTS: Total number of account endpoints.
    TOTAL_ACCOUNT_CATEGORIES: Total number of account categories.
"""

from typing import Any, Dict, List, Optional

STR: str = "string"
INT: str = "integer"
BOOL: str = "boolean"


def _p(
    name: str,
    desc: str,
    required: bool = False,
    type_: str = STR,
    default: str = "",
) -> Dict[str, Any]:
    """Build a parameter definition dict for an endpoint.

    Args:
        name: Parameter name as expected by the Databricks REST API.
        desc: Human-readable description shown in the UI.
        required: Whether the parameter is mandatory.
        type_: Data type hint (``"string"``, ``"integer"``, or
            ``"boolean"``).
        default: Default value pre-filled in the input field.

    Returns:
        A parameter dict consumable by :func:`app.build_param_form`.
    """
    return {
        "name": name,
        "description": desc,
        "required": required,
        "type": type_,
        "default": default,
    }


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
# Format: list_endpoint_id → (get_endpoint_id, list_key, id_field, param_name, label_field[, extra_params[, actions]])
#   list_key      — top-level key in the response that holds the array of items
#   id_field      — field within each item that contains the primary identifier
#   param_name    — parameter name expected by the get endpoint (None if no get endpoint)
#   label_field   — optional field for a human-friendly chip label (dotted path supported)
#   extra_params  — optional dict {target_param: source_item_field} for additional params
#   actions       — optional list of (target_endpoint_id, icon_class, tooltip, {target_param: source_field})
LIST_TO_GET: Dict[str, Any] = {
    "clusters-list":              ("clusters-get",           "clusters",       "cluster_id",    "cluster_id",    "cluster_name", None, [
                                      ("permissions-clusters-get", "bi-shield-check", "Get Cluster Permissions", {"cluster_id": "cluster_id"}),
                                      ("clusters-events", "bi-journal-text", "Get Cluster Events", {"cluster_id": "cluster_id"}),
                                  ]),
    "jobs-list":                  ("jobs-get",               "jobs",           "job_id",        "job_id",        "settings.name", None, [
                                      ("permissions-jobs-get", "bi-shield-check", "Get Job Permissions", {"job_id": "job_id"}),
                                  ]),
    "jobs-runs-list":             ("jobs-runs-get",          "runs",           "run_id",        "run_id",        None),
    "sql-warehouses-list":        ("sql-warehouses-get",     "warehouses",     "id",            "id",            "name", None, [
                                      ("permissions-warehouses-get", "bi-shield-check", "Get Warehouse Permissions", {"warehouse_id": "id"}),
                                  ]),
    "uc-catalogs-list":           ("uc-schemas-list",        "catalogs",       "name",          "catalog_name",  None),
    "uc-schemas-list":            ("uc-tables-list",         "schemas",        "name",          "schema_name",   None, {"catalog_name": "catalog_name"}, [
                                      ("uc-volumes-list", "bi-archive", "List Volumes", {"catalog_name": "catalog_name", "schema_name": "name"}),
                                  ]),
    "uc-tables-list":             ("uc-tables-get",          "tables",         "full_name",     "full_name",     "name"),
    "mlflow-experiments-search":  ("mlflow-experiments-get", "experiments",    "experiment_id", "experiment_id", "name"),
    "serving-endpoints-list":     ("serving-endpoints-get",  "endpoints",      "name",          "name",          None),
    "pipelines-list":             ("pipelines-get",          "statuses",       "pipeline_id",   "pipeline_id",   "name"),
    "secrets-list-scopes":        ("secrets-list",           "scopes",         "name",          "scope",         None),
    "dbfs-list":                  ("dbfs-get-status",        "files",          "path",          "path",          None),
    "workspace-list":             ("workspace-get-status",   "objects",        "path",          "path",          None),
}


# ── Account-level API Catalog ─────────────────────────────────────────────────
# These target the accounts console (accounts.cloud.databricks.com) rather
# than an individual workspace.  Every path includes {account_id}.


def _usage_start_month() -> str:
    """Return YYYY-MM for three months ago (default start for Usage Download)."""
    from datetime import date, timedelta  # noqa: PLC0415
    d = date.today().replace(day=1) - timedelta(days=90)
    return d.strftime("%Y-%m")


def _usage_end_month() -> str:
    """Return YYYY-MM for the current month (default end for Usage Download)."""
    from datetime import date  # noqa: PLC0415
    return date.today().strftime("%Y-%m")


ACCOUNT_API_CATALOG: Dict[str, Any] = {
    "Account Users": {
        "icon": "bi-people",
        "color": "#14b8a6",
        "endpoints": [
            {
                "id": "acct-users-list",
                "name": "List Users",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/scim/v2/Users",
                "description": "Lists all users in the Databricks account.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                    _p("startIndex", "1-based start index.", default="1", type_=INT),
                    _p("count", "Max results per page.", default="100", type_=INT),
                    _p("filter", "SCIM filter expression."),
                ],
                "body": None,
                "path_params": ["account_id"],
            },
            {
                "id": "acct-users-get",
                "name": "Get User",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/scim/v2/Users/{user_id}",
                "description": "Gets details for a single user by ID.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                    _p("user_id", "The user's SCIM ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id", "user_id"],
            },
        ],
    },
    "Account Groups": {
        "icon": "bi-people-fill",
        "color": "#8b5cf6",
        "endpoints": [
            {
                "id": "acct-groups-list",
                "name": "List Groups",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/scim/v2/Groups",
                "description": "Lists all groups in the Databricks account.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                    _p("startIndex", "1-based start index.", default="1", type_=INT),
                    _p("count", "Max results per page.", default="100", type_=INT),
                    _p("filter", "SCIM filter expression."),
                ],
                "body": None,
                "path_params": ["account_id"],
            },
            {
                "id": "acct-groups-get",
                "name": "Get Group",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/scim/v2/Groups/{group_id}",
                "description": "Gets details for a single group by ID.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                    _p("group_id", "The group's SCIM ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id", "group_id"],
            },
        ],
    },
    "Service Principals": {
        "icon": "bi-robot",
        "color": "#f97316",
        "endpoints": [
            {
                "id": "acct-sp-list",
                "name": "List Service Principals",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/scim/v2/ServicePrincipals",
                "description": "Lists all service principals in the account.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                    _p("startIndex", "1-based start index.", default="1", type_=INT),
                    _p("count", "Max results per page.", default="100", type_=INT),
                    _p("filter", "SCIM filter expression."),
                ],
                "body": None,
                "path_params": ["account_id"],
            },
            {
                "id": "acct-sp-get",
                "name": "Get Service Principal",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/scim/v2/ServicePrincipals/{sp_id}",
                "description": "Gets a single service principal by ID.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                    _p("sp_id", "The service principal's SCIM ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id", "sp_id"],
            },
        ],
    },
    "Workspaces": {
        "icon": "bi-building",
        "color": "#00d4ff",
        "endpoints": [
            {
                "id": "acct-workspaces-list",
                "name": "List Workspaces",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/workspaces",
                "description": "Lists all workspaces associated with the account.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id"],
            },
            {
                "id": "acct-workspaces-get",
                "name": "Get Workspace",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/workspaces/{workspace_id}",
                "description": "Gets details for a workspace by its numeric ID.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                    _p("workspace_id", "The workspace ID.", required=True, type_=INT),
                ],
                "body": None,
                "path_params": ["account_id", "workspace_id"],
            },
        ],
    },
    "Credentials": {
        "icon": "bi-key-fill",
        "color": "#eab308",
        "endpoints": [
            {
                "id": "acct-credentials-list",
                "name": "List Credential Configs",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/credentials",
                "description": "Lists all credential configurations for the account.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id"],
            },
            {
                "id": "acct-credentials-get",
                "name": "Get Credential Config",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/credentials/{credentials_id}",
                "description": "Gets a credential configuration by ID.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                    _p("credentials_id", "The credential configuration ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id", "credentials_id"],
            },
        ],
    },
    "Storage": {
        "icon": "bi-bucket-fill",
        "color": "#10b981",
        "endpoints": [
            {
                "id": "acct-storage-list",
                "name": "List Storage Configs",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/storage-configurations",
                "description": "Lists all storage configurations for the account.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id"],
            },
            {
                "id": "acct-storage-get",
                "name": "Get Storage Config",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/storage-configurations/{storage_configuration_id}",
                "description": "Gets a storage configuration by ID.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                    _p("storage_configuration_id", "The storage configuration ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id", "storage_configuration_id"],
            },
        ],
    },
    "Networks": {
        "icon": "bi-diagram-3-fill",
        "color": "#6366f1",
        "endpoints": [
            {
                "id": "acct-networks-list",
                "name": "List Network Configs",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/networks",
                "description": "Lists all network configurations for the account (customer-managed VPC).",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id"],
            },
            {
                "id": "acct-networks-get",
                "name": "Get Network Config",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/networks/{network_id}",
                "description": "Gets a network configuration by ID.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                    _p("network_id", "The network configuration ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id", "network_id"],
            },
        ],
    },
    "Private Access": {
        "icon": "bi-shield-lock-fill",
        "color": "#ec4899",
        "endpoints": [
            {
                "id": "acct-private-access-list",
                "name": "List Private Access Settings",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/private-access-settings",
                "description": "Lists all private access settings for the account.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id"],
            },
            {
                "id": "acct-private-access-get",
                "name": "Get Private Access Settings",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/private-access-settings/{private_access_settings_id}",
                "description": "Gets a private access settings object by ID.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                    _p("private_access_settings_id", "The private access settings ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id", "private_access_settings_id"],
            },
        ],
    },
    "VPC Endpoints": {
        "icon": "bi-plug-fill",
        "color": "#a855f7",
        "endpoints": [
            {
                "id": "acct-vpc-endpoints-list",
                "name": "List VPC Endpoints",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/vpc-endpoints",
                "description": "Lists all registered VPC endpoints for the account.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id"],
            },
            {
                "id": "acct-vpc-endpoints-get",
                "name": "Get VPC Endpoint",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/vpc-endpoints/{vpc_endpoint_id}",
                "description": "Gets a VPC endpoint by ID.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                    _p("vpc_endpoint_id", "The VPC endpoint ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id", "vpc_endpoint_id"],
            },
        ],
    },
    "Encryption Keys": {
        "icon": "bi-lock-fill",
        "color": "#f59e0b",
        "endpoints": [
            {
                "id": "acct-keys-list",
                "name": "List Encryption Key Configs",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/customer-managed-keys",
                "description": "Lists all customer-managed encryption key configurations.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id"],
            },
            {
                "id": "acct-keys-get",
                "name": "Get Encryption Key Config",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/customer-managed-keys/{customer_managed_key_id}",
                "description": "Gets a customer-managed key configuration by ID.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                    _p("customer_managed_key_id", "The key configuration ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id", "customer_managed_key_id"],
            },
        ],
    },
    "Log Delivery": {
        "icon": "bi-journal-text",
        "color": "#84cc16",
        "endpoints": [
            {
                "id": "acct-log-delivery-list",
                "name": "List Log Delivery Configs",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/log-delivery",
                "description": "Lists all log delivery configurations for the account.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                    _p("status", "Filter by status (ENABLED or DISABLED)."),
                    _p("credentials_id", "Filter by credential config ID."),
                    _p("storage_configuration_id", "Filter by storage config ID."),
                ],
                "body": None,
                "path_params": ["account_id"],
            },
            {
                "id": "acct-log-delivery-get",
                "name": "Get Log Delivery Config",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/log-delivery/{log_delivery_configuration_id}",
                "description": "Gets a log delivery configuration by ID.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                    _p("log_delivery_configuration_id", "The log delivery config ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id", "log_delivery_configuration_id"],
            },
        ],
    },
    "Budgets": {
        "icon": "bi-cash-stack",
        "color": "#22d3ee",
        "endpoints": [
            {
                "id": "acct-budgets-list",
                "name": "List Budgets",
                "method": "GET",
                "path": "/api/2.1/accounts/{account_id}/budgets",
                "description": "Lists all budgets for the account.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id"],
            },
            {
                "id": "acct-budgets-get",
                "name": "Get Budget",
                "method": "GET",
                "path": "/api/2.1/accounts/{account_id}/budgets/{budget_id}",
                "description": "Gets a budget by its ID.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                    _p("budget_id", "The budget ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id", "budget_id"],
            },
        ],
    },
    "Usage Download": {
        "icon": "bi-cloud-download",
        "color": "#fb923c",
        "endpoints": [
            {
                "id": "acct-usage-download",
                "name": "Download Usage (CSV)",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/usage/download",
                "description": "Downloads usage data as CSV for the specified date range.",
                "response_format": "csv",
                "timeout": 120,
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                    _p("start_month", "Start month (YYYY-MM format).", required=True, default=_usage_start_month()),
                    _p("end_month", "End month (YYYY-MM format).", required=True, default=_usage_end_month()),
                    _p("personal_data", "Include PII (true/false).", default="false"),
                ],
                "body": None,
                "path_params": ["account_id"],
            },
        ],
    },
    "Account Metastores": {
        "icon": "bi-layers-fill",
        "color": "#6366f1",
        "endpoints": [
            {
                "id": "acct-metastores-list",
                "name": "List Metastores",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/metastores",
                "description": "Lists all Unity Catalog metastores in the account.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id"],
            },
            {
                "id": "acct-metastores-get",
                "name": "Get Metastore",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/metastores/{metastore_id}",
                "description": "Gets a Unity Catalog metastore by ID.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                    _p("metastore_id", "The metastore ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id", "metastore_id"],
            },
            {
                "id": "acct-metastore-assignments-list",
                "name": "List Metastore Assignments",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/metastores/{metastore_id}/workspaces",
                "description": "Lists workspace–metastore assignments for a given metastore.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                    _p("metastore_id", "The metastore ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id", "metastore_id"],
            },
        ],
    },
    "Account Access Control": {
        "icon": "bi-shield-check",
        "color": "#fbbf24",
        "endpoints": [
            {
                "id": "acct-ruleset-get",
                "name": "Get Rule Set",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/access-control/rule-sets",
                "description": "Gets the rule set for an account-level resource.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                    _p("name", "Rule set name (e.g. accounts/{account_id}/ruleSets/default)."),
                    _p("etag", "Etag for optimistic concurrency."),
                ],
                "body": None,
                "path_params": ["account_id"],
            },
        ],
    },
    "Account Settings": {
        "icon": "bi-gear-fill",
        "color": "#94a3b8",
        "endpoints": [
            {
                "id": "acct-settings-personal-compute",
                "name": "Get Personal Compute Setting",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/settings/types/shield_csp_enablement_ac/names/default",
                "description": "Gets the personal compute (compliance security profile) setting.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id"],
            },
            {
                "id": "acct-settings-ip-access-list",
                "name": "List IP Access Lists",
                "method": "GET",
                "path": "/api/2.0/accounts/{account_id}/ip-access-lists",
                "description": "Lists all IP access lists defined at the account level.",
                "params": [
                    _p("account_id", "Databricks account ID.", required=True),
                ],
                "body": None,
                "path_params": ["account_id"],
            },
        ],
    },
}


# ── Account List → Get link map ──────────────────────────────────────────────
ACCOUNT_LIST_TO_GET: Dict[str, Any] = {
    "acct-users-list":              ("acct-users-get",            "Resources",     "id",                          "user_id",                     "displayName"),
    "acct-groups-list":             ("acct-groups-get",           "Resources",     "id",                          "group_id",                    "displayName"),
    "acct-sp-list":                 ("acct-sp-get",               "Resources",     "id",                          "sp_id",                       "displayName"),
    "acct-workspaces-list":         ("acct-workspaces-get",       None,            "workspace_id",                "workspace_id",                "workspace_name"),
    "acct-credentials-list":        ("acct-credentials-get",      None,            "credentials_id",              "credentials_id",              "credentials_name"),
    "acct-storage-list":            ("acct-storage-get",          None,            "storage_configuration_id",    "storage_configuration_id",    "storage_configuration_name"),
    "acct-networks-list":           ("acct-networks-get",         None,            "network_id",                  "network_id",                  "network_name"),
    "acct-private-access-list":     ("acct-private-access-get",   None,            "private_access_settings_id",  "private_access_settings_id",  "private_access_settings_name"),
    "acct-vpc-endpoints-list":      ("acct-vpc-endpoints-get",    None,            "vpc_endpoint_id",             "vpc_endpoint_id",             "vpc_endpoint_name"),
    "acct-keys-list":               ("acct-keys-get",             None,            "customer_managed_key_id",     "customer_managed_key_id",     None),
    "acct-log-delivery-list":       ("acct-log-delivery-get",     "log_delivery_configurations", "config_id", "log_delivery_configuration_id", "config_name"),
    "acct-budgets-list":            ("acct-budgets-get",          "budgets",       "budget_configuration_id",     "budget_id",                   "display_name"),
    "acct-metastores-list":         ("acct-metastores-get",       "metastores",    "metastore_id",                "metastore_id",                "name",
                                     None,
                                     [("acct-metastore-assignments-list", "bi-diagram-3", "List workspace assignments", {"metastore_id": "metastore_id"})]),
}


def _nested_get(obj: Dict, dotted_key: str) -> Any:
    """Retrieve a value from a nested dict using a dotted key path.

    Args:
        obj: The root dictionary.
        dotted_key: Dot-separated key path (e.g. ``"settings.name"``).

    Returns:
        The resolved value, or ``None`` if any segment is missing.
    """
    for part in dotted_key.split("."):
        if not isinstance(obj, dict):
            return None
        obj = obj.get(part)
    return obj


def extract_chips(endpoint_id: str, data: Any) -> List[Dict[str, Any]]:
    """Extract clickable ID chip descriptors from a list API response.

    Chips power the inline navigation links and side-panel items that
    let users jump from a list response to the corresponding *get*
    endpoint for each row.

    Args:
        endpoint_id: The ``id`` of the list endpoint whose response is
            being processed (must be a key in :data:`LIST_TO_GET`).
        data: The parsed JSON response body (typically a ``dict`` with
            a top-level array key).

    Returns:
        A list of chip dicts, each containing:

        * ``get_id`` -- target *get* endpoint ID.
        * ``param`` -- query/path parameter name for the get call.
        * ``id_field`` -- JSON key that holds the identifier.
        * ``value`` -- the identifier value (stringified).
        * ``label`` -- short display label (max 60 chars).
        * ``title`` -- tooltip text (typically the raw ID).
        * ``extras`` -- additional params to pass along.
        * ``actions`` -- list of secondary action dicts.
    """
    mapping = LIST_TO_GET.get(endpoint_id) or ACCOUNT_LIST_TO_GET.get(endpoint_id)
    if not mapping:
        return []
    get_id, list_key, id_field, param_name, label_field = mapping[:5]
    extra_params = mapping[5] if len(mapping) > 5 else None
    actions_def = mapping[6] if len(mapping) > 6 else None
    if not get_id or not param_name:
        return []
    # list_key=None means the response is a bare array
    if list_key is None:
        items = data if isinstance(data, list) else []
    else:
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
        extras = {}
        if extra_params:
            for target_param, source_field in extra_params.items():
                v = item.get(source_field)
                if v is not None:
                    extras[target_param] = str(v)
        actions = []
        if actions_def:
            for act_id, act_icon, act_title, act_params in actions_def:
                act_p = {}
                for tp, sf in act_params.items():
                    v = item.get(sf)
                    if v is not None:
                        act_p[tp] = str(v)
                actions.append({"gid": act_id, "icon": act_icon, "title": act_title, "params": act_p})
        chips.append({
            "get_id":   get_id,
            "param":    param_name,
            "id_field": id_field,
            "value":    str(value),
            "label":    label[:60],
            "title":    str(value),
            "extras":   extras,
            "actions":  actions,
        })
    return chips


def get_endpoint_by_id(endpoint_id: str) -> Optional[Dict[str, Any]]:
    """Find an endpoint definition by its unique string ID.

    Searches every category in both :data:`API_CATALOG` and
    :data:`ACCOUNT_API_CATALOG`.

    Args:
        endpoint_id: The endpoint ``id`` to look up (e.g.
            ``"clusters-list"`` or ``"acct-users-list"``).

    Returns:
        A copy of the endpoint dict enriched with ``category``,
        ``category_color``, and ``scope`` (``"workspace"`` or
        ``"account"``) keys, or ``None`` if not found.
    """
    for catalog, scope in ((API_CATALOG, "workspace"), (ACCOUNT_API_CATALOG, "account")):
        for category_name, category in catalog.items():
            for endpoint in category["endpoints"]:
                if endpoint["id"] == endpoint_id:
                    return {
                        **endpoint,
                        "category": category_name,
                        "category_color": category["color"],
                        "scope": scope,
                    }
    return None


def build_endpoint_map() -> Dict[str, Dict[str, Any]]:
    """Build a flat lookup of all endpoints keyed by their string ID.

    Covers both workspace and account catalogs.  Each value is an
    endpoint dict augmented with ``category``, ``category_color``,
    and ``scope``.

    Returns:
        A ``{endpoint_id: endpoint_dict}`` mapping.
    """
    result: Dict[str, Dict[str, Any]] = {}
    for catalog, scope in ((API_CATALOG, "workspace"), (ACCOUNT_API_CATALOG, "account")):
        for cat_name, cat in catalog.items():
            for endpoint in cat["endpoints"]:
                result[endpoint["id"]] = {
                    **endpoint,
                    "category": cat_name,
                    "category_color": cat["color"],
                    "scope": scope,
                }
    return result


ENDPOINT_MAP = build_endpoint_map()

TOTAL_ENDPOINTS: int = sum(len(c["endpoints"]) for c in API_CATALOG.values())
TOTAL_CATEGORIES: int = len(API_CATALOG)
TOTAL_ACCOUNT_ENDPOINTS: int = sum(len(c["endpoints"]) for c in ACCOUNT_API_CATALOG.values())
TOTAL_ACCOUNT_CATEGORIES: int = len(ACCOUNT_API_CATALOG)
