"""Filename and path sanitisation utilities.

These helpers ensure user-supplied strings can never escape the
designated base directory or produce invalid filesystem entries.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.exceptions.handlers import InvalidInputError

# ── Pre-compiled patterns ────────────────────────────────────────────────

_UNSAFE_CHARS_RE: re.Pattern[str] = re.compile(
    r"[<>:\"/\\|?*\x00-\x1f]",
)
"""Characters that are unsafe in filenames on Windows and/or POSIX."""

_SHELL_META_RE: re.Pattern[str] = re.compile(
    r"[;&`$!#(){}\[\]~]",
)
"""Shell metacharacters that could be dangerous if interpolated."""

_PATH_SEP_RE: re.Pattern[str] = re.compile(
    r"[/\\]",
)
"""Forward and back slashes used as path separators."""

_WHITESPACE_COLLAPSE_RE: re.Pattern[str] = re.compile(
    r"\s+",
)
"""One or more whitespace characters (for collapsing runs)."""

_MAX_FILENAME_LENGTH: int = 200
"""Maximum allowed filename length (characters, not bytes)."""


# ── Public API ───────────────────────────────────────────────────────────


def sanitize_filename(name: str) -> str:
    """Produce a filesystem-safe filename from an arbitrary string.

    The following transformations are applied in order:

    1. Strip leading/trailing whitespace.
    2. Remove path separator characters (``/``, ``\\``).
    3. Remove null bytes and control characters (``\\x00``–``\\x1f``).
    4. Replace shell metacharacters (``; & ` $ ! # ( ) { } [ ] ~``) with
       underscores.
    5. Replace remaining unsafe characters (``< > : " | ? *``) with
       underscores.
    6. Collapse consecutive whitespace into a single space.
    7. Strip leading/trailing dots and spaces (prevents hidden files and
       trailing-dot issues on Windows).
    8. Truncate to :data:`_MAX_FILENAME_LENGTH` characters.
    9. Fall back to ``"untitled"`` if the result is empty.

    Parameters
    ----------
    name:
        The raw, untrusted filename string.

    Returns
    -------
    str
        A sanitised filename safe for use on both Windows and POSIX
        filesystems.

    Examples
    --------
    >>> sanitize_filename("My Song (feat. Artist).mp3")
    'My Song _feat. Artist_.mp3'
    >>> sanitize_filename("../../etc/passwd")
    '..etc_passwd'
    >>> sanitize_filename("")
    'untitled'
    """
    # Step 1: strip outer whitespace
    result = name.strip()

    # Step 2: remove path separators
    result = _PATH_SEP_RE.sub("", result)

    # Step 3: remove null bytes and control characters, plus unsafe chars
    result = _UNSAFE_CHARS_RE.sub("_", result)

    # Step 4: replace shell metacharacters
    result = _SHELL_META_RE.sub("_", result)

    # Step 5: collapse whitespace runs
    result = _WHITESPACE_COLLAPSE_RE.sub(" ", result)

    # Step 6: strip leading/trailing dots and spaces
    result = result.strip(". ")

    # Step 7: truncate
    if len(result) > _MAX_FILENAME_LENGTH:
        result = result[:_MAX_FILENAME_LENGTH].rstrip(". ")

    # Step 8: fallback
    if not result:
        result = "untitled"

    return result


def safe_path_join(base: Path, *parts: str) -> Path:
    """Join path components and verify the result stays within *base*.

    This is a defence-in-depth measure against path-traversal attacks.
    After joining and resolving symlinks the resulting absolute path
    **must** be a descendant of (or equal to) *base*.

    Parameters
    ----------
    base:
        The trusted root directory.  It will be resolved to an absolute
        path before comparison.
    *parts:
        One or more untrusted path components to join.

    Returns
    -------
    Path
        The resolved, absolute path.

    Raises
    ------
    InvalidInputError
        If the resolved path escapes the base directory.

    Examples
    --------
    >>> safe_path_join(Path("/tmp/flashifi"), "abc", "song.mp3")
    PosixPath('/tmp/flashifi/abc/song.mp3')
    """
    resolved_base = base.resolve()
    joined = resolved_base.joinpath(*parts).resolve()

    # The resolved path must start with the base path (i.e. be inside it).
    try:
        joined.relative_to(resolved_base)
    except ValueError:
        raise InvalidInputError(
            f"Path traversal detected: the resulting path escapes "
            f"the base directory '{resolved_base}'."
        ) from None

    return joined
