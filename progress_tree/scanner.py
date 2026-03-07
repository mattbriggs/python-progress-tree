"""
scanner.py
==========

Recursive directory-tree scanner.

The :class:`TreeScanner` class is the single entry point for walking a
filesystem tree.  It delegates ignore decisions to an
:class:`~progress_tree.ignore.IgnoreStrategy`, accumulates metrics in a
:class:`~progress_tree.models.ScanMetrics` instance, and invokes an optional
progress callback at a configurable interval so the caller can display live
feedback without coupling the scanner to any particular UI.

Example::

    from pathlib import Path
    from progress_tree.ignore import load_ignore_strategy
    from progress_tree.scanner import TreeScanner

    strategy = load_ignore_strategy(Path("tree_ignore.txt"))
    scanner  = TreeScanner(root=Path("."), ignore_strategy=strategy)
    result   = scanner.scan()

    print(f"Files: {result.metrics.file_count}")
    for line in result.tree_lines:
        print(line)
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable, List, Optional

from progress_tree.ignore import IgnoreStrategy, NullIgnoreStrategy
from progress_tree.models import ScanMetrics, ScanResult

logger = logging.getLogger(__name__)

# Type alias for the optional progress callback.
ProgressCallback = Callable[[ScanMetrics], None]

# Box-drawing connectors used to render the ASCII tree.
_CONNECTOR_LAST = "└── "
_CONNECTOR_MID = "├── "
_EXTENSION_LAST = "    "
_EXTENSION_MID = "│   "


class TreeScanner:
    """Recursively scan a directory and build an ASCII tree with metrics.

    :param root: Root directory to scan.  Defaults to the current working
        directory if not supplied.
    :param ignore_strategy: Strategy used to decide which paths to skip.
        Defaults to :class:`~progress_tree.ignore.NullIgnoreStrategy`
        (nothing is ignored).
    :param progress_interval: Emit a progress callback every *N* files.
        Set to ``0`` to disable progress reporting.
    :param progress_callback: Callable invoked with the live
        :class:`~progress_tree.models.ScanMetrics` snapshot whenever the
        progress interval fires.  Receives the metrics object so the caller
        can read ``file_count``, ``dir_count``, and ``line_count``.
    :param count_lines: When ``True`` (default) open each readable file and
        count its lines.  Set to ``False`` for a faster scan that skips line
        counting.
    """

    def __init__(
        self,
        root: Optional[Path] = None,
        *,
        ignore_strategy: Optional[IgnoreStrategy] = None,
        progress_interval: int = 200,
        progress_callback: Optional[ProgressCallback] = None,
        count_lines: bool = True,
    ) -> None:
        self._root: Path = (root or Path.cwd()).resolve()
        self._ignore: IgnoreStrategy = ignore_strategy or NullIgnoreStrategy()
        self._progress_interval: int = progress_interval
        self._progress_callback: Optional[ProgressCallback] = progress_callback
        self._count_lines: bool = count_lines

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(self) -> ScanResult:
        """Execute the scan and return a :class:`~progress_tree.models.ScanResult`.

        The method is intentionally stateless across calls: each invocation
        creates fresh :class:`~progress_tree.models.ScanMetrics` so the same
        :class:`TreeScanner` instance can be reused.

        :return: A :class:`~progress_tree.models.ScanResult` containing the
            ASCII tree lines and aggregate metrics.
        :raises PermissionError: Propagated only if the *root* itself is
            unreadable.  Subdirectory permission errors are silently skipped.
        """
        logger.info("Starting scan of '%s'", self._root)
        metrics = ScanMetrics()
        start = time.monotonic()

        tree_lines = self._walk(self._root, metrics, prefix="")

        metrics.elapsed = time.monotonic() - start
        logger.info(
            "Scan complete – files=%d dirs=%d lines=%d elapsed=%.2fs",
            metrics.file_count,
            metrics.dir_count,
            metrics.line_count,
            metrics.elapsed,
        )
        return ScanResult(root=self._root, tree_lines=tree_lines, metrics=metrics)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _walk(self, path: Path, metrics: ScanMetrics, prefix: str) -> List[str]:
        """Recursively build tree lines for *path*.

        :param path: Directory currently being walked.
        :param metrics: Mutable metrics accumulator.
        :param prefix: Current indentation prefix string.
        :return: List of rendered tree-line strings.
        """
        lines: List[str] = []

        try:
            entries = self._sorted_entries(path)
        except PermissionError:
            logger.warning("Permission denied reading directory '%s'; skipping", path)
            return lines

        total = len(entries)
        for index, entry in enumerate(entries):
            is_last = index == total - 1
            connector = _CONNECTOR_LAST if is_last else _CONNECTOR_MID
            lines.append(f"{prefix}{connector}{entry.name}")

            if entry.is_dir():
                metrics.update_dir()
                extension = _EXTENSION_LAST if is_last else _EXTENSION_MID
                lines.extend(self._walk(entry, metrics, prefix + extension))
            else:
                line_count = self._count_file_lines(entry) if self._count_lines else 0
                metrics.update_file(line_count)
                self._maybe_emit_progress(metrics)

        return lines

    def _sorted_entries(self, path: Path) -> List[Path]:
        """Return the children of *path* sorted directories-first, then by
        lower-cased name.  Symlinks and ignored entries are excluded.

        :param path: Directory to list.
        :return: Filtered and sorted list of child :class:`~pathlib.Path` objects.
        :raises PermissionError: If the directory cannot be listed.
        """
        return sorted(
            [
                entry
                for entry in path.iterdir()
                if not entry.is_symlink()
                and not self._ignore.is_ignored(entry, self._root)
            ],
            key=lambda p: (p.is_file(), p.name.lower()),
        )

    @staticmethod
    def _count_file_lines(file_path: Path) -> int:
        """Return the number of lines in *file_path*, or ``0`` on any error.

        :param file_path: Path to the file to read.
        :return: Line count, or ``0`` if the file is unreadable / binary.
        """
        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as fh:
                return sum(1 for _ in fh)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not count lines in '%s': %s", file_path, exc)
            return 0

    def _maybe_emit_progress(self, metrics: ScanMetrics) -> None:
        """Fire the progress callback if the interval has been reached.

        :param metrics: Current metrics snapshot.
        """
        if (
            self._progress_interval > 0
            and self._progress_callback is not None
            and metrics.file_count % self._progress_interval == 0
            and metrics.file_count > 0
        ):
            self._progress_callback(metrics)
