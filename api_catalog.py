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
    "Lakeflow": {
        "icon": "bi-collection-play",
        "color": "#a855f7",
        "endpoints": [
            # ── Jobs ──────────────────────────────────────────────────────
            {
                "id": "jobs-list",
                "name": "List Jobs",
                "method": "GET",
                "path": "/api/2.2/jobs/list",
                "description": "Retrieves a list of jobs. Does not include deleted jobs. Supports paginated tasks via the 2.2 API.",
                "params": [
                    _p("limit", "Max number of jobs to return (1–100).", default="25", type_=INT),
                    _p("page_token", "Page token for pagination."),
                    _p("expand_tasks", "Include task and cluster spec info (true/false).", default="false"),
                    _p("name", "Filter by job name (substring match)."),
                ],
                "body": None,
            },
            {
                "id": "jobs-get",
                "name": "Get Job",
                "method": "GET",
                "path": "/api/2.2/jobs/get",
                "description": "Retrieves the details for a single job. Tasks and job clusters can be paginated via page_token.",
                "params": [
                    _p("job_id", "The canonical identifier of the job.", required=True, type_=INT),
                    _p("page_token", "Page token for paginated tasks/job_clusters."),
                ],
                "body": None,
            },
            {
                "id": "jobs-create",
                "name": "Create Job",
                "method": "POST",
                "path": "/api/2.2/jobs/create",
                "description": "Create a new job. Returns the canonical identifier for the new job.",
                "params": [],
                "body": '{\n  "name": "<job_name>",\n  "tasks": [\n    {\n      "task_key": "main_task",\n      "notebook_task": {\n        "notebook_path": "/Users/<user>/notebook"\n      },\n      "new_cluster": {\n        "spark_version": "15.4.x-scala2.12",\n        "node_type_id": "i3.xlarge",\n        "num_workers": 2\n      }\n    }\n  ]\n}',
            },
            {
                "id": "jobs-update",
                "name": "Update Job",
                "method": "POST",
                "path": "/api/2.2/jobs/update",
                "description": "Add, update, or remove specific settings of an existing job. Use reset to overwrite all settings.",
                "params": [],
                "body": '{\n  "job_id": <job_id>,\n  "new_settings": {\n    "name": "<new_name>"\n  },\n  "fields_to_remove": []\n}',
            },
            {
                "id": "jobs-reset",
                "name": "Reset Job",
                "method": "POST",
                "path": "/api/2.2/jobs/reset",
                "description": "Overwrite all settings for the given job. Use update to partially modify settings.",
                "params": [],
                "body": '{\n  "job_id": <job_id>,\n  "new_settings": {\n    "name": "<job_name>",\n    "tasks": []\n  }\n}',
            },
            {
                "id": "jobs-delete",
                "name": "Delete Job",
                "method": "POST",
                "path": "/api/2.2/jobs/delete",
                "description": "Deletes a job. Active runs of the job are cancelled.",
                "params": [],
                "body": '{\n  "job_id": <job_id>\n}',
            },
            {
                "id": "jobs-run-now",
                "name": "Trigger New Run",
                "method": "POST",
                "path": "/api/2.2/jobs/run-now",
                "description": "Run a job now and return the run_id of the triggered run.",
                "params": [],
                "body": '{\n  "job_id": <job_id>,\n  "notebook_params": {},\n  "python_params": [],\n  "jar_params": [],\n  "spark_submit_params": []\n}',
            },
            {
                "id": "jobs-runs-submit",
                "name": "Create One-time Run",
                "method": "POST",
                "path": "/api/2.2/jobs/runs/submit",
                "description": "Submit a one-time run. Endpoint allows submission of a workload directly without creating a job.",
                "params": [],
                "body": '{\n  "run_name": "<run_name>",\n  "tasks": [\n    {\n      "task_key": "submit_task",\n      "notebook_task": {\n        "notebook_path": "/Users/<user>/notebook"\n      },\n      "new_cluster": {\n        "spark_version": "15.4.x-scala2.12",\n        "node_type_id": "i3.xlarge",\n        "num_workers": 2\n      }\n    }\n  ]\n}',
            },
            {
                "id": "jobs-runs-list",
                "name": "List Job Runs",
                "method": "GET",
                "path": "/api/2.2/jobs/runs/list",
                "description": "Lists runs in descending order by start time. Supports paginated tasks.",
                "params": [
                    _p("job_id", "Filter runs by job ID (optional).", type_=INT),
                    _p("limit", "Max number of runs to return (1–25).", default="25", type_=INT),
                    _p("page_token", "Page token for pagination."),
                    _p("active_only", "Return only active runs (true/false).", default="false"),
                    _p("completed_only", "Return only completed runs (true/false).", default="false"),
                    _p("expand_tasks", "Include task info (true/false).", default="false"),
                    _p("run_type", "Filter by run type: JOB_RUN, WORKFLOW_RUN, or SUBMIT_RUN."),
                    _p("start_time_from", "Filter runs starting at or after this UTC timestamp (ms).", type_=INT),
                    _p("start_time_to", "Filter runs starting at or before this UTC timestamp (ms).", type_=INT),
                ],
                "body": None,
            },
            {
                "id": "jobs-runs-get",
                "name": "Get Run",
                "method": "GET",
                "path": "/api/2.2/jobs/runs/get",
                "description": "Retrieves the metadata of a run. Iterations and tasks can be paginated via page_token.",
                "params": [
                    _p("run_id", "The canonical identifier of the run.", required=True, type_=INT),
                    _p("include_history", "Include iteration history (true/false).", default="false"),
                    _p("include_resolved_values", "Include resolved parameter values (true/false).", default="false"),
                    _p("page_token", "Page token for paginated iterations/tasks."),
                ],
                "body": None,
            },
            {
                "id": "jobs-runs-get-output",
                "name": "Get Run Output",
                "method": "GET",
                "path": "/api/2.2/jobs/runs/get-output",
                "description": "Retrieve the output and metadata of a single task run. Notebook tasks return the value from dbutils.notebook.exit().",
                "params": [_p("run_id", "The canonical identifier of the run.", required=True, type_=INT)],
                "body": None,
            },
            {
                "id": "jobs-runs-export",
                "name": "Export and Retrieve a Run",
                "method": "GET",
                "path": "/api/2.2/jobs/runs/export",
                "description": "Export and retrieve the job run task. Only notebook runs can be exported.",
                "params": [
                    _p("run_id", "The canonical identifier of the run.", required=True, type_=INT),
                    _p("views_to_export", "Which views to export: CODE, DASHBOARDS, or ALL.", default="CODE"),
                ],
                "body": None,
            },
            {
                "id": "jobs-runs-cancel",
                "name": "Cancel a Run",
                "method": "POST",
                "path": "/api/2.2/jobs/runs/cancel",
                "description": "Cancels a job run or a task run. The run is cancelled asynchronously.",
                "params": [],
                "body": '{\n  "run_id": <run_id>\n}',
            },
            {
                "id": "jobs-runs-cancel-all",
                "name": "Cancel All Runs",
                "method": "POST",
                "path": "/api/2.2/jobs/runs/cancel-all",
                "description": "Cancels all active runs of a job. Pass all_queued_runs=true to also cancel queued runs.",
                "params": [],
                "body": '{\n  "job_id": <job_id>,\n  "all_queued_runs": false\n}',
            },
            {
                "id": "jobs-runs-delete",
                "name": "Delete a Run",
                "method": "POST",
                "path": "/api/2.2/jobs/runs/delete",
                "description": "Deletes a non-active run. Returns an error if the run is active.",
                "params": [],
                "body": '{\n  "run_id": <run_id>\n}',
            },
            {
                "id": "jobs-runs-repair",
                "name": "Repair a Run",
                "method": "POST",
                "path": "/api/2.2/jobs/runs/repair",
                "description": "Re-run one or more failed tasks of a job run. Failed tasks are re-run, while successful tasks are skipped.",
                "params": [],
                "body": '{\n  "run_id": <run_id>,\n  "rerun_tasks": [],\n  "rerun_all_failed_tasks": true,\n  "rerun_dependent_tasks": false\n}',
            },
            # ── Jobs 2.1 (legacy non-paginated reads) ─────────────────────
            {
                "id": "jobs-list-21",
                "name": "List Jobs (2.1)",
                "method": "GET",
                "path": "/api/2.1/jobs/list",
                "description": "Legacy 2.1 list endpoint. Returns up to 100 jobs per call without paginated tasks.",
                "params": [
                    _p("limit", "Max number of jobs to return (1–100).", default="25", type_=INT),
                    _p("offset", "Offset of the first job to return.", default="0", type_=INT),
                    _p("expand_tasks", "Include task and cluster spec info (true/false).", default="false"),
                    _p("name", "Filter by job name (substring match)."),
                ],
                "body": None,
                "legacy": True,
            },
            {
                "id": "jobs-get-21",
                "name": "Get Job (2.1)",
                "method": "GET",
                "path": "/api/2.1/jobs/get",
                "description": "Legacy 2.1 endpoint that returns a job without paginated tasks/job_clusters.",
                "params": [_p("job_id", "The canonical identifier of the job.", required=True, type_=INT)],
                "body": None,
                "legacy": True,
            },
            {
                "id": "jobs-runs-list-21",
                "name": "List Job Runs (2.1)",
                "method": "GET",
                "path": "/api/2.1/jobs/runs/list",
                "description": "Legacy 2.1 endpoint that lists runs without paginated tasks.",
                "params": [
                    _p("job_id", "Filter runs by job ID (optional).", type_=INT),
                    _p("limit", "Max number of runs to return (1–25).", default="25", type_=INT),
                    _p("offset", "Offset of the first run.", default="0", type_=INT),
                    _p("active_only", "Return only active runs (true/false).", default="false"),
                    _p("completed_only", "Return only completed runs (true/false).", default="false"),
                ],
                "body": None,
                "legacy": True,
            },
            {
                "id": "jobs-runs-get-21",
                "name": "Get Run (2.1)",
                "method": "GET",
                "path": "/api/2.1/jobs/runs/get",
                "description": "Legacy 2.1 endpoint that returns run metadata without paginated iterations/tasks.",
                "params": [
                    _p("run_id", "The canonical identifier of the run.", required=True, type_=INT),
                    _p("include_history", "Include iteration history (true/false).", default="false"),
                ],
                "body": None,
                "legacy": True,
            },
            # ── Pipelines (Lakeflow Declarative / DLT) ────────────────────
            {
                "id": "pipelines-list",
                "name": "List Pipelines",
                "method": "GET",
                "path": "/api/2.0/pipelines",
                "description": "Returns a list of pipelines.",
                "params": [
                    _p("max_results", "Maximum number of entries to return.", default="25", type_=INT),
                    _p("page_token", "Page token for pagination."),
                    _p("filter", "Select a subset based on the specified criteria (e.g., state = 'RUNNING')."),
                    _p("order_by", "List of columns to sort by, e.g. 'name asc'."),
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
                "id": "pipelines-create",
                "name": "Create Pipeline",
                "method": "POST",
                "path": "/api/2.0/pipelines",
                "description": "Creates a new Lakeflow Declarative Pipeline. Returns the new pipeline_id.",
                "params": [],
                "body": '{\n  "name": "<pipeline_name>",\n  "storage": "/pipelines/<pipeline_name>",\n  "target": "<target_schema>",\n  "libraries": [\n    {"notebook": {"path": "/Users/<user>/pipeline_notebook"}}\n  ],\n  "continuous": false,\n  "development": true\n}',
            },
            {
                "id": "pipelines-edit",
                "name": "Edit Pipeline",
                "method": "PUT",
                "path": "/api/2.0/pipelines/{pipeline_id}",
                "description": "Updates a pipeline with the supplied configuration. Settings that are not specified are reset to their defaults.",
                "params": [_p("pipeline_id", "The pipeline ID.", required=True)],
                "path_params": ["pipeline_id"],
                "body": '{\n  "id": "<pipeline_id>",\n  "name": "<pipeline_name>",\n  "libraries": [\n    {"notebook": {"path": "/Users/<user>/pipeline_notebook"}}\n  ]\n}',
            },
            {
                "id": "pipelines-delete",
                "name": "Delete Pipeline",
                "method": "DELETE",
                "path": "/api/2.0/pipelines/{pipeline_id}",
                "description": "Deletes a pipeline. Pipeline must not be running.",
                "params": [_p("pipeline_id", "The pipeline ID.", required=True)],
                "path_params": ["pipeline_id"],
                "body": None,
            },
            {
                "id": "pipelines-stop",
                "name": "Stop Pipeline",
                "method": "POST",
                "path": "/api/2.0/pipelines/{pipeline_id}/stop",
                "description": "Stops the pipeline by canceling the active update. No-op if there is no active update.",
                "params": [_p("pipeline_id", "The pipeline ID.", required=True)],
                "path_params": ["pipeline_id"],
                "body": None,
            },
            {
                "id": "pipelines-start-update",
                "name": "Start a Pipeline Update",
                "method": "POST",
                "path": "/api/2.0/pipelines/{pipeline_id}/updates",
                "description": "Starts a new update for the pipeline. Returns update_id.",
                "params": [_p("pipeline_id", "The pipeline ID.", required=True)],
                "path_params": ["pipeline_id"],
                "body": '{\n  "full_refresh": false,\n  "refresh_selection": [],\n  "full_refresh_selection": [],\n  "cause": "API_CALL"\n}',
            },
            {
                "id": "pipelines-list-updates",
                "name": "List Pipeline Updates",
                "method": "GET",
                "path": "/api/2.0/pipelines/{pipeline_id}/updates",
                "description": "Lists updates for a pipeline.",
                "params": [
                    _p("pipeline_id", "The pipeline ID.", required=True),
                    _p("max_results", "Max number of entries to return.", default="25", type_=INT),
                    _p("page_token", "Page token for pagination."),
                    _p("until_update_id", "If present, returns updates until and including this update_id."),
                ],
                "path_params": ["pipeline_id"],
                "body": None,
            },
            {
                "id": "pipelines-get-update",
                "name": "Get a Pipeline Update",
                "method": "GET",
                "path": "/api/2.0/pipelines/{pipeline_id}/updates/{update_id}",
                "description": "Gets an update for a pipeline.",
                "params": [
                    _p("pipeline_id", "The pipeline ID.", required=True),
                    _p("update_id", "The update ID.", required=True),
                ],
                "path_params": ["pipeline_id", "update_id"],
                "body": None,
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
                    _p("page_token", "Page token for pagination."),
                    _p("filter", "Filter expression (e.g., level = 'ERROR')."),
                    _p("order_by", "Order by, e.g. 'timestamp desc'."),
                ],
                "body": None,
                "path_params": ["pipeline_id"],
            },
            # ── Policy Compliance for Jobs ────────────────────────────────
            {
                "id": "jobs-list-compliance",
                "name": "List Compliance for Jobs",
                "method": "GET",
                "path": "/api/2.0/policies/jobs/list-compliance",
                "description": "Returns the policy compliance status of jobs that use a given policy. Jobs can be out of compliance if their policy was updated after the job was last edited.",
                "params": [
                    _p("policy_id", "Canonical unique identifier for the cluster policy.", required=True),
                    _p("page_size", "Maximum number of results returned per page.", type_=INT),
                    _p("page_token", "Page token for pagination."),
                ],
                "body": None,
            },
            {
                "id": "jobs-get-compliance",
                "name": "Get Job Compliance",
                "method": "GET",
                "path": "/api/2.0/policies/jobs/get-compliance",
                "description": "Returns the policy compliance status of a single job.",
                "params": [_p("job_id", "The ID of the job to get compliance status for.", required=True, type_=INT)],
                "body": None,
            },
            {
                "id": "jobs-enforce-compliance",
                "name": "Enforce Job Compliance",
                "method": "POST",
                "path": "/api/2.0/policies/jobs/enforce-compliance",
                "description": "Updates job clusters to be compliant with the current version of the policy. Use validate_only=true to preview changes without applying them.",
                "params": [],
                "body": '{\n  "job_id": <job_id>,\n  "validate_only": false\n}',
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
            {
                "id": "dbfs-read",
                "name": "Read File",
                "method": "GET",
                "path": "/api/2.0/dbfs/read",
                "description": "Returns the contents of a file (base64-encoded). Files larger than 1 MB must be read in chunks via offset and length.",
                "params": [
                    _p("path", "The path of the file to read.", required=True),
                    _p("offset", "The offset to read from in bytes.", type_=INT),
                    _p("length", "The number of bytes to read (max 1 MB / 1048576).", type_=INT),
                ],
                "body": None,
            },
            {
                "id": "dbfs-create",
                "name": "Open Upload Stream",
                "method": "POST",
                "path": "/api/2.0/dbfs/create",
                "description": "Opens a stream for writing to a file. Returns a handle used by add-block and close to upload the contents in chunks.",
                "params": [],
                "body": '{\n  "path": "/tmp/example.txt",\n  "overwrite": true\n}',
            },
            {
                "id": "dbfs-add-block",
                "name": "Append Block",
                "method": "POST",
                "path": "/api/2.0/dbfs/add-block",
                "description": "Appends a block of data (base64-encoded, up to 1 MB) to the upload stream identified by handle.",
                "params": [],
                "body": '{\n  "handle": 0,\n  "data": ""\n}',
            },
            {
                "id": "dbfs-close",
                "name": "Close Upload Stream",
                "method": "POST",
                "path": "/api/2.0/dbfs/close",
                "description": "Closes the upload stream identified by handle, committing the file.",
                "params": [],
                "body": '{\n  "handle": 0\n}',
            },
            {
                "id": "dbfs-put",
                "name": "Put File (Single-Shot Upload)",
                "method": "POST",
                "path": "/api/2.0/dbfs/put",
                "description": "Uploads a file in a single request. The contents must be base64-encoded and at most 1 MB.",
                "params": [],
                "body": '{\n  "path": "/tmp/example.txt",\n  "contents": "",\n  "overwrite": true\n}',
            },
            {
                "id": "dbfs-mkdirs",
                "name": "Create Directory",
                "method": "POST",
                "path": "/api/2.0/dbfs/mkdirs",
                "description": "Creates the given directory and any necessary parent directories. Idempotent if the directory already exists.",
                "params": [],
                "body": '{\n  "path": "/tmp/new-dir"\n}',
            },
            {
                "id": "dbfs-move",
                "name": "Move",
                "method": "POST",
                "path": "/api/2.0/dbfs/move",
                "description": "Moves a file or directory between DBFS paths. The source and destination must both be on DBFS.",
                "params": [],
                "body": '{\n  "source_path": "/tmp/source",\n  "destination_path": "/tmp/dest"\n}',
            },
            {
                "id": "dbfs-delete",
                "name": "Delete",
                "method": "POST",
                "path": "/api/2.0/dbfs/delete",
                "description": "Deletes the file or directory at the given path. Set recursive=true to delete a non-empty directory.",
                "params": [],
                "body": '{\n  "path": "/tmp/to-delete",\n  "recursive": false\n}',
            },
        ],
    },
    "Files": {
        "icon": "bi-file-earmark",
        "color": "#22c55e",
        "endpoints": [
            {
                "id": "files-list-directory-contents",
                "name": "List Directory Contents",
                "method": "GET",
                "path": "/api/2.0/fs/directories{directory_path}",
                "description": "Lists the contents of a UC Volume directory. Tip: list your volumes first via Unity Catalog → List Volumes to find a real path.",
                "params": [
                    _p("directory_path", "Path under /Volumes/<catalog>/<schema>/<volume> — must point to an existing UC Volume; the API rejects '/' or empty values.", required=True, default="/Volumes/main/default/myvolume"),
                    _p("page_token", "Opaque token for paginating results."),
                    _p("page_size", "Maximum number of items to return per page.", type_=INT),
                ],
                "body": None,
                "path_params": ["directory_path"],
            },
            {
                "id": "files-get-directory-metadata",
                "name": "Get Directory Metadata",
                "method": "HEAD",
                "path": "/api/2.0/fs/directories{directory_path}",
                "description": "Returns metadata for a directory (existence and headers only, no body).",
                "params": [
                    _p("directory_path", "Path under /Volumes/<catalog>/<schema>/<volume>.", required=True, default="/Volumes/main/default/myvolume"),
                ],
                "body": None,
                "path_params": ["directory_path"],
            },
            {
                "id": "files-create-directory",
                "name": "Create Directory",
                "method": "PUT",
                "path": "/api/2.0/fs/directories{directory_path}",
                "description": "Creates an empty directory in a UC Volume. Idempotent — succeeds if the directory already exists.",
                "params": [
                    _p("directory_path", "Path under /Volumes/<catalog>/<schema>/<volume> for the new directory.", required=True, default="/Volumes/main/default/myvolume/new-dir"),
                ],
                "body": None,
                "path_params": ["directory_path"],
            },
            {
                "id": "files-delete-directory",
                "name": "Delete Directory",
                "method": "DELETE",
                "path": "/api/2.0/fs/directories{directory_path}",
                "description": "Deletes an empty directory. Returns an error if the directory is not empty.",
                "params": [
                    _p("directory_path", "Path under /Volumes/<catalog>/<schema>/<volume>.", required=True),
                ],
                "body": None,
                "path_params": ["directory_path"],
            },
            {
                "id": "files-get-metadata",
                "name": "Get File Metadata",
                "method": "HEAD",
                "path": "/api/2.0/fs/files{file_path}",
                "description": "Returns metadata for a file (existence, content-length, content-type) via response headers.",
                "params": [
                    _p("file_path", "Path under /Volumes/<catalog>/<schema>/<volume>/<file>.", required=True, default="/Volumes/main/default/myvolume/myfile.txt"),
                ],
                "body": None,
                "path_params": ["file_path"],
            },
            {
                "id": "files-download",
                "name": "Download File",
                "method": "GET",
                "path": "/api/2.0/fs/files{file_path}",
                "description": "Downloads the contents of a file. Response is the raw file bytes — not JSON. Useful for small text files.",
                "params": [
                    _p("file_path", "Path under /Volumes/<catalog>/<schema>/<volume>/<file>.", required=True, default="/Volumes/main/default/myvolume/myfile.txt"),
                ],
                "body": None,
                "path_params": ["file_path"],
            },
            {
                "id": "files-upload",
                "name": "Upload File",
                "method": "PUT",
                "path": "/api/2.0/fs/files{file_path}",
                "description": "Uploads a file to a UC Volume. The body is the raw file bytes — not supported via this JSON-based explorer; use the Databricks CLI instead.",
                "params": [
                    _p("file_path", "Path under /Volumes/<catalog>/<schema>/<volume>/<file>.", required=True, default="/Volumes/main/default/myvolume/myfile.txt"),
                    _p("overwrite", "Whether to overwrite an existing file.", type_=BOOL),
                ],
                "body": None,
                "path_params": ["file_path"],
            },
            {
                "id": "files-delete",
                "name": "Delete File",
                "method": "DELETE",
                "path": "/api/2.0/fs/files{file_path}",
                "description": "Deletes a file from a UC Volume.",
                "params": [
                    _p("file_path", "Path under /Volumes/<catalog>/<schema>/<volume>/<file>.", required=True),
                ],
                "body": None,
                "path_params": ["file_path"],
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
    "Experiments Tracing": {
        "icon": "bi-bezier",
        "color": "#22d3ee",
        "endpoints": [
            {
                "id": "trace-search",
                "name": "Search Traces",
                "method": "POST",
                "path": "/api/3.0/mlflow/traces/search",
                "description": "Search for traces that match the supplied filter and locations. Returns a paginated list of traces.",
                "params": [],
                "body": '{\n  "locations": [\n    {\n      "type": "MLFLOW_EXPERIMENT",\n      "mlflow_experiment": { "experiment_id": "<experiment-id>" }\n    }\n  ],\n  "max_results": 100\n}',
            },
            {
                "id": "trace-get-info",
                "name": "Get Trace",
                "method": "GET",
                "path": "/api/3.0/mlflow/traces/{trace_id}",
                "description": "Get trace info (metadata, assessments, tags) for a single trace by ID.",
                "params": [_p("trace_id", "The ID of the trace to fetch.", required=True)],
                "path_params": ["trace_id"],
                "body": None,
            },
            {
                "id": "trace-start",
                "name": "Create Trace",
                "method": "POST",
                "path": "/api/3.0/mlflow/traces",
                "description": "Create a new trace within an experiment. Omit state and execution_duration to leave the trace IN_PROGRESS, then finalize it via 'End Trace'.",
                "params": [],
                "body": '{\n  "trace": {\n    "trace_info": {\n      "trace_location": {\n        "type": "MLFLOW_EXPERIMENT",\n        "mlflow_experiment": { "experiment_id": "<experiment-id>" }\n      },\n      "request_time": "2026-01-01T00:00:00Z"\n    }\n  }\n}',
            },
            {
                "id": "trace-end",
                "name": "End Trace",
                "method": "PATCH",
                "path": "/api/3.0/mlflow/traces/{trace_id}",
                "description": "Finalize an in-progress trace by setting state and execution_duration.",
                "params": [_p("trace_id", "The ID of the trace.", required=True)],
                "path_params": ["trace_id"],
                "body": '{\n  "trace": {\n    "trace_info": {\n      "state": "OK",\n      "execution_duration": "1.0s"\n    }\n  },\n  "update_mask": "trace.trace_info.state,trace.trace_info.execution_duration"\n}',
            },
            {
                "id": "trace-delete-batch",
                "name": "Delete Traces",
                "method": "POST",
                "path": "/api/3.0/mlflow/traces/delete-traces",
                "description": "Bulk-delete traces from an experiment by list of trace_ids or by max_timestamp_millis / max_traces filter.",
                "params": [],
                "body": '{\n  "experiment_id": "<experiment-id>",\n  "trace_ids": ["<trace-id>"]\n}',
            },
            {
                "id": "trace-set-tag",
                "name": "Set Trace Tag",
                "method": "PATCH",
                "path": "/api/3.0/mlflow/traces/{trace_id}/tags",
                "description": "Set or update a single tag (key/value) on a trace.",
                "params": [_p("trace_id", "The ID of the trace on which to set the tag.", required=True)],
                "path_params": ["trace_id"],
                "body": '{\n  "key": "<tag-name>",\n  "value": "<tag-value>"\n}',
            },
            {
                "id": "trace-delete-tag",
                "name": "Delete Trace Tag",
                "method": "DELETE",
                "path": "/api/3.0/mlflow/traces/{trace_id}/tags",
                "description": "Delete a tag from a trace by key.",
                "params": [
                    _p("trace_id", "The ID of the trace from which to delete the tag.", required=True),
                    _p("key", "The name of the tag to delete.", required=True),
                ],
                "path_params": ["trace_id"],
                "body": None,
            },
            {
                "id": "trace-assessment-create",
                "name": "Create Assessment",
                "method": "POST",
                "path": "/api/3.0/mlflow/traces/{trace_id}/assessments",
                "description": "Create an assessment (feedback or expectation) on a trace.",
                "params": [_p("trace_id", "The ID of the trace the assessment belongs to.", required=True)],
                "path_params": ["trace_id"],
                "body": '{\n  "assessment": {\n    "assessment_name": "<name>",\n    "feedback": { "value": "good" },\n    "source": { "source_type": "HUMAN", "source_id": "<user@example.com>" }\n  }\n}',
            },
            {
                "id": "trace-assessment-get",
                "name": "Get Assessment",
                "method": "GET",
                "path": "/api/3.0/mlflow/traces/{trace_id}/assessments/{assessment_id}",
                "description": "Retrieve a single assessment of a trace.",
                "params": [
                    _p("trace_id", "The ID of the trace the assessment belongs to.", required=True),
                    _p("assessment_id", "The ID of the assessment.", required=True),
                ],
                "path_params": ["trace_id", "assessment_id"],
                "body": None,
            },
            {
                "id": "trace-assessment-update",
                "name": "Update Assessment",
                "method": "PATCH",
                "path": "/api/3.0/mlflow/traces/{trace_id}/assessments/{assessment_id}",
                "description": "Update fields on an assessment (e.g. rationale, feedback). Use update_mask to specify which fields to change.",
                "params": [
                    _p("trace_id", "The ID of the trace the assessment belongs to.", required=True),
                    _p("assessment_id", "The ID of the assessment.", required=True),
                ],
                "path_params": ["trace_id", "assessment_id"],
                "body": '{\n  "assessment": {\n    "rationale": "<updated rationale>"\n  },\n  "update_mask": "rationale"\n}',
            },
            {
                "id": "trace-assessment-delete",
                "name": "Delete Assessment",
                "method": "DELETE",
                "path": "/api/3.0/mlflow/traces/{trace_id}/assessments/{assessment_id}",
                "description": "Delete an assessment from a trace.",
                "params": [
                    _p("trace_id", "The ID of the trace the assessment belongs to.", required=True),
                    _p("assessment_id", "The ID of the assessment.", required=True),
                ],
                "path_params": ["trace_id", "assessment_id"],
                "body": None,
            },
            {
                "id": "trace-credentials-download",
                "name": "Get Trace Data Download Credentials",
                "method": "GET",
                "path": "/api/3.0/mlflow/traces/{trace_id}/credentials-for-data-download",
                "description": "Get short-lived credentials for downloading trace artifact data (defaults to traces.json).",
                "params": [
                    _p("trace_id", "The ID of the trace.", required=True),
                    _p("path", "Optional relative path within the trace artifact directory. Defaults to 'traces.json'."),
                ],
                "path_params": ["trace_id"],
                "body": None,
            },
            {
                "id": "trace-credentials-upload",
                "name": "Get Trace Data Upload Credentials",
                "method": "GET",
                "path": "/api/3.0/mlflow/traces/{trace_id}/credentials-for-data-upload",
                "description": "Get short-lived credentials for uploading trace artifact data (defaults to traces.json).",
                "params": [
                    _p("trace_id", "The ID of the trace.", required=True),
                    _p("path", "Optional relative path within the trace artifact directory. Defaults to 'traces.json'."),
                ],
                "path_params": ["trace_id"],
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
                "description": "Returns a list of instance pools with their statistics.",
                "params": [],
                "body": None,
            },
            {
                "id": "instance-pools-get",
                "name": "Get Instance Pool",
                "method": "GET",
                "path": "/api/2.0/instance-pools/get",
                "description": "Retrieves an instance pool definition by ID.",
                "params": [_p("instance_pool_id", "The instance pool ID.", required=True)],
                "body": None,
            },
            {
                "id": "instance-pools-create",
                "name": "Create Instance Pool",
                "method": "POST",
                "path": "/api/2.0/instance-pools/create",
                "description": "Creates a new instance pool using idle and ready-to-use cloud instances.",
                "params": [],
                "body": '{\n  "instance_pool_name": "my-pool",\n  "node_type_id": "i3.xlarge",\n  "min_idle_instances": 0,\n  "max_capacity": 10,\n  "idle_instance_autotermination_minutes": 60,\n  "enable_elastic_disk": true,\n  "preloaded_spark_versions": []\n}',
            },
            {
                "id": "instance-pools-edit",
                "name": "Edit Instance Pool",
                "method": "POST",
                "path": "/api/2.0/instance-pools/edit",
                "description": "Modifies the configuration of an existing instance pool.",
                "params": [],
                "body": '{\n  "instance_pool_id": "<instance_pool_id>",\n  "instance_pool_name": "my-pool",\n  "node_type_id": "i3.xlarge",\n  "min_idle_instances": 0,\n  "max_capacity": 10,\n  "idle_instance_autotermination_minutes": 60\n}',
            },
            {
                "id": "instance-pools-delete",
                "name": "Delete Instance Pool",
                "method": "POST",
                "path": "/api/2.0/instance-pools/delete",
                "description": "Deletes the instance pool permanently. Any idle instances in the pool are terminated asynchronously.",
                "params": [],
                "body": '{\n  "instance_pool_id": "<instance_pool_id>"\n}',
            },
            {
                "id": "instance-pools-permission-levels",
                "name": "Get Instance Pool Permission Levels",
                "method": "GET",
                "path": "/api/2.0/permissions/instance-pools/{instance_pool_id}/permissionLevels",
                "description": "Gets the permission levels that a user can have on an instance pool.",
                "params": [_p("instance_pool_id", "The instance pool ID.", required=True)],
                "path_params": ["instance_pool_id"],
                "body": None,
            },
            {
                "id": "instance-pools-permissions-get",
                "name": "Get Instance Pool Permissions",
                "method": "GET",
                "path": "/api/2.0/permissions/instance-pools/{instance_pool_id}",
                "description": "Gets the permissions of an instance pool. Instance pools can inherit permissions from their root object.",
                "params": [_p("instance_pool_id", "The instance pool ID.", required=True)],
                "path_params": ["instance_pool_id"],
                "body": None,
            },
            {
                "id": "instance-pools-permissions-set",
                "name": "Set Instance Pool Permissions",
                "method": "PUT",
                "path": "/api/2.0/permissions/instance-pools/{instance_pool_id}",
                "description": "Sets permissions on an object, replacing existing permissions if they exist.",
                "params": [_p("instance_pool_id", "The instance pool ID.", required=True)],
                "path_params": ["instance_pool_id"],
                "body": '{\n  "access_control_list": [\n    {\n      "user_name": "user@example.com",\n      "permission_level": "CAN_ATTACH_TO"\n    }\n  ]\n}',
            },
            {
                "id": "instance-pools-permissions-update",
                "name": "Update Instance Pool Permissions",
                "method": "PATCH",
                "path": "/api/2.0/permissions/instance-pools/{instance_pool_id}",
                "description": "Updates the permissions on an instance pool. Instance pools can inherit permissions from their root object.",
                "params": [_p("instance_pool_id", "The instance pool ID.", required=True)],
                "path_params": ["instance_pool_id"],
                "body": '{\n  "access_control_list": [\n    {\n      "user_name": "user@example.com",\n      "permission_level": "CAN_MANAGE"\n    }\n  ]\n}',
            },
        ],
    },
    "Instance Profiles": {
        "icon": "bi-person-badge",
        "color": "#fb923c",
        "endpoints": [
            {
                "id": "instance-profiles-list",
                "name": "List Instance Profiles",
                "method": "GET",
                "path": "/api/2.0/instance-profiles/list",
                "description": "Lists the instance profiles that the calling user can use to launch a cluster (AWS only).",
                "params": [],
                "body": None,
            },
            {
                "id": "instance-profiles-add",
                "name": "Add Instance Profile",
                "method": "POST",
                "path": "/api/2.0/instance-profiles/add",
                "description": "Registers an instance profile in Databricks. In the UI, admin users can then give users the permission to use this instance profile when launching clusters (AWS only).",
                "params": [],
                "body": '{\n  "instance_profile_arn": "arn:aws:iam::<account-id>:instance-profile/<profile-name>",\n  "iam_role_arn": "arn:aws:iam::<account-id>:role/<role-name>",\n  "is_meta_instance_profile": false,\n  "skip_validation": false\n}',
            },
            {
                "id": "instance-profiles-edit",
                "name": "Edit Instance Profile",
                "method": "POST",
                "path": "/api/2.0/instance-profiles/edit",
                "description": "Changes the optional IAM role ARN and/or meta-instance-profile flag associated with a registered instance profile (AWS only).",
                "params": [],
                "body": '{\n  "instance_profile_arn": "arn:aws:iam::<account-id>:instance-profile/<profile-name>",\n  "iam_role_arn": "arn:aws:iam::<account-id>:role/<role-name>",\n  "is_meta_instance_profile": false\n}',
            },
            {
                "id": "instance-profiles-remove",
                "name": "Remove Instance Profile",
                "method": "POST",
                "path": "/api/2.0/instance-profiles/remove",
                "description": "Removes the instance profile with the provided ARN. Existing clusters with this instance profile continue to work (AWS only).",
                "params": [],
                "body": '{\n  "instance_profile_arn": "arn:aws:iam::<account-id>:instance-profile/<profile-name>"\n}',
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
            {
                "id": "policies-list-compliance",
                "name": "List Compliance for Clusters",
                "method": "GET",
                "path": "/api/2.0/policies/clusters/list-compliance",
                "description": "Returns the policy compliance status of all clusters that use a given policy. Clusters can be out of compliance if their policy was updated after the cluster was last edited.",
                "params": [
                    _p("policy_id", "Canonical unique identifier for the cluster policy.", required=True),
                    _p("page_size", "Maximum number of results returned per page.", type_=INT),
                    _p("page_token", "Page token for pagination."),
                ],
                "body": None,
            },
            {
                "id": "policies-get-compliance",
                "name": "Get Cluster Compliance",
                "method": "GET",
                "path": "/api/2.0/policies/clusters/get-compliance",
                "description": "Returns the policy compliance status of a single cluster. A cluster can be out of compliance if its policy was updated after the cluster was last edited.",
                "params": [_p("cluster_id", "The ID of the cluster to get the compliance status of.", required=True)],
                "body": None,
            },
            {
                "id": "policies-enforce-compliance",
                "name": "Enforce Cluster Compliance",
                "method": "POST",
                "path": "/api/2.0/policies/clusters/enforce-compliance",
                "description": "Updates a cluster to be compliant with the current version of its policy. A RUNNING cluster will be restarted; a TERMINATED cluster picks up the new attributes on next start. Use validate_only=true to preview changes without applying them.",
                "params": [],
                "body": '{\n  "cluster_id": "<cluster_id>",\n  "validate_only": false\n}',
            },
            {
                "id": "policy-families-list",
                "name": "List Policy Families",
                "method": "GET",
                "path": "/api/2.0/policy-families",
                "description": "Returns the list of policy definition families that the user has access to. Policy families are templates that can be used to create cluster policies.",
                "params": [
                    _p("max_results", "Maximum number of policy families to return.", type_=INT),
                    _p("page_token", "A token that can be used to get the next page of results."),
                ],
                "body": None,
            },
            {
                "id": "policy-families-get",
                "name": "Get Policy Family",
                "method": "GET",
                "path": "/api/2.0/policy-families/{policy_family_id}",
                "description": "Retrieves the policy definition family for the given family ID.",
                "params": [_p("policy_family_id", "The family ID about which to retrieve information.", required=True)],
                "path_params": ["policy_family_id"],
                "body": None,
            },
        ],
    },
    "Libraries": {
        "icon": "bi-bookshelf",
        "color": "#a78bfa",
        "endpoints": [
            {
                "id": "libraries-all-cluster-statuses",
                "name": "All Cluster Library Statuses",
                "method": "GET",
                "path": "/api/2.0/libraries/all-cluster-statuses",
                "description": "Returns library statuses for all clusters in the workspace, including library installation states and any errors.",
                "params": [],
                "body": None,
            },
            {
                "id": "libraries-cluster-status",
                "name": "Cluster Library Status",
                "method": "GET",
                "path": "/api/2.0/libraries/cluster-status",
                "description": "Returns the status of all libraries on a specific cluster, including pending, installing, installed, failed, and uninstalled libraries.",
                "params": [_p("cluster_id", "The unique identifier of the cluster.", required=True)],
                "body": None,
            },
            {
                "id": "libraries-install",
                "name": "Install Libraries",
                "method": "POST",
                "path": "/api/2.0/libraries/install",
                "description": "Installs libraries on a cluster. Installation is asynchronous; libraries are installed once the cluster is RUNNING. Supports jar, egg, whl, pypi, maven, cran, and requirements library types.",
                "params": [],
                "body": '{\n  "cluster_id": "<cluster_id>",\n  "libraries": [\n    {"pypi": {"package": "simplejson==3.8.0"}},\n    {"jar": "dbfs:/mnt/libraries/library.jar"},\n    {"whl": "dbfs:/mnt/libraries/library.whl"},\n    {"maven": {"coordinates": "org.jsoup:jsoup:1.7.2", "exclusions": []}},\n    {"cran": {"package": "ggplot2"}},\n    {"requirements": "dbfs:/path/to/requirements.txt"}\n  ]\n}',
            },
            {
                "id": "libraries-uninstall",
                "name": "Uninstall Libraries",
                "method": "POST",
                "path": "/api/2.0/libraries/uninstall",
                "description": "Marks libraries on a cluster to be uninstalled. The libraries are not actually uninstalled until the cluster is restarted.",
                "params": [],
                "body": '{\n  "cluster_id": "<cluster_id>",\n  "libraries": [\n    {"pypi": {"package": "simplejson==3.8.0"}}\n  ]\n}',
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
    "Git Credentials": {
        "icon": "bi-key",
        "color": "#f472b6",
        "endpoints": [
            {
                "id": "git-credentials-list",
                "name": "List Git Credentials",
                "method": "GET",
                "path": "/api/2.0/git-credentials",
                "description": "Lists the calling user's Git credentials. One credential per remote is supported.",
                "params": [],
                "body": None,
            },
            {
                "id": "git-credentials-get",
                "name": "Get Git Credential",
                "method": "GET",
                "path": "/api/2.0/git-credentials/{credential_id}",
                "description": "Gets the Git credential with the specified credential ID.",
                "params": [_p("credential_id", "The ID of the Git credential.", required=True, type_=INT)],
                "path_params": ["credential_id"],
                "body": None,
            },
            {
                "id": "git-credentials-create",
                "name": "Create Git Credential",
                "method": "POST",
                "path": "/api/2.0/git-credentials",
                "description": "Creates a Git credential entry for the user. Only one Git credential per remote is supported.",
                "params": [],
                "body": '{\n  "git_provider": "gitHub",\n  "git_username": "<username>",\n  "personal_access_token": "<token>"\n}',
            },
            {
                "id": "git-credentials-update",
                "name": "Update Git Credential",
                "method": "PATCH",
                "path": "/api/2.0/git-credentials/{credential_id}",
                "description": "Updates the specified Git credential.",
                "params": [_p("credential_id", "The ID of the Git credential.", required=True, type_=INT)],
                "path_params": ["credential_id"],
                "body": '{\n  "git_provider": "gitHub",\n  "git_username": "<username>",\n  "personal_access_token": "<new-token>"\n}',
            },
            {
                "id": "git-credentials-delete",
                "name": "Delete Git Credential",
                "method": "DELETE",
                "path": "/api/2.0/git-credentials/{credential_id}",
                "description": "Deletes the specified Git credential.",
                "params": [_p("credential_id", "The ID of the Git credential.", required=True, type_=INT)],
                "path_params": ["credential_id"],
                "body": None,
            },
        ],
    },
    "Global Init Scripts": {
        "icon": "bi-file-earmark-code",
        "color": "#f59e0b",
        "endpoints": [
            {
                "id": "global-init-scripts-list",
                "name": "List Global Init Scripts",
                "method": "GET",
                "path": "/api/2.0/global-init-scripts",
                "description": "Lists all global init scripts for this workspace (metadata only — use Get to retrieve script content).",
                "params": [],
                "body": None,
            },
            {
                "id": "global-init-scripts-get",
                "name": "Get Global Init Script",
                "method": "GET",
                "path": "/api/2.0/global-init-scripts/{script_id}",
                "description": "Gets a single global init script, including the base64-encoded script content.",
                "params": [_p("script_id", "The ID of the global init script.", required=True)],
                "path_params": ["script_id"],
                "body": None,
            },
            {
                "id": "global-init-scripts-create",
                "name": "Create Global Init Script",
                "method": "POST",
                "path": "/api/2.0/global-init-scripts",
                "description": "Creates a new global init script. Script content must be base64-encoded.",
                "params": [],
                "body": '{\n  "name": "my-init-script",\n  "script": "<base64-encoded-bash>",\n  "enabled": true,\n  "position": 0\n}',
            },
            {
                "id": "global-init-scripts-update",
                "name": "Update Global Init Script",
                "method": "PATCH",
                "path": "/api/2.0/global-init-scripts/{script_id}",
                "description": "Updates a global init script. Script content must be base64-encoded when provided.",
                "params": [_p("script_id", "The ID of the global init script.", required=True)],
                "path_params": ["script_id"],
                "body": '{\n  "name": "my-init-script",\n  "script": "<base64-encoded-bash>",\n  "enabled": true,\n  "position": 0\n}',
            },
            {
                "id": "global-init-scripts-delete",
                "name": "Delete Global Init Script",
                "method": "DELETE",
                "path": "/api/2.0/global-init-scripts/{script_id}",
                "description": "Deletes a global init script.",
                "params": [_p("script_id", "The ID of the global init script.", required=True)],
                "path_params": ["script_id"],
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
    "Data Quality Monitoring": {
        "icon": "bi-clipboard-check",
        "color": "#a78bfa",
        "endpoints": [
            {
                "id": "dqm-monitor-create",
                "name": "Create Monitor",
                "method": "POST",
                "path": "/api/2.1/unity-catalog/tables/{table_name}/monitor",
                "description": "Creates a data quality monitor on a Unity Catalog table.",
                "params": [_p("table_name", "Full table name: catalog.schema.table", required=True)],
                "path_params": ["table_name"],
                "body": '{\n  "assets_dir": "/Shared/monitoring",\n  "output_schema_name": "monitoring_schema",\n  "schedule": {\n    "quartz_cron_expression": "0 0 8 * * ?",\n    "timezone_id": "UTC"\n  },\n  "skip_builtin_dashboard": false\n}',
            },
            {
                "id": "dqm-monitor-get",
                "name": "Get Monitor",
                "method": "GET",
                "path": "/api/2.1/unity-catalog/tables/{table_name}/monitor",
                "description": "Gets a data quality monitor for a Unity Catalog table.",
                "params": [_p("table_name", "Full table name: catalog.schema.table", required=True)],
                "path_params": ["table_name"],
                "body": None,
            },
            {
                "id": "dqm-monitor-update",
                "name": "Update Monitor",
                "method": "PUT",
                "path": "/api/2.1/unity-catalog/tables/{table_name}/monitor",
                "description": "Updates a data quality monitor on a Unity Catalog table.",
                "params": [_p("table_name", "Full table name: catalog.schema.table", required=True)],
                "path_params": ["table_name"],
                "body": '{\n  "output_schema_name": "monitoring_schema",\n  "schedule": {\n    "quartz_cron_expression": "0 0 8 * * ?",\n    "timezone_id": "UTC"\n  }\n}',
            },
            {
                "id": "dqm-monitor-delete",
                "name": "Delete Monitor",
                "method": "DELETE",
                "path": "/api/2.1/unity-catalog/tables/{table_name}/monitor",
                "description": "Deletes a data quality monitor from a Unity Catalog table.",
                "params": [_p("table_name", "Full table name: catalog.schema.table", required=True)],
                "path_params": ["table_name"],
                "body": None,
            },
            {
                "id": "dqm-refreshes-run",
                "name": "Run Refresh",
                "method": "POST",
                "path": "/api/2.1/unity-catalog/tables/{table_name}/monitor/refreshes",
                "description": "Queues a metric refresh for a data quality monitor.",
                "params": [_p("table_name", "Full table name: catalog.schema.table", required=True)],
                "path_params": ["table_name"],
                "body": None,
            },
            {
                "id": "dqm-refreshes-list",
                "name": "List Refreshes",
                "method": "GET",
                "path": "/api/2.1/unity-catalog/tables/{table_name}/monitor/refreshes",
                "description": "Lists refresh history for a data quality monitor.",
                "params": [_p("table_name", "Full table name: catalog.schema.table", required=True)],
                "path_params": ["table_name"],
                "body": None,
            },
            {
                "id": "dqm-refresh-get",
                "name": "Get Refresh",
                "method": "GET",
                "path": "/api/2.1/unity-catalog/tables/{table_name}/monitor/refreshes/{refresh_id}",
                "description": "Gets info about a specific refresh for a data quality monitor.",
                "params": [
                    _p("table_name", "Full table name: catalog.schema.table", required=True),
                    _p("refresh_id", "ID of the refresh.", required=True),
                ],
                "path_params": ["table_name", "refresh_id"],
                "body": None,
            },
            {
                "id": "dqm-refresh-cancel",
                "name": "Cancel Refresh",
                "method": "POST",
                "path": "/api/2.1/unity-catalog/tables/{table_name}/monitor/refreshes/{refresh_id}/cancel",
                "description": "Cancels an in-progress refresh for a data quality monitor.",
                "params": [
                    _p("table_name", "Full table name: catalog.schema.table", required=True),
                    _p("refresh_id", "ID of the refresh to cancel.", required=True),
                ],
                "path_params": ["table_name", "refresh_id"],
                "body": None,
            },
            {
                "id": "dqm-dashboard-regenerate",
                "name": "Regenerate Dashboard",
                "method": "POST",
                "path": "/api/2.1/quality-monitoring/tables/{table_name}/monitor/dashboard",
                "description": "Regenerates the monitoring dashboard for a data quality monitor.",
                "params": [_p("table_name", "Full table name: catalog.schema.table", required=True)],
                "path_params": ["table_name"],
                "body": None,
            },
        ],
    },
    "Lakebase Provisioned": {
        "icon": "bi-database-gear",
        "color": "#22d3ee",
        "endpoints": [
            {
                "id": "lakebase-instances-list",
                "name": "List Database Instances",
                "method": "GET",
                "path": "/api/2.0/database/instances",
                "description": "Returns a list of all Lakebase (managed PostgreSQL) database instances in the workspace.",
                "params": [
                    _p("page_size", "Maximum number of results per page.", type_=INT),
                    _p("page_token", "Pagination token for the next page."),
                ],
                "body": None,
            },
            {
                "id": "lakebase-instances-get",
                "name": "Get Database Instance",
                "method": "GET",
                "path": "/api/2.0/database/instances/{name}",
                "description": "Gets details for a single Lakebase database instance.",
                "params": [_p("name", "The instance name.", required=True)],
                "body": None,
                "path_params": ["name"],
            },
            {
                "id": "lakebase-catalogs-get",
                "name": "Get Database Catalog",
                "method": "GET",
                "path": "/api/2.0/database/catalogs/{name}",
                "description": "Gets details for a Lakebase database catalog registered in Unity Catalog.",
                "params": [_p("name", "The catalog name.", required=True)],
                "body": None,
                "path_params": ["name"],
            },
            {
                "id": "lakebase-tables-get",
                "name": "Get Database Table",
                "method": "GET",
                "path": "/api/2.0/database/tables/{name}",
                "description": "Gets details for a Lakebase database table. Name is the full three-part name (catalog.schema.table).",
                "params": [_p("name", "Full three-part table name (catalog.schema.table).", required=True)],
                "body": None,
                "path_params": ["name"],
            },
            {
                "id": "lakebase-synced-tables-get",
                "name": "Get Synced Database Table",
                "method": "GET",
                "path": "/api/2.0/database/synced-tables/{name}",
                "description": "Gets details for a synced database table (reverse ETL from Delta Lake to Lakebase).",
                "params": [_p("name", "Full three-part synced table name (catalog.schema.table).", required=True)],
                "body": None,
                "path_params": ["name"],
            },
            {
                "id": "lakebase-instances-create",
                "name": "Create Database Instance",
                "method": "POST",
                "path": "/api/2.0/database/instances",
                "description": "Creates a new Lakebase database instance.",
                "params": [],
                "body": '{\n  "name": "my-instance",\n  "capacity": "CU_1",\n  "stopped": false\n}',
            },
            {
                "id": "lakebase-instances-update",
                "name": "Update Database Instance",
                "method": "PATCH",
                "path": "/api/2.0/database/instances/{name}",
                "description": "Updates a Lakebase database instance (e.g. capacity, stopped state).",
                "params": [_p("name", "The instance name.", required=True)],
                "body": '{\n  "capacity": "CU_2",\n  "stopped": false\n}',
                "path_params": ["name"],
            },
            {
                "id": "lakebase-instances-delete",
                "name": "Delete Database Instance",
                "method": "DELETE",
                "path": "/api/2.0/database/instances/{name}",
                "description": "Deletes a Lakebase database instance.",
                "params": [
                    _p("name", "The instance name.", required=True),
                    _p("force", "Force delete even if instance has PITR descendants.", type_=BOOL),
                ],
                "body": None,
                "path_params": ["name"],
            },
            {
                "id": "lakebase-credential-generate",
                "name": "Generate Database Credential",
                "method": "POST",
                "path": "/api/2.0/database/credential",
                "description": "Generates an OAuth token for connecting to Lakebase instances (expires after 1 hour).",
                "params": [],
                "body": '{\n  "instance_names": ["my-instance"]\n}',
            },
            {
                "id": "lakebase-catalogs-create",
                "name": "Create Database Catalog",
                "method": "POST",
                "path": "/api/2.0/database/catalogs",
                "description": "Registers a Lakebase database as a Unity Catalog catalog.",
                "params": [],
                "body": '{\n  "name": "my-catalog",\n  "database_instance_name": "my-instance",\n  "database_name": "postgres"\n}',
            },
            {
                "id": "lakebase-catalogs-delete",
                "name": "Delete Database Catalog",
                "method": "DELETE",
                "path": "/api/2.0/database/catalogs/{name}",
                "description": "Deletes a Lakebase database catalog from Unity Catalog.",
                "params": [_p("name", "The catalog name.", required=True)],
                "body": None,
                "path_params": ["name"],
            },
            {
                "id": "lakebase-tables-create",
                "name": "Create Database Table",
                "method": "POST",
                "path": "/api/2.0/database/tables",
                "description": "Registers a pre-existing PostgreSQL table in Unity Catalog.",
                "params": [],
                "body": '{\n  "name": "catalog.schema.table",\n  "database_instance_name": "my-instance",\n  "logical_database_name": "postgres"\n}',
            },
            {
                "id": "lakebase-tables-delete",
                "name": "Delete Database Table",
                "method": "DELETE",
                "path": "/api/2.0/database/tables/{name}",
                "description": "Deletes a Lakebase database table registration from Unity Catalog.",
                "params": [_p("name", "Full three-part table name (catalog.schema.table).", required=True)],
                "body": None,
                "path_params": ["name"],
            },
            {
                "id": "lakebase-synced-tables-create",
                "name": "Create Synced Database Table",
                "method": "POST",
                "path": "/api/2.0/database/synced-tables",
                "description": "Creates a synced table for reverse ETL from a Delta Lake source to Lakebase.",
                "params": [],
                "body": '{\n  "name": "catalog.schema.table",\n  "database_instance_name": "my-instance",\n  "logical_database_name": "postgres"\n}',
            },
            {
                "id": "lakebase-synced-tables-delete",
                "name": "Delete Synced Database Table",
                "method": "DELETE",
                "path": "/api/2.0/database/synced-tables/{name}",
                "description": "Deletes a synced database table.",
                "params": [_p("name", "Full three-part synced table name (catalog.schema.table).", required=True)],
                "body": None,
                "path_params": ["name"],
            },
        ],
    },
    "Lakebase Autoscaling": {
        "icon": "bi-database-add",
        "color": "#06b6d4",
        "endpoints": [
            {
                "id": "pg-projects-list",
                "name": "List Projects",
                "method": "GET",
                "path": "/api/2.0/postgres/projects",
                "description": "Lists all Lakebase Autoscaling projects in the workspace.",
                "params": [
                    _p("page_size", "Maximum number of results per page.", type_=INT),
                    _p("page_token", "Pagination token for the next page."),
                ],
                "body": None,
            },
            {
                "id": "pg-projects-get",
                "name": "Get Project",
                "method": "GET",
                "path": "/api/2.0/postgres/projects/{project_id}",
                "description": "Gets details for a Lakebase Autoscaling project.",
                "params": [_p("project_id", "The project ID (e.g. my-app).", required=True)],
                "body": None,
                "path_params": ["project_id"],
            },
            {
                "id": "pg-projects-create",
                "name": "Create Project",
                "method": "POST",
                "path": "/api/2.0/postgres/projects",
                "description": "Creates a new Lakebase Autoscaling project containing branches and compute endpoints.",
                "params": [_p("project_id", "The project ID (1-63 chars, lowercase, letters/numbers/hyphens).", required=True)],
                "body": '{\n  "status": {\n    "display_name": "my-project",\n    "pg_version": 17\n  }\n}',
            },
            {
                "id": "pg-projects-update",
                "name": "Update Project",
                "method": "PATCH",
                "path": "/api/2.0/postgres/projects/{project_id}",
                "description": "Updates a Lakebase Autoscaling project.",
                "params": [_p("project_id", "The project ID.", required=True)],
                "body": '{\n  "status": {\n    "default_endpoint_settings": {\n      "autoscaling_limit_min_cu": 1,\n      "autoscaling_limit_max_cu": 4\n    }\n  }\n}',
                "path_params": ["project_id"],
            },
            {
                "id": "pg-projects-delete",
                "name": "Delete Project",
                "method": "DELETE",
                "path": "/api/2.0/postgres/projects/{project_id}",
                "description": "Deletes a Lakebase Autoscaling project and all its branches and endpoints.",
                "params": [_p("project_id", "The project ID.", required=True)],
                "body": None,
                "path_params": ["project_id"],
            },
            {
                "id": "pg-branches-list",
                "name": "List Branches",
                "method": "GET",
                "path": "/api/2.0/postgres/projects/{project_id}/branches",
                "description": "Lists all branches in a Lakebase Autoscaling project.",
                "params": [
                    _p("project_id", "The project ID.", required=True),
                    _p("page_size", "Maximum number of results per page.", type_=INT),
                    _p("page_token", "Pagination token for the next page."),
                ],
                "body": None,
                "path_params": ["project_id"],
            },
            {
                "id": "pg-branches-get",
                "name": "Get Branch",
                "method": "GET",
                "path": "/api/2.0/postgres/projects/{project_id}/branches/{branch_id}",
                "description": "Gets details for a branch in a Lakebase Autoscaling project.",
                "params": [
                    _p("project_id", "The project ID.", required=True),
                    _p("branch_id", "The branch ID (e.g. production, dev).", required=True),
                ],
                "body": None,
                "path_params": ["project_id", "branch_id"],
            },
            {
                "id": "pg-branches-create",
                "name": "Create Branch",
                "method": "POST",
                "path": "/api/2.0/postgres/projects/{project_id}/branches",
                "description": "Creates a new branch in a Lakebase Autoscaling project.",
                "params": [
                    _p("project_id", "The project ID.", required=True),
                    _p("branch_id", "The branch ID (1-63 chars, lowercase, letters/numbers/hyphens).", required=True),
                ],
                "body": None,
                "path_params": ["project_id"],
            },
            {
                "id": "pg-branches-update",
                "name": "Update Branch",
                "method": "PATCH",
                "path": "/api/2.0/postgres/projects/{project_id}/branches/{branch_id}",
                "description": "Updates a branch in a Lakebase Autoscaling project.",
                "params": [
                    _p("project_id", "The project ID.", required=True),
                    _p("branch_id", "The branch ID.", required=True),
                ],
                "body": '{\n  "status": {\n    "is_protected": true\n  }\n}',
                "path_params": ["project_id", "branch_id"],
            },
            {
                "id": "pg-branches-delete",
                "name": "Delete Branch",
                "method": "DELETE",
                "path": "/api/2.0/postgres/projects/{project_id}/branches/{branch_id}",
                "description": "Deletes a branch and all its endpoints.",
                "params": [
                    _p("project_id", "The project ID.", required=True),
                    _p("branch_id", "The branch ID.", required=True),
                ],
                "body": None,
                "path_params": ["project_id", "branch_id"],
            },
            {
                "id": "pg-endpoints-list",
                "name": "List Endpoints",
                "method": "GET",
                "path": "/api/2.0/postgres/projects/{project_id}/branches/{branch_id}/endpoints",
                "description": "Lists all compute endpoints in a branch.",
                "params": [
                    _p("project_id", "The project ID.", required=True),
                    _p("branch_id", "The branch ID.", required=True),
                    _p("page_size", "Maximum number of results per page.", type_=INT),
                    _p("page_token", "Pagination token for the next page."),
                ],
                "body": None,
                "path_params": ["project_id", "branch_id"],
            },
            {
                "id": "pg-endpoints-get",
                "name": "Get Endpoint",
                "method": "GET",
                "path": "/api/2.0/postgres/projects/{project_id}/branches/{branch_id}/endpoints/{endpoint_id}",
                "description": "Gets details for a compute endpoint including its host and autoscaling settings.",
                "params": [
                    _p("project_id", "The project ID.", required=True),
                    _p("branch_id", "The branch ID.", required=True),
                    _p("endpoint_id", "The endpoint ID (e.g. primary).", required=True),
                ],
                "body": None,
                "path_params": ["project_id", "branch_id", "endpoint_id"],
            },
            {
                "id": "pg-endpoints-create",
                "name": "Create Endpoint",
                "method": "POST",
                "path": "/api/2.0/postgres/projects/{project_id}/branches/{branch_id}/endpoints",
                "description": "Creates a new compute endpoint in a branch.",
                "params": [
                    _p("project_id", "The project ID.", required=True),
                    _p("branch_id", "The branch ID.", required=True),
                    _p("endpoint_id", "The endpoint ID (1-63 chars, lowercase, letters/numbers/hyphens).", required=True),
                ],
                "body": '{\n  "status": {\n    "autoscaling_limit_min_cu": 1,\n    "autoscaling_limit_max_cu": 4,\n    "suspend_timeout_duration": "300s"\n  }\n}',
                "path_params": ["project_id", "branch_id"],
            },
            {
                "id": "pg-endpoints-update",
                "name": "Update Endpoint",
                "method": "PATCH",
                "path": "/api/2.0/postgres/projects/{project_id}/branches/{branch_id}/endpoints/{endpoint_id}",
                "description": "Updates a compute endpoint's settings (autoscaling, suspend timeout, etc.).",
                "params": [
                    _p("project_id", "The project ID.", required=True),
                    _p("branch_id", "The branch ID.", required=True),
                    _p("endpoint_id", "The endpoint ID.", required=True),
                ],
                "body": '{\n  "status": {\n    "autoscaling_limit_min_cu": 2,\n    "autoscaling_limit_max_cu": 8,\n    "suspend_timeout_duration": "600s"\n  }\n}',
                "path_params": ["project_id", "branch_id", "endpoint_id"],
            },
            {
                "id": "pg-endpoints-delete",
                "name": "Delete Endpoint",
                "method": "DELETE",
                "path": "/api/2.0/postgres/projects/{project_id}/branches/{branch_id}/endpoints/{endpoint_id}",
                "description": "Deletes a compute endpoint.",
                "params": [
                    _p("project_id", "The project ID.", required=True),
                    _p("branch_id", "The branch ID.", required=True),
                    _p("endpoint_id", "The endpoint ID.", required=True),
                ],
                "body": None,
                "path_params": ["project_id", "branch_id", "endpoint_id"],
            },
            {
                "id": "pg-credential-generate",
                "name": "Generate Credential",
                "method": "POST",
                "path": "/api/2.0/postgres/credentials",
                "description": "Generates OAuth credentials for connecting to a Lakebase Autoscaling Postgres database.",
                "params": [_p("endpoint", "Endpoint resource name (projects/{id}/branches/{id}/endpoints/{id}).")],
                "body": None,
            },
            {
                "id": "pg-operations-get",
                "name": "Get Operation",
                "method": "GET",
                "path": "/api/2.0/postgres/projects/{project_id}/operations/{operation_id}",
                "description": "Retrieves the status of a long-running operation (create, update, delete).",
                "params": [
                    _p("project_id", "The project ID.", required=True),
                    _p("operation_id", "The operation ID.", required=True),
                ],
                "body": None,
                "path_params": ["project_id", "operation_id"],
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
                                      ("policies-get-compliance", "bi-patch-check", "Get Cluster Compliance", {"cluster_id": "cluster_id"}),
                                      ("_cmd_execute_nav", "bi-terminal", "Run Command on this cluster", {"clusterId": "cluster_id"}),
                                  ]),
    "jobs-list":                  ("jobs-get",               "jobs",           "job_id",        "job_id",        "settings.name", None, [
                                      ("permissions-jobs-get", "bi-shield-check", "Get Job Permissions", {"job_id": "job_id"}),
                                      ("jobs-get-compliance", "bi-patch-check", "Get Job Compliance", {"job_id": "job_id"}),
                                      ("jobs-runs-list", "bi-list-ul", "List Runs for this Job", {"job_id": "job_id"}),
                                  ]),
    "jobs-list-21":               ("jobs-get-21",            "jobs",           "job_id",        "job_id",        "settings.name"),
    "jobs-runs-list":             ("jobs-runs-get",          "runs",           "run_id",        "run_id",        None, None, [
                                      ("jobs-runs-get-output", "bi-file-earmark-text", "Get Run Output", {"run_id": "run_id"}),
                                  ]),
    "jobs-runs-list-21":          ("jobs-runs-get-21",       "runs",           "run_id",        "run_id",        None),
    "jobs-list-compliance":       ("jobs-get-compliance",    "jobs",           "job_id",        "job_id",        None, None, [
                                      ("jobs-get", "bi-briefcase", "Get Job", {"job_id": "job_id"}),
                                  ]),
    "sql-warehouses-list":        ("sql-warehouses-get",     "warehouses",     "id",            "id",            "name", None, [
                                      ("permissions-warehouses-get", "bi-shield-check", "Get Warehouse Permissions", {"warehouse_id": "id"}),
                                  ]),
    "uc-catalogs-list":           ("uc-schemas-list",        "catalogs",       "name",          "catalog_name",  None),
    "uc-schemas-list":            ("uc-tables-list",         "schemas",        "name",          "schema_name",   None, {"catalog_name": "catalog_name"}, [
                                      ("uc-volumes-list", "bi-archive", "List Volumes", {"catalog_name": "catalog_name", "schema_name": "name"}),
                                  ]),
    "uc-tables-list":             ("uc-tables-get",          "tables",         "full_name",     "full_name",     "name", None, [
                                      ("_sql_select_star", "bi-play-circle", "SELECT * FROM this table", {"full_name": "full_name"}),
                                      ("dqm-monitor-get", "bi-clipboard-check", "Get Data Quality Monitor", {"table_name": "full_name"}),
                                      ("dqm-refreshes-list", "bi-arrow-repeat", "List Data Quality Monitor Refreshes", {"table_name": "full_name"}),
                                  ]),
    "mlflow-experiments-search":  ("mlflow-experiments-get", "experiments",    "experiment_id", "experiment_id", "name", None, [
                                      ("mlflow-runs-search", "bi-list-ul", "Search Runs", {"experiment_id": "experiment_id"}),
                                      ("trace-search", "bi-bezier", "Search Traces", {"locations[0].mlflow_experiment.experiment_id": "experiment_id"}),
                                  ]),
    "trace-search":               ("trace-get-info",         "traces",         "trace_id",      "trace_id",      "request_preview", None, [
                                      ("trace-set-tag", "bi-tag", "Set Tag", {"trace_id": "trace_id"}),
                                      ("trace-assessment-create", "bi-chat-quote", "Create Assessment", {"trace_id": "trace_id"}),
                                      ("trace-credentials-download", "bi-cloud-download", "Get Download Credentials", {"trace_id": "trace_id"}),
                                  ]),
    "serving-endpoints-list":     ("serving-endpoints-get",  "endpoints",      "name",          "name",          None),
    "pipelines-list":             ("pipelines-get",          "statuses",       "pipeline_id",   "pipeline_id",   "name", None, [
                                      ("pipelines-events", "bi-journal-text", "List Pipeline Events", {"pipeline_id": "pipeline_id"}),
                                      ("pipelines-list-updates", "bi-arrow-repeat", "List Pipeline Updates", {"pipeline_id": "pipeline_id"}),
                                  ]),
    "pipelines-list-updates":     ("pipelines-get-update",   "updates",        "update_id",     "update_id",     None, {"pipeline_id": "pipeline_id"}),
    "git-credentials-list":       ("git-credentials-get",    "credentials",    "credential_id", "credential_id", "git_provider"),
    "instance-pools-list":        ("instance-pools-get",     "instance_pools", "instance_pool_id", "instance_pool_id", "instance_pool_name"),
    "libraries-all-cluster-statuses": ("libraries-cluster-status", "statuses",   "cluster_id",    "cluster_id",    None, None, [
                                      ("clusters-get", "bi-cpu", "Get Cluster", {"cluster_id": "cluster_id"}),
                                  ]),
    "policies-list":              ("policies-list-compliance", "policies",    "policy_id",     "policy_id",     "name"),
    "policies-list-compliance":   ("policies-get-compliance", "clusters",    "cluster_id",    "cluster_id",    None, None, [
                                      ("clusters-get", "bi-cpu", "Get Cluster", {"cluster_id": "cluster_id"}),
                                  ]),
    "policy-families-list":       ("policy-families-get",    "policy_families", "policy_family_id", "policy_family_id", "name"),
    "global-init-scripts-list":   ("global-init-scripts-get", "scripts",       "script_id",     "script_id",     "name"),
    "secrets-list-scopes":        ("secrets-list",           "scopes",         "name",          "scope",         None),
    "uc-volumes-list":            ("files-list-directory-contents", "volumes", "name",         "directory_path", "full_name", None, None, "/Volumes/{catalog_name}/{schema_name}/{name}"),
    "dbfs-list":                  ("dbfs-get-status",        "files",          "path",          "path",          None),
    "files-list-directory-contents": ("files-download",       "contents",       "path",          "file_path",     "name", None, [
                                      ("files-get-metadata", "bi-info-circle", "Get File Metadata", {"file_path": "path"}),
                                  ]),
    "workspace-list":             ("workspace-get-status",   "objects",        "path",          "path",          None),
    "lakebase-instances-list":    ("lakebase-instances-get", "database_instances", "name",      "name",          None),
    "pg-branches-list":           ("pg-branches-get",        "branches",           "@name",               "branch_id",  None, {"project_id": "@parent"}, [
                                      ("pg-endpoints-list", "bi-hdd-network", "List Endpoints", {"project_id": "@parent", "branch_id": "@name"}),
                                  ]),
    "pg-endpoints-list":          ("pg-endpoints-get",       "endpoints",          "@name",               "endpoint_id", None, {"project_id": "@@parent", "branch_id": "@parent"}),
    "pg-projects-list":           ("pg-projects-get",        "projects",           "@name",               "project_id", None, None, [
                                      ("pg-branches-list", "bi-diagram-2", "List Branches", {"project_id": "@name"}),
                                  ]),
    "dqm-refreshes-list":         ("dqm-refresh-get",        "refreshes",      "refresh_id",    "refresh_id",    None),
}


# ── Command Execution API Catalog ─────────────────────────────────────────────
# Legacy 1.2 API for running commands on a cluster. Two entities:
#   - Execution Contexts (attached to a cluster, scoped to a language)
#   - Commands (run within a context)
# Docs: https://docs.databricks.com/api/workspace/commandexecution


COMMAND_API_CATALOG: Dict[str, Any] = {
    "Execution Contexts": {
        "icon": "bi-terminal",
        "color": "#f59e0b",
        "endpoints": [
            {
                "id": "cmd-context-create",
                "name": "Create Context",
                "method": "POST",
                "path": "/api/1.2/contexts/create",
                "description": "Creates an execution context on a cluster for a specific language.",
                "params": [],
                "body": '{\n  "clusterId": "",\n  "language": "python"\n}',
            },
            {
                "id": "cmd-context-status",
                "name": "Get Context Status",
                "method": "GET",
                "path": "/api/1.2/contexts/status",
                "description": "Gets the status of an execution context.",
                "params": [
                    _p("clusterId", "The cluster the context is attached to.", required=True),
                    _p("contextId", "The execution context ID.", required=True),
                ],
                "body": None,
            },
            {
                "id": "cmd-context-destroy",
                "name": "Destroy Context",
                "method": "POST",
                "path": "/api/1.2/contexts/destroy",
                "description": "Destroys an execution context on a cluster.",
                "params": [],
                "body": '{\n  "clusterId": "",\n  "contextId": ""\n}',
            },
        ],
    },
    "Commands": {
        "icon": "bi-play-btn",
        "color": "#f59e0b",
        "endpoints": [
            {
                "id": "cmd-execute",
                "name": "Run Command",
                "method": "POST",
                "path": "/api/1.2/commands/execute",
                "description": "Runs a command (or file) in an execution context. Use multipart/form-data when uploading a file.",
                "params": [],
                "body": '{\n  "clusterId": "",\n  "contextId": "",\n  "language": "python",\n  "command": "print(\\"hello\\")"\n}',
            },
            {
                "id": "cmd-status",
                "name": "Get Command Status",
                "method": "GET",
                "path": "/api/1.2/commands/status",
                "description": "Gets the status of a command, including any results once it completes.",
                "params": [
                    _p("clusterId", "The cluster the command is running on.", required=True),
                    _p("contextId", "The execution context ID.", required=True),
                    _p("commandId", "The command ID.", required=True),
                ],
                "body": None,
            },
            {
                "id": "cmd-cancel",
                "name": "Cancel Command",
                "method": "POST",
                "path": "/api/1.2/commands/cancel",
                "description": "Cancels a running command.",
                "params": [],
                "body": '{\n  "clusterId": "",\n  "contextId": "",\n  "commandId": ""\n}',
            },
        ],
    },
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
    value_template = mapping[7] if len(mapping) > 7 else None
    if not get_id or not param_name:
        return []
    # "@field" means: use field, but take only the last path segment as the value
    strip_prefix = id_field.startswith("@")
    if strip_prefix:
        id_field = id_field[1:]
    # list_key=None means the response is a bare array
    if list_key is None:
        items = data if isinstance(data, list) else []
    else:
        items = data.get(list_key, []) if isinstance(data, dict) else []
    if not isinstance(items, list):
        return []
    chips = []
    for item in items[:60]:
        value = _nested_get(item, id_field) if "." in id_field else item.get(id_field)
        if value is None:
            continue
        if strip_prefix and isinstance(value, str) and "/" in value:
            value = value.rsplit("/", 1)[-1]
        if value_template and isinstance(item, dict):
            try:
                value = value_template.format_map(item)
            except (KeyError, IndexError, ValueError):
                continue
        label = _nested_get(item, label_field) if label_field else None
        label = str(label) if label else str(value)
        if label != str(value):
            label = f"{label}"   # show name only; value accessible via title
        extras = {}
        if extra_params:
            for target_param, source_field in extra_params.items():
                sf_grandparent = source_field.startswith("@@")
                sf_strip = source_field.startswith("@") and not sf_grandparent
                sf_key = source_field[2:] if sf_grandparent else (source_field[1:] if sf_strip else source_field)
                v = _nested_get(item, sf_key) if "." in sf_key else item.get(sf_key)
                if v is not None:
                    v = str(v)
                    if sf_grandparent and "/" in v:
                        parts = v.split("/")
                        v = "/".join(parts[:-2]).rsplit("/", 1)[-1] if len(parts) > 2 else v
                    elif sf_strip and "/" in v:
                        v = v.rsplit("/", 1)[-1]
                    extras[target_param] = v
        actions = []
        if actions_def:
            for act_id, act_icon, act_title, act_params in actions_def:
                act_p = {}
                for tp, sf in act_params.items():
                    sf_gp = sf.startswith("@@")
                    sf_strip = sf.startswith("@") and not sf_gp
                    sf_key = sf[2:] if sf_gp else (sf[1:] if sf_strip else sf)
                    v = _nested_get(item, sf_key) if "." in sf_key else item.get(sf_key)
                    if v is not None:
                        v = str(v)
                        if sf_gp and "/" in v:
                            parts = v.split("/")
                            v = "/".join(parts[:-2]).rsplit("/", 1)[-1] if len(parts) > 2 else v
                        elif sf_strip and "/" in v:
                            v = v.rsplit("/", 1)[-1]
                        act_p[tp] = v
                actions.append({"gid": act_id, "icon": act_icon, "title": act_title, "params": act_p})
        chip = {
            "get_id":   get_id,
            "param":    param_name,
            "id_field": id_field.rsplit(".", 1)[-1] if "." in id_field else id_field,
            "value":    str(value),
            "label":    label[:60],
            "title":    str(value),
            "extras":   extras,
            "actions":  actions,
        }
        if endpoint_id == "clusters-list":
            chip["state"] = item.get("state")
        if endpoint_id == "files-list-directory-contents":
            if item.get("is_directory") is True:
                chip["get_id"] = "files-list-directory-contents"
                chip["param"] = "directory_path"
                chip["actions"] = [{
                    "gid": "files-get-directory-metadata",
                    "icon": "bi-info-circle",
                    "title": "Get Directory Metadata",
                    "params": {"directory_path": str(item.get("path", ""))},
                }]
            else:
                chip["get_id"] = "files-download"
                chip["param"] = "file_path"
        chips.append(chip)
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
    for catalog, scope in ((API_CATALOG, "workspace"), (ACCOUNT_API_CATALOG, "account"), (COMMAND_API_CATALOG, "commands")):
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
    for catalog, scope in ((API_CATALOG, "workspace"), (ACCOUNT_API_CATALOG, "account"), (COMMAND_API_CATALOG, "commands")):
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
TOTAL_COMMAND_ENDPOINTS: int = sum(len(c["endpoints"]) for c in COMMAND_API_CATALOG.values())
TOTAL_COMMAND_CATEGORIES: int = len(COMMAND_API_CATALOG)


# ── API Documentation URL map ────────────────────────────────────────────────
# Maps endpoint IDs to their path on https://docs.databricks.com/api/
# Pattern: {scope}/{service}/{operation}
_DOCS_BASE = "https://docs.databricks.com/api"
_CLOUD_PREFIXES = {"aws": "aws/", "azure": "azure/", "gcp": "gcp/"}

# Maps category names → docs service path (without scope prefix).
# Used for linking category headings to the API group overview page.
CATEGORY_DOCS_MAP: Dict[str, str] = {
    # Workspace
    "Clusters":            "workspace/clusters",
    "Lakeflow":            "workspace/jobs",
    "Workspace":           "workspace/workspace",
    "DBFS":                "workspace/dbfs",
    "Files":               "workspace/files",
    "SQL Warehouses":      "workspace/warehouses",
    "Unity Catalog":       "workspace/catalogs",
    "MLflow":              "workspace/experiments",
    "Experiments Tracing": "workspace/mlflowexperimenttrace",
    "Model Serving":       "workspace/servingendpoints",
    "Secrets":             "workspace/secrets",
    "Identity (SCIM)":     "workspace/users",
    "Tokens":              "workspace/tokenmanagement",
    "Instance Pools":      "workspace/instancepools",
    "Instance Profiles":   "workspace/instanceprofiles",
    "Cluster Policies":    "workspace/clusterpolicies",
    "Libraries":           "workspace/libraries",
    "Repos":               "workspace/repos",
    "Git Credentials":     "workspace/gitcredentials",
    "Global Init Scripts": "workspace/globalinitscripts",
    "Permissions":         "workspace/permissions",
    "Data Quality Monitoring": "workspace/dataquality",
    "Execution Contexts":  "workspace/commandexecution",
    "Commands":            "workspace/commandexecution",
    # Account
    "Account Users":       "account/accountusers",
    "Account Groups":      "account/accountgroups",
    "Service Principals":  "account/serviceprincipals",
    "Workspaces":          "account/workspaces",
    "Credentials":         "account/credentials",
    "Storage":             "account/storageconfigurations",
    "Networks":            "account/networkconfigurations",
    "Private Access":      "account/privateaccesssettings",
    "VPC Endpoints":       "account/vpcendpoints",
    "Encryption Keys":     "account/encryptionkeys",
    "Log Delivery":        "account/logdelivery",
    "Budgets":             "account/budgets",
    "Usage Download":      "account/billableusage",
    "Account Metastores":  "account/accountmetastores",
    "Account Access Control": "account/accountaccesscontrol",
    "Account Settings":    "account/accountsettings",
}

DOCS_URL_MAP: Dict[str, str] = {
    # Workspace — Clusters
    "clusters-list":             "workspace/clusters/list",
    "clusters-get":              "workspace/clusters/get",
    "clusters-list-node-types":  "workspace/clusters/listnodetype",
    "clusters-spark-versions":   "workspace/clusters/sparkversions",
    "clusters-events":           "workspace/clusters/events",
    # Workspace — Jobs
    "jobs-list":                 "workspace/jobs/list",
    "jobs-get":                  "workspace/jobs/get",
    "jobs-create":               "workspace/jobs/create",
    "jobs-update":               "workspace/jobs/update",
    "jobs-reset":                "workspace/jobs/reset",
    "jobs-delete":               "workspace/jobs/delete",
    "jobs-run-now":              "workspace/jobs/runnow",
    "jobs-runs-submit":          "workspace/jobs/submit",
    "jobs-runs-list":            "workspace/jobs/listruns",
    "jobs-runs-get":             "workspace/jobs/getrun",
    "jobs-runs-get-output":      "workspace/jobs/getrunoutput",
    "jobs-runs-export":          "workspace/jobs/exportrun",
    "jobs-runs-cancel":          "workspace/jobs/cancelrun",
    "jobs-runs-cancel-all":      "workspace/jobs/cancelallruns",
    "jobs-runs-delete":          "workspace/jobs/deleterun",
    "jobs-runs-repair":          "workspace/jobs/repairrun",
    "jobs-list-21":              "workspace/jobs_21/list",
    "jobs-get-21":               "workspace/jobs_21/get",
    "jobs-runs-list-21":         "workspace/jobs_21/listruns",
    "jobs-runs-get-21":          "workspace/jobs_21/getrun",
    "jobs-list-compliance":      "workspace/policycomplianceforjobs/listcompliance",
    "jobs-get-compliance":       "workspace/policycomplianceforjobs/getcompliance",
    "jobs-enforce-compliance":   "workspace/policycomplianceforjobs/enforcecompliance",
    # Workspace — Workspace
    "workspace-list":            "workspace/workspace/list",
    "workspace-get-status":      "workspace/workspace/getstatus",
    # Workspace — DBFS
    "dbfs-list":                 "workspace/dbfs/list",
    "dbfs-get-status":           "workspace/dbfs/getstatus",
    "dbfs-read":                 "workspace/dbfs/read",
    "dbfs-create":               "workspace/dbfs/create",
    "dbfs-add-block":            "workspace/dbfs/addblock",
    "dbfs-close":                "workspace/dbfs/close",
    "dbfs-put":                  "workspace/dbfs/put",
    "dbfs-mkdirs":               "workspace/dbfs/mkdirs",
    "dbfs-move":                 "workspace/dbfs/move",
    "dbfs-delete":               "workspace/dbfs/delete",
    # Workspace — Files (UC Volumes)
    "files-list-directory-contents": "workspace/files/listdirectorycontents",
    "files-get-directory-metadata":  "workspace/files/getdirectorymetadata",
    "files-create-directory":        "workspace/files/createdirectory",
    "files-delete-directory":        "workspace/files/deletedirectory",
    "files-get-metadata":            "workspace/files/getmetadata",
    "files-download":                "workspace/files/download",
    "files-upload":                  "workspace/files/upload",
    "files-delete":                  "workspace/files/delete",
    # Workspace — SQL Warehouses
    "sql-warehouses-list":       "workspace/warehouses/list",
    "sql-warehouses-get":        "workspace/warehouses/get",
    "sql-queries-list":          "workspace/queries/list",
    # Workspace — Unity Catalog
    "uc-catalogs-list":          "workspace/catalogs/list",
    "uc-schemas-list":           "workspace/schemas/list",
    "uc-tables-list":            "workspace/tables/list",
    "uc-tables-get":             "workspace/tables/get",
    "uc-volumes-list":           "workspace/volumes/list",
    "uc-metastore-get":          "workspace/metastores/summary",
    # Workspace — MLflow
    "mlflow-experiments-search":        "workspace/experiments/searchexperiments",
    "mlflow-experiments-get":           "workspace/experiments/getexperiment",
    "mlflow-runs-search":               "workspace/experiments/searchruns",
    "mlflow-registered-models-search":  "workspace/modelregistry/searchregisteredmodels",
    # Workspace — Experiments Tracing
    "trace-search":                     "workspace/mlflowexperimenttrace/searchtracesv3",
    "trace-get-info":                   "workspace/mlflowexperimenttrace/gettraceinfov3",
    "trace-start":                      "workspace/mlflowexperimenttrace/starttracev3",
    "trace-end":                        "workspace/mlflowexperimenttrace/endtracev3",
    "trace-delete-batch":               "workspace/mlflowexperimenttrace/deletetracesv3",
    "trace-set-tag":                    "workspace/mlflowexperimenttrace/settracetagv3",
    "trace-delete-tag":                 "workspace/mlflowexperimenttrace/deletetracetagv3",
    "trace-assessment-create":          "workspace/mlflowexperimenttrace/createassessmentv3",
    "trace-assessment-get":             "workspace/mlflowexperimenttrace/getassessmentv3",
    "trace-assessment-update":          "workspace/mlflowexperimenttrace/updateassessmentv3",
    "trace-assessment-delete":          "workspace/mlflowexperimenttrace/deleteassessmentv3",
    "trace-credentials-download":       "workspace/mlflowexperimenttrace/getcredentialsfortracedatadownload",
    "trace-credentials-upload":         "workspace/mlflowexperimenttrace/getcredentialsfortracedataupload",
    # Workspace — Model Serving
    "serving-endpoints-list":    "workspace/servingendpoints/list",
    "serving-endpoints-get":     "workspace/servingendpoints/get",
    # Workspace — Pipelines (DLT)
    "pipelines-list":            "workspace/pipelines/listpipelines",
    "pipelines-get":             "workspace/pipelines/getpipeline",
    "pipelines-create":          "workspace/pipelines/createpipeline",
    "pipelines-edit":            "workspace/pipelines/editpipeline",
    "pipelines-delete":          "workspace/pipelines/deletepipeline",
    "pipelines-stop":            "workspace/pipelines/stoppipeline",
    "pipelines-start-update":    "workspace/pipelines/startupdate",
    "pipelines-list-updates":    "workspace/pipelines/listupdates",
    "pipelines-get-update":      "workspace/pipelines/getupdate",
    "pipelines-events":          "workspace/pipelines/listpipelineevents",
    # Workspace — Secrets
    "secrets-list-scopes":       "workspace/secrets/listscopes",
    "secrets-list":              "workspace/secrets/listsecrets",
    # Workspace — Identity (SCIM)
    "scim-me":                   "workspace/currentuser/me",
    "scim-users-list":           "workspace/users/list",
    "scim-groups-list":          "workspace/groups/list",
    "scim-service-principals-list": "workspace/serviceprincipals/list",
    # Workspace — Tokens
    "tokens-list":               "workspace/tokenmanagement/list",
    # Workspace — Instance Pools
    "instance-pools-list":                "workspace/instancepools/list",
    "instance-pools-get":                 "workspace/instancepools/get",
    "instance-pools-create":              "workspace/instancepools/create",
    "instance-pools-edit":                "workspace/instancepools/edit",
    "instance-pools-delete":              "workspace/instancepools/delete",
    "instance-pools-permission-levels":   "workspace/instancepools/getinstancepoolpermissionlevels",
    "instance-pools-permissions-get":     "workspace/instancepools/getinstancepoolpermissions",
    "instance-pools-permissions-set":     "workspace/instancepools/setinstancepoolpermissions",
    "instance-pools-permissions-update":  "workspace/instancepools/updateinstancepoolpermissions",
    # Workspace — Instance Profiles
    "instance-profiles-list":             "workspace/instanceprofiles/list",
    "instance-profiles-add":              "workspace/instanceprofiles/add",
    "instance-profiles-edit":             "workspace/instanceprofiles/edit",
    "instance-profiles-remove":           "workspace/instanceprofiles/remove",
    # Workspace — Cluster Policies
    "policies-list":             "workspace/clusterpolicies/list",
    # Workspace — Policy Compliance for Clusters
    "policies-list-compliance":    "workspace/policycomplianceforclusters/listcompliance",
    "policies-get-compliance":     "workspace/policycomplianceforclusters/getcompliance",
    "policies-enforce-compliance": "workspace/policycomplianceforclusters/enforcecompliance",
    # Workspace — Policy Families
    "policy-families-list":      "workspace/policyfamilies/list",
    "policy-families-get":       "workspace/policyfamilies/get",
    # Workspace — Libraries
    "libraries-all-cluster-statuses": "workspace/libraries/allclusterstatuses",
    "libraries-cluster-status":       "workspace/libraries/clusterstatus",
    "libraries-install":              "workspace/libraries/install",
    "libraries-uninstall":            "workspace/libraries/uninstall",
    # Workspace — Repos
    "repos-list":                "workspace/repos/list",
    # Workspace — Permissions
    # Workspace — Git Credentials
    "git-credentials-list":        "workspace/gitcredentials/list",
    "git-credentials-get":         "workspace/gitcredentials/get",
    "git-credentials-create":      "workspace/gitcredentials/create",
    "git-credentials-update":      "workspace/gitcredentials/update",
    "git-credentials-delete":      "workspace/gitcredentials/delete",
    # Workspace — Global Init Scripts
    "global-init-scripts-list":    "workspace/globalinitscripts/list",
    "global-init-scripts-get":     "workspace/globalinitscripts/get",
    "global-init-scripts-create":  "workspace/globalinitscripts/create",
    "global-init-scripts-update":  "workspace/globalinitscripts/update",
    "global-init-scripts-delete":  "workspace/globalinitscripts/delete",
    # Workspace — Permissions
    "permissions-clusters-get":    "workspace/permissions/getobjectpermissions",
    "permissions-jobs-get":        "workspace/permissions/getobjectpermissions",
    "permissions-warehouses-get":  "workspace/permissions/getobjectpermissions",
    # Workspace — Data Quality Monitoring
    "dqm-monitor-create":        "workspace/dataquality/create",
    "dqm-monitor-get":           "workspace/dataquality/get",
    "dqm-monitor-update":        "workspace/dataquality/update",
    "dqm-monitor-delete":        "workspace/dataquality/delete",
    "dqm-refreshes-run":         "workspace/dataquality/runrefresh",
    "dqm-refreshes-list":        "workspace/dataquality/listrefreshes",
    "dqm-refresh-get":           "workspace/dataquality/getrefresh",
    "dqm-refresh-cancel":        "workspace/dataquality/cancelrefresh",
    "dqm-dashboard-regenerate":  "workspace/dataquality/regeneratedashboard",
    # Account — Users
    "acct-users-list":           "account/accountusers/list",
    "acct-users-get":            "account/accountusers/get",
    # Account — Groups
    "acct-groups-list":          "account/accountgroups/list",
    "acct-groups-get":           "account/accountgroups/get",
    # Account — Service Principals
    "acct-sp-list":              "account/serviceprincipals/list",
    "acct-sp-get":               "account/serviceprincipals/get",
    # Account — Workspaces
    "acct-workspaces-list":      "account/workspaces/list",
    "acct-workspaces-get":       "account/workspaces/get",
    # Account — Credentials
    "acct-credentials-list":     "account/credentials/list",
    "acct-credentials-get":      "account/credentials/get",
    # Account — Storage
    "acct-storage-list":         "account/storageconfigurations/list",
    "acct-storage-get":          "account/storageconfigurations/get",
    # Account — Networks
    "acct-networks-list":        "account/networkconfigurations/list",
    "acct-networks-get":         "account/networkconfigurations/get",
    # Account — Private Access
    "acct-private-access-list":  "account/privateaccesssettings/list",
    "acct-private-access-get":   "account/privateaccesssettings/get",
    # Account — VPC Endpoints
    "acct-vpc-endpoints-list":   "account/vpcendpoints/list",
    "acct-vpc-endpoints-get":    "account/vpcendpoints/get",
    # Account — Encryption Keys
    "acct-keys-list":            "account/encryptionkeys/list",
    "acct-keys-get":             "account/encryptionkeys/get",
    # Account — Log Delivery
    "acct-log-delivery-list":    "account/logdelivery/list",
    "acct-log-delivery-get":     "account/logdelivery/get",
    # Account — Budgets
    "acct-budgets-list":         "account/budgets/list",
    "acct-budgets-get":          "account/budgets/get",
    # Account — Usage Download
    "acct-usage-download":       "account/billableusage/download",
    # Account — Metastores
    "acct-metastores-list":              "account/accountmetastores/list",
    "acct-metastores-get":               "account/accountmetastores/get",
    "acct-metastore-assignments-list":   "account/accountmetastoreassignments/list",
    # Account — Access Control
    "acct-ruleset-get":          "account/accountaccesscontrol/getruleset",
    # Account — Settings
    "acct-settings-personal-compute": "account/cspenablement/get",
    "acct-settings-ip-access-list":   "account/accountipaccesslists/list",
    # Command Execution
    "cmd-context-create":        "workspace/commandexecution/create",
    "cmd-context-status":        "workspace/commandexecution/contextstatus",
    "cmd-context-destroy":       "workspace/commandexecution/destroy",
    "cmd-execute":               "workspace/commandexecution/execute",
    "cmd-status":                "workspace/commandexecution/commandstatus",
    "cmd-cancel":                "workspace/commandexecution/cancel",
}


def get_doc_url(endpoint_id: str, cloud: Optional[str] = None) -> Optional[str]:
    """Return the Databricks API documentation URL for an endpoint.

    Args:
        endpoint_id: The endpoint ``id`` (e.g. ``"clusters-list"``).
        cloud: Optional cloud provider (``"aws"``, ``"azure"``, or
            ``"gcp"``).  When set the URL includes the cloud prefix
            so the docs site shows the correct cloud variant.

    Returns:
        The full docs URL, or ``None`` if no mapping exists.
    """
    path = DOCS_URL_MAP.get(endpoint_id)
    if not path:
        return None
    prefix = _CLOUD_PREFIXES.get(cloud, "")
    return f"{_DOCS_BASE}/{prefix}{path}"


def get_category_doc_url(category_name: str, cloud: Optional[str] = None) -> Optional[str]:
    """Return the Databricks API documentation URL for a category.

    Args:
        category_name: The display name of the category (e.g.
            ``"Clusters"``).
        cloud: Optional cloud provider (``"aws"``, ``"azure"``, or
            ``"gcp"``).

    Returns:
        The full docs URL, or ``None`` if no mapping exists.
    """
    path = CATEGORY_DOCS_MAP.get(category_name)
    if not path:
        return None
    prefix = _CLOUD_PREFIXES.get(cloud, "")
    return f"{_DOCS_BASE}/{prefix}{path}"


def detect_cloud(host: str) -> Optional[str]:
    """Detect the cloud provider from a Databricks workspace host URL.

    Args:
        host: The workspace URL (e.g.
            ``"https://adb-123.azuredatabricks.net"``).

    Returns:
        ``"aws"``, ``"azure"``, ``"gcp"``, or ``None`` if unknown.
    """
    h = (host or "").lower()
    if "azuredatabricks" in h:
        return "azure"
    if ".gcp.databricks.com" in h:
        return "gcp"
    if "databricks.com" in h or "cloud.databricks" in h:
        return "aws"
    return None
