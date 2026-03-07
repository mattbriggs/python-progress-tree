"""
test_reporter.py
================

Unit tests for :mod:`progress_tree.reporter`.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from progress_tree.models import ScanMetrics
from progress_tree.reporter import ReportBuilder


class TestReportBuilderBuild:
    """Tests for the terminal :meth:`~progress_tree.reporter.ReportBuilder.build` method."""

    def test_empty_builder_returns_string(self):
        result = ReportBuilder().build()
        assert isinstance(result, str)

    def test_build_is_multiline(self):
        result = (
            ReportBuilder()
            .set_header(Path("/tmp"))
            .set_metrics(ScanMetrics())
            .build()
        )
        assert "\n" in result


class TestSetHeader:
    """Tests for :meth:`~progress_tree.reporter.ReportBuilder.set_header`."""

    def test_header_contains_root_path(self):
        report = ReportBuilder().set_header(Path("/my/project")).build()
        assert "/my/project" in report

    def test_header_contains_timestamp(self):
        ts = datetime(2026, 1, 15, 12, 30, 0)
        report = ReportBuilder().set_header(Path("/proj"), timestamp=ts).build()
        assert "2026-01-15" in report

    def test_header_uses_now_when_no_timestamp(self):
        report = ReportBuilder().set_header(Path("/proj")).build()
        # Just check that the year is present (2026 from system date)
        assert str(datetime.now().year) in report

    def test_set_header_returns_self(self):
        builder = ReportBuilder()
        assert builder.set_header(Path("/tmp")) is builder


class TestSetTree:
    """Tests for :meth:`~progress_tree.reporter.ReportBuilder.set_tree`."""

    def test_tree_lines_appear_in_output(self):
        lines = ["├── src", "└── tests"]
        report = ReportBuilder().set_tree(lines).build()
        assert "├── src" in report
        assert "└── tests" in report

    def test_root_label_appears_when_given(self):
        report = ReportBuilder().set_tree([], root_label="my_project").build()
        assert "my_project" in report

    def test_root_label_absent_when_not_given(self):
        report = ReportBuilder().set_tree([]).build()
        # The section heading should still appear
        assert "ASCII TREE" in report

    def test_set_tree_returns_self(self):
        builder = ReportBuilder()
        assert builder.set_tree([]) is builder


class TestSetMetrics:
    """Tests for :meth:`~progress_tree.reporter.ReportBuilder.set_metrics`."""

    def test_metrics_counts_appear(self):
        m = ScanMetrics(file_count=42, dir_count=7, line_count=1234, elapsed=0.5)
        report = ReportBuilder().set_metrics(m).build()
        assert "42" in report
        assert "7" in report
        assert "1,234" in report

    def test_elapsed_appears_formatted(self):
        m = ScanMetrics(elapsed=3.75)
        report = ReportBuilder().set_metrics(m).build()
        assert "3.75s" in report

    def test_set_metrics_returns_self(self):
        builder = ReportBuilder()
        assert builder.set_metrics(ScanMetrics()) is builder


class TestSetInterpretation:
    """Tests for :meth:`~progress_tree.reporter.ReportBuilder.set_interpretation`."""

    def test_interpretation_section_present(self):
        report = ReportBuilder().set_interpretation().build()
        assert "INTERPRETATION" in report

    def test_set_interpretation_returns_self(self):
        builder = ReportBuilder()
        assert builder.set_interpretation() is builder


class TestAddSection:
    """Tests for :meth:`~progress_tree.reporter.ReportBuilder.add_section`."""

    def test_custom_section_title_appears_uppercased(self):
        report = ReportBuilder().add_section("custom notes", ["line one"]).build()
        assert "CUSTOM NOTES" in report

    def test_custom_section_lines_appear(self):
        report = ReportBuilder().add_section("notes", ["hello", "world"]).build()
        assert "hello" in report
        assert "world" in report

    def test_add_section_returns_self(self):
        builder = ReportBuilder()
        assert builder.add_section("x", []) is builder


class TestMethodChaining:
    """Tests verifying that methods can be chained fluently."""

    def test_full_chain_produces_all_sections(self):
        m = ScanMetrics(file_count=5, dir_count=2, line_count=100, elapsed=0.1)
        report = (
            ReportBuilder()
            .set_header(Path("/project"), timestamp=datetime(2026, 3, 1))
            .set_tree(["├── src"], root_label="project")
            .set_metrics(m)
            .set_interpretation()
            .build()
        )
        assert "Project Tree Report" in report
        assert "ASCII TREE" in report
        assert "PROJECT METRICS" in report
        assert "INTERPRETATION" in report
        assert "├── src" in report

    def test_sections_appear_in_order(self):
        report = (
            ReportBuilder()
            .set_header(Path("/p"))
            .set_tree([])
            .set_metrics(ScanMetrics())
            .build()
        )
        header_pos = report.index("Project Tree Report")
        tree_pos = report.index("ASCII TREE")
        metrics_pos = report.index("PROJECT METRICS")
        assert header_pos < tree_pos < metrics_pos
