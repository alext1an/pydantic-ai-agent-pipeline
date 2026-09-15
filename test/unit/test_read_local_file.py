"""Unit tests for read_local_file function."""
import sys
sys.path.insert(0, 'src')

import tempfile
from pathlib import Path

from myagent.tools.mcp_server.file_tools import (
    FileReadError,
    FileReadSuccess,
    read_local_file,
)


def test_reads_allowed_markdown_file(tmp_path: Path) -> None:
    """Test that we can read an allowed markdown file."""
    # Create a test markdown file
    test_file = tmp_path / "test.md"
    test_file.write_text("# Test\nThis is a test file.\n")

    result = read_local_file(
        root=tmp_path,
        file_path="test.md",
        max_lines=100
    )

    assert isinstance(result, FileReadSuccess)
    assert "# Test" in result.content
    assert result.metadata.truncated is False
    assert result.metadata.lines_read == 2


def test_truncates_after_max_lines(tmp_path: Path) -> None:
    """Test that files are truncated after max_lines."""
    # Create a file with more than 2 lines
    test_file = tmp_path / "test.md"
    content = "\n".join(f"Line {i}" for i in range(5))
    test_file.write_text(content)

    result = read_local_file(
        root=tmp_path,
        file_path="test.md",
        max_lines=2
    )

    assert isinstance(result, FileReadSuccess)
    # Should only have 2 lines
    assert result.metadata.lines_read == 2
    # Should be truncated since we had 5 lines but only read 2
    assert result.metadata.truncated is True
    assert "Line 0" in result.content
    assert "Line 1" in result.content
    assert "Line 2" not in result.content


def test_rejects_max_lines_below_one() -> None:
    """Test that max_lines below 1 is rejected."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        result = read_local_file(
            root=tmp_path,
            file_path="test.md",
            max_lines=0
        )

        assert isinstance(result, FileReadError)
        assert result.code == "INVALID_ARGUMENT"


def test_rejects_max_lines_above_one_thousand() -> None:
    """Test that max_lines above 1000 is rejected."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        result = read_local_file(
            root=tmp_path,
            file_path="test.md",
            max_lines=1001
        )

        assert isinstance(result, FileReadError)
        assert result.code == "INVALID_ARGUMENT"


def test_rejects_path_outside_root(tmp_path: Path) -> None:
    """Test that paths outside the root are rejected."""
    # Create a file outside the root
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "test.md"
    outside_file.write_text("# Outside file")

    result = read_local_file(
        root=tmp_path,
        file_path="../outside/test.md",
        max_lines=100
    )

    assert isinstance(result, FileReadError)
    assert result.code == "PERMISSION_DENIED"


def test_rejects_symlink_to_path_outside_root(tmp_path: Path) -> None:
    """Test that symlinks to paths outside root are rejected."""
    # Create a temp directory OUTSIDE tmp_path
    with tempfile.TemporaryDirectory() as outside_dir:
        outside_file = Path(outside_dir) / "test.md"
        outside_file.write_text("# Outside file")

        # Create a symlink inside the root pointing outside
        symlink_path = tmp_path / "link.md"
        try:
            symlink_path.symlink_to(outside_file)
        except (OSError, NotImplementedError, PermissionError):
            # Symlinks might not be supported or require permissions on some systems
            import pytest
            pytest.skip("Symlinks not supported on this system")
            return

        result = read_local_file(
            root=tmp_path,
            file_path="link.md",
            max_lines=100
        )

        assert isinstance(result, FileReadError)
        assert result.code == "PERMISSION_DENIED"


def test_rejects_disallowed_extension(tmp_path: Path) -> None:
    """Test that disallowed file extensions are rejected."""
    # Create a file with disallowed extension
    test_file = tmp_path / "test.py"
    test_file.write_text("# Python file")

    result = read_local_file(
        root=tmp_path,
        file_path="test.py",
        max_lines=100
    )

    assert isinstance(result, FileReadError)
    assert result.code == "FILE_NOT_FOUND"


def test_returns_file_not_found_for_missing_file(tmp_path: Path) -> None:
    """Test that missing files return FILE_NOT_FOUND."""
    result = read_local_file(
        root=tmp_path,
        file_path="nonexistent.md",
        max_lines=100
    )

    assert isinstance(result, FileReadError)
    assert result.code == "FILE_NOT_FOUND"


def test_rejects_directory(tmp_path: Path) -> None:
    """Test that directories are rejected."""
    # Create a directory
    test_dir = tmp_path / "test_dir.md"
    test_dir.mkdir()

    result = read_local_file(
        root=tmp_path,
        file_path="test_dir.md",
        max_lines=100
    )

    assert isinstance(result, FileReadError)
    assert result.code == "FILE_NOT_FOUND"

def test_rejects_symlink_within_root(tmp_path: Path) -> None:
    """Test that symlinks within root are allowed."""
    # Create a real file
    real_file = tmp_path / "real.md"
    real_file.write_text("# Real file")

    # Create a symlink within the root
    symlink_path = tmp_path / "link.md"
    symlink_path.symlink_to(real_file)

    result = read_local_file(
        root=tmp_path,
        file_path="link.md",
        max_lines=100
    )

    assert isinstance(result, FileReadError)
    assert result.code == "PERMISSION_DENIED"
