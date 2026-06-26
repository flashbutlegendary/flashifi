"""
Tests for app.utils.sanitizers.
Covers filename sanitisation (dangerous chars, null bytes, length limits)
and safe_path_join (traversal & absolute-path blocking).
"""
import pytest
from pathlib import Path
from app.utils.sanitizers import sanitize_filename, safe_path_join
from app.exceptions.handlers import InvalidInputError


# ── sanitize_filename ────────────────────────────────────────────────────────


class TestSanitizeFilename:
    """Filename sanitisation edge-cases."""

    def test_removes_forward_slashes(self):
        assert "/" not in sanitize_filename("path/to/file")

    def test_removes_backslashes(self):
        assert "\\" not in sanitize_filename("path\\to\\file")

    def test_removes_null_bytes(self):
        assert "\x00" not in sanitize_filename("file\x00name")

    def test_removes_shell_metacharacters(self):
        result = sanitize_filename("file;rm -rf /")
        assert ";" not in result
        assert result  # must be non-empty

    def test_empty_string_returns_untitled(self):
        assert sanitize_filename("") == "untitled"

    def test_only_slashes_returns_untitled(self):
        assert sanitize_filename("///") == "untitled"

    def test_length_capped_at_200(self):
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) <= 200


# ── safe_path_join ───────────────────────────────────────────────────────────


class TestSafePathJoin:
    """Path-join must prevent traversal and absolute-path injection."""

    def test_normal_join(self):
        base = Path("/tmp/flashifi")
        result = safe_path_join(base, "task123", "output.mp3")
        assert str(result).startswith(str(base.resolve()))

    def test_traversal_blocked(self):
        base = Path("/tmp/flashifi")
        with pytest.raises(InvalidInputError):
            safe_path_join(base, "..", "..", "etc", "passwd")

    def test_absolute_path_blocked(self):
        base = Path("/tmp/flashifi")
        with pytest.raises(InvalidInputError):
            safe_path_join(base, "/etc/passwd")
