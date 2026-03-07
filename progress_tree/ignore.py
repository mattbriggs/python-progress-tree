"""
ignore.py
=========

Ignore-pattern handling using the **Strategy** design pattern.

Classes
-------
- :class:`IgnoreStrategy` – Abstract base class.
- :class:`PatternIgnoreStrategy` – Matches against a list of gitignore-style
  patterns held in memory.
- :class:`NullIgnoreStrategy` – Never ignores anything; useful as a safe
  default or in tests.
- :class:`CompositeIgnoreStrategy` – Chains multiple strategies with
  logical-OR semantics (ignores if *any* child strategy ignores).

Factory
-------
- :func:`load_ignore_strategy` – Reads a ``tree_ignore.txt``-style file from
  disk and returns a ready-to-use :class:`PatternIgnoreStrategy`.  Returns a
  :class:`NullIgnoreStrategy` when the file does not exist.

Pattern syntax (subset of gitignore)
--------------------------------------
- ``dir/``        – matches any path component that starts with ``dir``
- ``*.ext``       – glob match against the full relative POSIX path
- ``exact_name``  – fnmatch against the file/directory name only
- Lines beginning with ``#`` and blank lines are ignored.
"""

from __future__ import annotations

import fnmatch
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Sequence

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class IgnoreStrategy(ABC):
    """Abstract strategy for deciding whether a filesystem path should be
    excluded from a directory scan.
    """

    @abstractmethod
    def is_ignored(self, path: Path, root: Path) -> bool:
        """Return ``True`` when *path* should be excluded from the scan.

        :param path: Absolute path of the candidate entry.
        :param root: Absolute path of the scan root (used to derive the
            relative path for pattern matching).
        :return: ``True`` if the entry should be skipped.
        """


# ---------------------------------------------------------------------------
# Concrete strategies
# ---------------------------------------------------------------------------

class NullIgnoreStrategy(IgnoreStrategy):
    """An ignore strategy that never ignores anything.

    Useful as a safe default when no ignore file is present.
    """

    def is_ignored(self, path: Path, root: Path) -> bool:  # noqa: D102
        return False


class PatternIgnoreStrategy(IgnoreStrategy):
    """Match a filesystem path against an ordered list of gitignore-style
    patterns.

    :param patterns: Sequence of pattern strings loaded from an ignore file.
    """

    def __init__(self, patterns: Sequence[str]) -> None:
        self._patterns: List[str] = list(patterns)
        logger.debug("PatternIgnoreStrategy initialised with %d pattern(s)", len(self._patterns))

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def patterns(self) -> List[str]:
        """Read-only view of the loaded patterns.

        :return: List of pattern strings.
        """
        return list(self._patterns)

    def is_ignored(self, path: Path, root: Path) -> bool:
        """Return ``True`` when *path* matches any loaded pattern.

        Matching rules (evaluated in order):

        1. **Directory prefix** – patterns ending with ``/`` match when the
           relative POSIX path starts with the pattern prefix.
        2. **Full-path glob** – ``fnmatch`` is applied to the full relative
           POSIX path.
        3. **Name-only glob** – ``fnmatch`` is applied to the bare filename /
           directory name.

        :param path: Absolute path of the candidate entry.
        :param root: Absolute path of the scan root.
        :return: ``True`` if the entry should be skipped.
        """
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            logger.warning("Path %s is not relative to root %s; treating as not-ignored", path, root)
            return False

        name = path.name

        for pattern in self._patterns:
            # Rule 1 – directory prefix  (e.g. ".git/")
            if pattern.endswith("/") and (
                rel.startswith(pattern[:-1] + "/") or rel == pattern[:-1]
            ):
                logger.debug("Path '%s' ignored by directory prefix pattern '%s'", rel, pattern)
                return True

            # Rule 2 – full-path glob  (e.g. "src/*.pyc")
            if fnmatch.fnmatch(rel, pattern):
                logger.debug("Path '%s' ignored by full-path pattern '%s'", rel, pattern)
                return True

            # Rule 3 – name-only glob  (e.g. "*.pyc", ".DS_Store")
            if fnmatch.fnmatch(name, pattern):
                logger.debug("Path '%s' ignored by name pattern '%s'", rel, pattern)
                return True

        return False


class CompositeIgnoreStrategy(IgnoreStrategy):
    """Chain multiple :class:`IgnoreStrategy` instances with logical-OR
    semantics.

    A path is ignored when *at least one* child strategy returns ``True``.

    :param strategies: Ordered sequence of child strategies to evaluate.
    """

    def __init__(self, strategies: Sequence[IgnoreStrategy]) -> None:
        self._strategies: List[IgnoreStrategy] = list(strategies)

    def is_ignored(self, path: Path, root: Path) -> bool:  # noqa: D102
        return any(s.is_ignored(path, root) for s in self._strategies)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def load_ignore_strategy(ignore_file: Path) -> IgnoreStrategy:
    """Build an :class:`IgnoreStrategy` from a ``tree_ignore.txt``-style file.

    Lines that are blank or start with ``#`` are skipped.  If *ignore_file*
    does not exist a :class:`NullIgnoreStrategy` is returned so callers
    do not need to handle the missing-file case.

    :param ignore_file: Path to the ignore-patterns file.
    :return: A ready-to-use :class:`IgnoreStrategy` instance.
    """
    if not ignore_file.exists():
        logger.info("Ignore file not found at '%s'; no patterns loaded", ignore_file)
        return NullIgnoreStrategy()

    patterns: List[str] = []
    for line in ignore_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            patterns.append(stripped)

    logger.info("Loaded %d ignore pattern(s) from '%s'", len(patterns), ignore_file)
    return PatternIgnoreStrategy(patterns)
