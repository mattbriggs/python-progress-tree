"""
progress_tree
=============

ASCII directory tree generator with project metrics.

Recursively walks a filesystem, builds a clean ASCII tree, collects
file/directory/line-count metrics, and writes a timestamped report.

Typical usage::

    from progress_tree import TreeScanner, ReportBuilder
    from progress_tree.ignore import load_ignore_strategy
    from pathlib import Path

    strategy = load_ignore_strategy(Path("tree_ignore.txt"))
    scanner  = TreeScanner(root=Path("."), ignore_strategy=strategy)
    result   = scanner.scan()
    report   = ReportBuilder().set_header(result.root).set_tree(result.tree_lines) \\
                              .set_metrics(result.metrics).build()
    print(report)

Entry point (after ``pip install -e .``)::

    progress-tree --help
"""

from __future__ import annotations

from progress_tree.models import ScanMetrics, ScanResult
from progress_tree.scanner import TreeScanner
from progress_tree.reporter import ReportBuilder

__all__ = ["ScanMetrics", "ScanResult", "TreeScanner", "ReportBuilder"]
__version__ = "1.0.0"
__author__ = "Matt Briggs"
