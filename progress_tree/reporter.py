"""
reporter.py
===========

Report assembly using the **Builder** design pattern.

:class:`ReportBuilder` accumulates labelled sections and renders them into a
single multi-line string.  Each setter returns ``self`` so calls can be
chained fluently::

    report = (
        ReportBuilder()
        .set_header(root=Path("."), timestamp=datetime.now())
        .set_tree(tree_lines)
        .set_metrics(metrics)
        .set_interpretation()
        .build()
    )

The builder enforces no mandatory ordering, but the rendered output always
places sections in the order they were added via the ``set_*`` methods.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from progress_tree.models import ScanMetrics

logger = logging.getLogger(__name__)

_SEPARATOR = "=" * 60


class ReportBuilder:
    """Incrementally assemble a plain-text project-tree report.

    Each ``set_*`` method appends one named section to an internal buffer and
    returns ``self`` to allow method chaining.  Call :meth:`build` to obtain
    the final string.

    :Example:

    .. code-block:: python

        from datetime import datetime
        from pathlib import Path
        from progress_tree.reporter import ReportBuilder
        from progress_tree.models import ScanMetrics

        metrics = ScanMetrics(file_count=10, dir_count=3, line_count=500)
        report  = (
            ReportBuilder()
            .set_header(Path("."))
            .set_tree(["├── src", "└── tests"])
            .set_metrics(metrics)
            .set_interpretation()
            .build()
        )
    """

    def __init__(self) -> None:
        self._sections: List[str] = []

    # ------------------------------------------------------------------
    # Builder methods
    # ------------------------------------------------------------------

    def set_header(
        self,
        root: Path,
        timestamp: Optional[datetime] = None,
    ) -> "ReportBuilder":
        """Add the report header with generation timestamp and root path.

        :param root: Absolute path of the scanned root directory.
        :param timestamp: Timestamp to embed.  Defaults to ``datetime.now()``.
        :return: ``self`` for chaining.
        """
        ts = timestamp or datetime.now()
        self._sections.extend([
            "Project Tree Report",
            f"Generated : {ts.isoformat(timespec='seconds')}",
            f"Root      : {root}",
        ])
        logger.debug("ReportBuilder: header section added")
        return self

    def set_tree(self, tree_lines: List[str], root_label: Optional[str] = None) -> "ReportBuilder":
        """Add the ASCII directory tree section.

        :param tree_lines: Lines produced by
            :class:`~progress_tree.scanner.TreeScanner` (without the root
            label).
        :param root_label: Label for the root node.  When ``None`` the root
            label is omitted.
        :return: ``self`` for chaining.
        """
        self._sections.append("")
        self._sections.append("ASCII TREE")
        self._sections.append(_SEPARATOR)
        if root_label:
            self._sections.append(root_label)
        self._sections.extend(tree_lines)
        logger.debug("ReportBuilder: tree section added (%d lines)", len(tree_lines))
        return self

    def set_metrics(self, metrics: ScanMetrics) -> "ReportBuilder":
        """Add the project-metrics section.

        :param metrics: Populated :class:`~progress_tree.models.ScanMetrics`
            instance from a completed scan.
        :return: ``self`` for chaining.
        """
        self._sections.append("")
        self._sections.append("PROJECT METRICS")
        self._sections.append(_SEPARATOR)
        self._sections.extend([
            f"Directories   : {metrics.dir_count:,}",
            f"Files         : {metrics.file_count:,}",
            f"Lines of code : {metrics.line_count:,}",
            f"Scan time     : {metrics.elapsed:.2f}s",
        ])
        logger.debug("ReportBuilder: metrics section added")
        return self

    def set_interpretation(self) -> "ReportBuilder":
        """Append a fixed human-readable interpretation note.

        :return: ``self`` for chaining.
        """
        self._sections.append("")
        self._sections.append("INTERPRETATION")
        self._sections.append(_SEPARATOR)
        self._sections.append(
            "This is a structural snapshot of your repository. "
            "It reflects architecture, complexity, and surface area. "
            "If this feels large, it is because the project is doing real work."
        )
        return self

    def add_section(self, title: str, lines: List[str]) -> "ReportBuilder":
        """Append a custom named section.

        :param title: Section heading (rendered in UPPER CASE).
        :param lines: Body lines for this section.
        :return: ``self`` for chaining.
        """
        self._sections.append("")
        self._sections.append(title.upper())
        self._sections.append(_SEPARATOR)
        self._sections.extend(lines)
        return self

    # ------------------------------------------------------------------
    # Terminal operation
    # ------------------------------------------------------------------

    def build(self) -> str:
        """Render all accumulated sections into a single string.

        :return: The completed report as a newline-delimited string.
        """
        return "\n".join(self._sections)
