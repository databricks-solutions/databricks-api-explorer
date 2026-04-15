"""Auto-incrementing build version.

Increments the patch number stored in ``version.txt`` on every
``import version`` (i.e. every app start).  The file is co-located
with this module.

Attributes:
    BUILD: Current integer build number.
    VERSION: Semantic-version string in the form ``v0.4.<BUILD>``.
"""

import os

_VERSION_FILE = os.path.join(os.path.dirname(__file__), "version.txt")


def _next_version() -> int:
    """Read the current build number from disk, bump it, and persist.

    Returns:
        The new (incremented) build number.
    """
    try:
        with open(_VERSION_FILE) as f:
            v = int(f.read().strip())
    except (FileNotFoundError, ValueError):
        v = 0
    v += 1
    with open(_VERSION_FILE, "w") as f:
        f.write(str(v))
    return v


BUILD: int = _next_version()
VERSION: str = f"v0.4.{BUILD}"
