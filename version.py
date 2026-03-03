"""Auto-incrementing build version — increments on every app start."""
import os

_VERSION_FILE = os.path.join(os.path.dirname(__file__), "version.txt")


def _next_version() -> int:
    try:
        with open(_VERSION_FILE) as f:
            v = int(f.read().strip())
    except (FileNotFoundError, ValueError):
        v = 0
    v += 1
    with open(_VERSION_FILE, "w") as f:
        f.write(str(v))
    return v


BUILD = _next_version()
VERSION = f"v{BUILD}"
