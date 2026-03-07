"""
test_scanner.py
===============

Unit tests for :mod:`progress_tree.scanner`.
"""

from __future__ import annotations

from pathlib import Path
from typing import List
from unittest.mock import MagicMock

import pytest

from progress_tree.ignore import NullIgnoreStrategy, PatternIgnoreStrategy
from progress_tree.models import ScanMetrics
from progress_tree.scanner import TreeScanner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tree(tmp_path: Path) -> Path:
    """Create a small, deterministic directory structure under *tmp_path*.

    Structure::

        root/
            alpha.py       (3 lines)
            beta.txt       (2 lines)
            sub/
                gamma.py   (1 line)
                delta.log  (4 lines)

    Returns the root path.
    """
    root = tmp_path / "root"
    root.mkdir()
    (root / "alpha.py").write_text("a\nb\nc\n", encoding="utf-8")
    (root / "beta.txt").write_text("x\ny\n", encoding="utf-8")
    sub = root / "sub"
    sub.mkdir()
    (sub / "gamma.py").write_text("z\n", encoding="utf-8")
    (sub / "delta.log").write_text("1\n2\n3\n4\n", encoding="utf-8")
    return root


# ---------------------------------------------------------------------------
# Basic scan behaviour
# ---------------------------------------------------------------------------

class TestTreeScannerBasic:
    """Tests for the fundamental scanning behaviour."""

    def test_scan_returns_scan_result(self, tmp_path):
        scanner = TreeScanner(root=tmp_path)
        result = scanner.scan()
        assert result.root == tmp_path

    def test_empty_directory_produces_no_tree_lines(self, tmp_path):
        scanner = TreeScanner(root=tmp_path)
        result = scanner.scan()
        assert result.tree_lines == []
        assert result.metrics.file_count == 0
        assert result.metrics.dir_count == 0

    def test_file_count_matches_fixture(self, tmp_path):
        root = _make_tree(tmp_path)
        scanner = TreeScanner(root=root)
        result = scanner.scan()
        assert result.metrics.file_count == 4  # alpha, beta, gamma, delta

    def test_dir_count_matches_fixture(self, tmp_path):
        root = _make_tree(tmp_path)
        scanner = TreeScanner(root=root)
        result = scanner.scan()
        assert result.metrics.dir_count == 1  # sub/

    def test_line_count_matches_fixture(self, tmp_path):
        root = _make_tree(tmp_path)
        scanner = TreeScanner(root=root)
        result = scanner.scan()
        # alpha(3) + beta(2) + gamma(1) + delta(4) = 10
        assert result.metrics.line_count == 10

    def test_elapsed_is_positive(self, tmp_path):
        scanner = TreeScanner(root=tmp_path)
        result = scanner.scan()
        assert result.metrics.elapsed >= 0.0

    def test_tree_lines_contain_file_names(self, tmp_path):
        root = _make_tree(tmp_path)
        scanner = TreeScanner(root=root)
        result = scanner.scan()
        joined = "\n".join(result.tree_lines)
        assert "alpha.py" in joined
        assert "beta.txt" in joined
        assert "gamma.py" in joined
        assert "sub" in joined

    def test_tree_uses_box_drawing_characters(self, tmp_path):
        root = _make_tree(tmp_path)
        scanner = TreeScanner(root=root)
        result = scanner.scan()
        joined = "\n".join(result.tree_lines)
        # At least one connector should be present
        assert "├──" in joined or "└──" in joined


# ---------------------------------------------------------------------------
# no-lines mode
# ---------------------------------------------------------------------------

class TestNoLinesMode:
    """Tests for the count_lines=False option."""

    def test_no_lines_skips_line_count(self, tmp_path):
        root = _make_tree(tmp_path)
        scanner = TreeScanner(root=root, count_lines=False)
        result = scanner.scan()
        assert result.metrics.line_count == 0

    def test_no_lines_still_counts_files(self, tmp_path):
        root = _make_tree(tmp_path)
        scanner = TreeScanner(root=root, count_lines=False)
        result = scanner.scan()
        assert result.metrics.file_count == 4


# ---------------------------------------------------------------------------
# Ignore strategy integration
# ---------------------------------------------------------------------------

