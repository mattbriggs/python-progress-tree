"""
cli.py
======

Command-line interface for ``progress-tree``.

Entry point: :func:`main`.  Registered as the ``progress-tree`` console
script in ``pyproject.toml``.

Usage::

    progress-tree [OPTIONS]

Run ``progress-tree --help`` for the full option list.

Exit codes
----------
- ``0`` – success.
- ``1`` – user-visible error (bad argument, unreadable root, etc.).
- ``2`` – argparse error (wrong flag, missing required value).
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from progress_tree import __version__
from progress_tree.ignore import load_ignore_strategy
from progress_tree.models import ScanMetrics
from progress_tree.reporter import ReportBuilder
from progress_tree.scanner import TreeScanner

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Construct and return the CLI argument parser.

    :return: Configured :class:`argparse.ArgumentParser` instance.
    """
    parser = argparse.ArgumentParser(
        prog="progress-tree",
        description=(
            "Generate an ASCII directory tree with project metrics "
            "and write a timestamped report."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan the current directory, write a report file
  progress-tree

  # Scan a specific directory and print to stdout instead of a file
  progress-tree --root ~/projects/my-app --stdout

  # Use a custom ignore file and log verbosely
  progress-tree --ignore-file .treeignore --log-level DEBUG

  # Skip line counting for a faster scan on large repos
  progress-tree --no-lines

  # Write report to a specific output file
  progress-tree --output /tmp/tree_report.txt
""",
    )

    # Version
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    # ---- Input / output -----------------------------------------------
    io_group = parser.add_argument_group("input / output")

    io_group.add_argument(
        "--root", "-r",
        metavar="DIR",
        type=Path,
        default=None,
        help=(
            "Root directory to scan. "
            "Defaults to the current working directory."
        ),
    )
    io_group.add_argument(
        "--output", "-o",
        metavar="FILE",
        type=Path,
        default=None,
        help=(
            "Path for the report file. "
            "Defaults to 'project_tree_<timestamp>.txt' in the root directory."
        ),
    )
    io_group.add_argument(
        "--ignore-file", "-i",
        metavar="FILE",
        type=Path,
        default=None,
        help=(
            "Path to the ignore-patterns file (gitignore style). "
            "Defaults to '<root>/tree_ignore.txt'."
        ),
    )

    # ---- Behaviour ----------------------------------------------------
    scan_group = parser.add_argument_group("scan behaviour")

    scan_group.add_argument(
        "--no-lines",
        action="store_true",
        default=False,
        help="Skip line counting.  Faster for very large repositories.",
    )
    scan_group.add_argument(
        "--progress-interval",
        metavar="N",
        type=int,
        default=200,
        help=(
            "Print a progress update to stderr every N files. "
            "Set to 0 to silence progress output. (default: 200)"
        ),
    )

    # ---- Output mode --------------------------------------------------
    output_group = parser.add_argument_group("output mode")

    output_group.add_argument(
        "--stdout",
        action="store_true",
        default=False,
        help="Print the report to stdout instead of writing a file.",
    )
    output_group.add_argument(
        "--quiet", "-q",
        action="store_true",
        default=False,
        help="Suppress the summary banner printed after a successful scan.",
    )

    # ---- Logging ------------------------------------------------------
    log_group = parser.add_argument_group("logging")

    log_group.add_argument(
        "--log-level", "-l",
        metavar="LEVEL",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help=(
            "Logging verbosity level. "
            "One of DEBUG | INFO | WARNING | ERROR | CRITICAL. "
            "(default: WARNING)"
        ),
    )
    log_group.add_argument(
        "--log-file",
        metavar="FILE",
        type=Path,
        default=None,
        help="Write log output to FILE instead of stderr.",
    )

    return parser


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def configure_logging(level: str, log_file: Optional[Path] = None) -> None:
    """Configure the root logger.

    :param level: Logging level string (e.g. ``"DEBUG"``, ``"WARNING"``).
    :param log_file: Optional path; when provided log records are written to
        *log_file* in addition to stderr.
    """
    numeric_level = getattr(logging, level.upper(), logging.WARNING)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]

    if log_file is not None:
        try:
            handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
        except OSError as exc:
            # Don't abort the run if the log file can't be opened.
            print(f"WARNING: Cannot open log file '{log_file}': {exc}", file=sys.stderr)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        handlers=handlers,
        force=True,
    )
    logger.debug("Logging configured: level=%s log_file=%s", level, log_file)


# ---------------------------------------------------------------------------
# Progress callback factory
# ---------------------------------------------------------------------------

def _make_progress_callback(quiet: bool):
    """Return a progress callback that prints to stderr unless *quiet* is set.

    :param quiet: When ``True`` the returned callable is a no-op.
    :return: Callable suitable for passing to :class:`~progress_tree.scanner.TreeScanner`.
    """
    if quiet:
        return None

    def _callback(metrics: ScanMetrics) -> None:
        print(
            f"  Scanning… {metrics.file_count:,} files  "
            f"{metrics.dir_count:,} dirs  "
            f"{metrics.line_count:,} lines",
            file=sys.stderr,
        )

    return _callback


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    """Parse arguments and run the scanner.

    :param argv: Argument list for testing; uses ``sys.argv`` when ``None``.
    :return: Exit code (``0`` = success, ``1`` = error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(args.log_level, args.log_file)
    logger.debug("Parsed arguments: %s", args)

    # ---- Resolve paths ------------------------------------------------
    root: Path = (args.root or Path.cwd()).resolve()
    if not root.exists():
        print(f"ERROR: Root directory does not exist: '{root}'", file=sys.stderr)
        return 1
    if not root.is_dir():
        print(f"ERROR: Root is not a directory: '{root}'", file=sys.stderr)
        return 1

    ignore_file: Path = args.ignore_file or (root / "tree_ignore.txt")
    ignore_strategy = load_ignore_strategy(ignore_file)

    # ---- Scan ---------------------------------------------------------
    if not args.quiet:
        print(f"\nProgress Tree  v{__version__}", file=sys.stderr)
        print(f"Root    : {root}", file=sys.stderr)
        print(f"Ignore  : {ignore_file}", file=sys.stderr)
        print("-" * 60, file=sys.stderr)

    scanner = TreeScanner(
        root=root,
        ignore_strategy=ignore_strategy,
        progress_interval=args.progress_interval,
        progress_callback=_make_progress_callback(args.quiet),
        count_lines=not args.no_lines,
    )

    try:
        result = scanner.scan()
    except PermissionError as exc:
        print(f"ERROR: Cannot read root directory: {exc}", file=sys.stderr)
        return 1

    # ---- Build report -------------------------------------------------
    timestamp = datetime.now()
    root_label = result.root.name

    report = (
        ReportBuilder()
        .set_header(root=result.root, timestamp=timestamp)
        .set_tree(tree_lines=result.tree_lines, root_label=root_label)
        .set_metrics(result.metrics)
        .set_interpretation()
        .build()
    )

    # ---- Write / print ------------------------------------------------
    if args.stdout:
        print(report)
    else:
        output_path: Path = args.output or (
            root / f"project_tree_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        )
        try:
            output_path.write_text(report, encoding="utf-8")
        except OSError as exc:
            print(f"ERROR: Cannot write report to '{output_path}': {exc}", file=sys.stderr)
            return 1

        if not args.quiet:
            print(f"Report written to: {output_path}", file=sys.stderr)

    # ---- Summary ------------------------------------------------------
    if not args.quiet:
        m = result.metrics
        print(
            f"\nDone.  Files: {m.file_count:,}  "
            f"Dirs: {m.dir_count:,}  "
            f"Lines: {m.line_count:,}  "
            f"Time: {m.elapsed:.2f}s",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
