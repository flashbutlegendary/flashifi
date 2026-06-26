"""Application version metadata.

``APP_VERSION`` follows `Semantic Versioning 2.0
<https://semver.org/>`_.  ``BUILD_DATE`` is captured at import time so
it reflects the moment the application was loaded (useful for container
images that embed version info at build time).
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone

APP_VERSION: str = "1.0.0"
"""Current semantic version of the FlashiFi application."""

BUILD_DATE: str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
"""ISO-8601 UTC timestamp captured when this module was first imported."""


def get_git_commit() -> str | None:
    """Return the abbreviated Git commit hash of the current HEAD.

    The function shells out to ``git rev-parse --short HEAD``.  If Git is
    not installed, the repository is absent, or the subprocess times out,
    ``None`` is returned silently — version reporting should never crash
    the application.

    Returns
    -------
    str | None
        A 7-character (default) abbreviated commit hash, or ``None``
        if the hash cannot be determined.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def get_version_info() -> dict[str, str | None]:
    """Return a dictionary of version-related metadata.

    This is the payload served by the ``/health`` or ``/version`` API
    endpoint.

    Returns
    -------
    dict[str, str | None]
        Keys: ``app_version``, ``build_date``, ``git_commit``.
    """
    return {
        "app_version": APP_VERSION,
        "build_date": BUILD_DATE,
        "git_commit": get_git_commit(),
    }
