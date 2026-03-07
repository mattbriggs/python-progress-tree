"""
models.py
=========

Data models shared across the progress_tree package.

All public classes are immutable-by-convention dataclasses.  Mutation
methods use explicit names (``update_file``, ``update_dir``) so call sites
are self-documenting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class ScanMetrics:
    """Aggregate counters collected during a directory scan.

    :param file_count: Total number of files encountered.
    :param dir_count: Total number of directories encountered.
    :param line_count: Total lines of text across all readable files.
    :param elapsed: Wall-clock seconds consumed by the scan.
    """

    file_count: int = 0
    dir_count: int = 0
    line_count: int = 0
    elapsed: float = 0.0

    def update_file(self, lines: int = 0) -> None:
        """Increment the file counter and add *lines* to the line total.

        :param lines: Number of lines in the file just processed.
        """
        self.file_count += 1
        self.line_count += lines

    def update_dir(self) -> None:
        """Increment the directory counter."""
        self.dir_count += 1


@dataclass
class ScanResult:
    """The complete output of a single :class:`~progress_tree.scanner.TreeScanner` run.

    :param root: Absolute path to the scanned root directory.
    :param tree_lines: Lines that form the ASCII directory tree (root label
        is *not* included; callers prepend it as needed).
    :param metrics: Aggregate statistics for the scan.
    """

    root: Path
    tree_lines: List[str] = field(default_factory=list)
    metrics: ScanMetrics = field(default_factory=ScanMetrics)
