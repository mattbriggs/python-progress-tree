"""
test_models.py
==============

Unit tests for :mod:`progress_tree.models`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from progress_tree.models import ScanMetrics, ScanResult


class TestScanMetrics:
    """Tests for :class:`~progress_tree.models.ScanMetrics`."""

    def test_defaults(self):
        """All counters default to zero and elapsed to 0.0."""
        m = ScanMetrics()
        assert m.file_count == 0
        assert m.dir_count == 0
        assert m.line_count == 0
        assert m.elapsed == 0.0

    def test_update_file_increments_file_count(self):
        """update_file() increments file_count by exactly one."""
        m = ScanMetrics()
        m.update_file(lines=10)
        assert m.file_count == 1

    def test_update_file_adds_lines(self):
        """update_file() adds the supplied line count to line_count."""
        m = ScanMetrics()
        m.update_file(lines=42)
        assert m.line_count == 42

    def test_update_file_zero_lines(self):
        """update_file() with zero lines still increments file_count."""
        m = ScanMetrics()
        m.update_file(lines=0)
        assert m.file_count == 1
        assert m.line_count == 0

    def test_update_file_accumulates(self):
        """Multiple update_file() calls accumulate correctly."""
        m = ScanMetrics()
        m.update_file(lines=10)
        m.update_file(lines=20)
        m.update_file(lines=30)
        assert m.file_count == 3
        assert m.line_count == 60

    def test_update_dir_increments_dir_count(self):
        """update_dir() increments dir_count by exactly one."""
        m = ScanMetrics()
        m.update_dir()
        assert m.dir_count == 1

    def test_update_dir_does_not_change_file_or_lines(self):
        """update_dir() must not touch file_count or line_count."""
        m = ScanMetrics()
        m.update_dir()
        assert m.file_count == 0
        assert m.line_count == 0

    def test_elapsed_is_mutable(self):
        """elapsed can be assigned after construction."""
        m = ScanMetrics()
        m.elapsed = 3.14
        assert m.elapsed == pytest.approx(3.14)


class TestScanResult:
    """Tests for :class:`~progress_tree.models.ScanResult`."""

    def test_construction_with_root(self):
        """ScanResult stores the root path."""
        result = ScanResult(root=Path("/tmp"))
        assert result.root == Path("/tmp")

    def test_tree_lines_defaults_to_empty(self):
        """tree_lines defaults to an empty list."""
        result = ScanResult(root=Path("/tmp"))
        assert result.tree_lines == []

    def test_metrics_defaults_to_zero_metrics(self):
        """metrics defaults to a fresh ScanMetrics with all-zero counts."""
        result = ScanResult(root=Path("/tmp"))
        assert result.metrics.file_count == 0
        assert result.metrics.dir_count == 0

    def test_separate_instances_have_independent_metrics(self):
        """Two ScanResult instances must not share the same ScanMetrics object."""
        r1 = ScanResult(root=Path("/a"))
        r2 = ScanResult(root=Path("/b"))
        r1.metrics.update_file(lines=5)
        assert r2.metrics.file_count == 0