class TestIgnoreIntegration:
    """Tests verifying that the ignore strategy is honoured."""

    def test_ignored_files_excluded_from_count(self, tmp_path):
        root = _make_tree(tmp_path)
        strategy = PatternIgnoreStrategy(["*.log"])
        scanner = TreeScanner(root=root, ignore_strategy=strategy)
        result = scanner.scan()
        # delta.log should be excluded
        assert result.metrics.file_count == 3

    def test_ignored_directory_excluded(self, tmp_path):
        root = _make_tree(tmp_path)
        strategy = PatternIgnoreStrategy(["sub/"])
        scanner = TreeScanner(root=root, ignore_strategy=strategy)
        result = scanner.scan()
        assert result.metrics.dir_count == 0
        assert result.metrics.file_count == 2  # only alpha + beta

    def test_ignored_files_absent_from_tree_lines(self, tmp_path):
        root = _make_tree(tmp_path)
        strategy = PatternIgnoreStrategy(["*.log"])
        scanner = TreeScanner(root=root, ignore_strategy=strategy)
        result = scanner.scan()
        joined = "\n".join(result.tree_lines)
        assert "delta.log" not in joined

    def test_null_strategy_includes_all(self, tmp_path):
        root = _make_tree(tmp_path)
        scanner = TreeScanner(root=root, ignore_strategy=NullIgnoreStrategy())
        result = scanner.scan()
        assert result.metrics.file_count == 4


# ---------------------------------------------------------------------------
# Symlink handling
# ---------------------------------------------------------------------------

class TestSymlinkHandling:
    """Symlinks must be silently skipped."""

    def test_symlinks_are_excluded(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        real_file = root / "real.py"
        real_file.write_text("hello\n", encoding="utf-8")
        link = root / "link.py"
        link.symlink_to(real_file)

        scanner = TreeScanner(root=root)
        result = scanner.scan()

        # Only real.py should be counted
        assert result.metrics.file_count == 1
        joined = "\n".join(result.tree_lines)
        assert "real.py" in joined
        assert "link.py" not in joined


# ---------------------------------------------------------------------------
# Progress callback
# ---------------------------------------------------------------------------

class TestProgressCallback:
    """Tests for the progress callback mechanism."""

    def test_callback_fires_at_interval(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        # Create 5 files; interval of 5 should fire once
        for i in range(5):
            (root / f"file_{i}.py").write_text("x\n", encoding="utf-8")

        callback = MagicMock()
        scanner = TreeScanner(root=root, progress_interval=5, progress_callback=callback)
        scanner.scan()

        callback.assert_called_once()

    def test_callback_not_fired_when_interval_zero(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        for i in range(10):
            (root / f"f{i}.py").write_text("x\n", encoding="utf-8")

        callback = MagicMock()
        scanner = TreeScanner(root=root, progress_interval=0, progress_callback=callback)
        scanner.scan()

        callback.assert_not_called()

    def test_callback_receives_metrics(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        for i in range(3):
            (root / f"f{i}.py").write_text("x\n", encoding="utf-8")

        received: List[ScanMetrics] = []
        scanner = TreeScanner(
            root=root,
            progress_interval=3,
            progress_callback=lambda m: received.append(m),
        )
        scanner.scan()

        assert len(received) == 1
        assert isinstance(received[0], ScanMetrics)

    def test_no_callback_no_error(self, tmp_path):
        """progress_callback=None must not raise even when interval fires."""
        root = tmp_path / "root"
        root.mkdir()
        for i in range(5):
            (root / f"f{i}.py").write_text("x\n", encoding="utf-8")

        scanner = TreeScanner(root=root, progress_interval=5, progress_callback=None)
        result = scanner.scan()
        assert result.metrics.file_count == 5


# ---------------------------------------------------------------------------
# Multiple scans on same instance
# ---------------------------------------------------------------------------

class TestMultipleScanCalls:
    """Each call to scan() must return independent results."""

    def test_second_scan_does_not_accumulate_first(self, tmp_path):
        root = _make_tree(tmp_path)
        scanner = TreeScanner(root=root)
        r1 = scanner.scan()
        r2 = scanner.scan()
        # Independent ScanMetrics objects
        assert r1.metrics is not r2.metrics
        assert r1.metrics.file_count == r2.metrics.file_count
