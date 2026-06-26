"""Human-friendly formatting helpers for durations, sizes, and speeds.

All functions accept numeric inputs and return concise, locale-neutral
strings suitable for API responses and log messages.
"""

from __future__ import annotations


def format_duration(seconds: int | float) -> str:
    """Format a duration as ``M:SS`` or ``H:MM:SS``.

    Parameters
    ----------
    seconds:
        Non-negative duration in seconds.  Fractional parts are
        truncated (floored).

    Returns
    -------
    str
        Human-readable duration string.

    Examples
    --------
    >>> format_duration(225)
    '3:45'
    >>> format_duration(3825)
    '1:03:45'
    >>> format_duration(5)
    '0:05'
    """
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_file_size(size_bytes: int | float) -> str:
    """Format a byte count as a human-readable size string.

    Uses binary-ish thresholds (1 024) but labels with SI-style
    suffixes (KB, MB, GB, TB) matching common user expectations.

    Parameters
    ----------
    size_bytes:
        Non-negative file size in bytes.

    Returns
    -------
    str
        Formatted size with one decimal place and a unit suffix.

    Examples
    --------
    >>> format_file_size(4_404_019)
    '4.2 MB'
    >>> format_file_size(1_181_116_006)
    '1.1 GB'
    >>> format_file_size(512)
    '512 B'
    """
    size = float(size_bytes)

    if size < 1024:
        return f"{int(size)} B"

    for unit in ("KB", "MB", "GB", "TB"):
        size /= 1024
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"

    # Unreachable for realistic file sizes, but keeps the type-checker happy
    return f"{size:.1f} TB"  # pragma: no cover


def format_speed(bytes_per_second: float) -> str:
    """Format a transfer speed as a human-readable string.

    Parameters
    ----------
    bytes_per_second:
        Non-negative transfer rate in bytes per second.

    Returns
    -------
    str
        Formatted speed with one decimal place and a ``/s`` suffix.

    Examples
    --------
    >>> format_speed(1_572_864)
    '1.5 MB/s'
    >>> format_speed(512)
    '512 B/s'
    """
    speed = float(bytes_per_second)

    if speed < 1024:
        return f"{int(speed)} B/s"

    for unit in ("KB/s", "MB/s", "GB/s"):
        speed /= 1024
        if speed < 1024 or unit == "GB/s":
            return f"{speed:.1f} {unit}"

    return f"{speed:.1f} GB/s"  # pragma: no cover


def format_eta(seconds: float) -> str:
    """Format an estimated time of arrival as a compact string.

    Parameters
    ----------
    seconds:
        Non-negative ETA in seconds.  Fractional parts are truncated.

    Returns
    -------
    str
        Human-readable ETA such as ``"45s"``, ``"2m 30s"``, or
        ``"1h 5m 20s"``.

    Examples
    --------
    >>> format_eta(150)
    '2m 30s'
    >>> format_eta(45)
    '45s'
    >>> format_eta(3920)
    '1h 5m 20s'
    """
    total = int(seconds)

    if total < 0:
        return "0s"

    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)

    parts: list[str] = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    # Always show seconds unless there's at least one larger unit and
    # the seconds component is zero.
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)
