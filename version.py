"""Auto-incrementing build version.

In local mode the patch number stored in ``version.txt`` is
incremented on every ``import version`` (i.e. every app start/reload).
In Databricks App mode the committed value is used as-is so the
displayed version reliably reflects the deployed code.

Attributes:
    BUILD: Current integer build number.
    VERSION: Semantic-version string in the form ``v0.4.<BUILD>``.
"""

import os

_VERSION_FILE = os.path.join(os.path.dirname(__file__), "version.txt")
_IS_APP = bool(os.getenv("DATABRICKS_CLIENT_SECRET"))


def _next_version() -> int:
    """Read the current build number from disk, bump it, and persist.

    In Databricks App mode the file is read-only (no increment) so the
    version matches the committed value exactly.

    Returns:
        The current (App mode) or new (local mode) build number.
    """
    try:
        with open(_VERSION_FILE) as f:
            v = int(f.read().strip())
    except (FileNotFoundError, ValueError):
        v = 0
    if _IS_APP:
        return v
    v += 1
    with open(_VERSION_FILE, "w") as f:
        f.write(str(v))
    return v


BUILD: int = _next_version()
VERSION: str = f"v0.4.{BUILD}"
