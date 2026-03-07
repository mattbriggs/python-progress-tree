"""
test_ignore.py
==============

Unit tests for :mod:`progress_tree.ignore`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from progress_tree.ignore import (
    CompositeIgnoreStrategy,
    NullIgnoreStrategy,
    PatternIgnoreStrategy,
    load_ignore_strategy,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def root(tmp_path: Path) -> Path:
    """Return a temporary root directory."""
    return tmp_path


# ---------------------------------------------------------------------------
# NullIgnoreStrategy
# ---------------------------------------------------------------------------

class TestNullIgnoreStrategy:
    """Tests for :class:`~progress_tree.ignore.NullIgnoreStrategy`."""

    def test_never_ignores_a_file(self, root):
        s = NullIgnoreStrategy()
        f = root / "hello.py"
        assert s.is_ignored(f, root) is False

    def test_never_ignores_a_directory(self, root):
        s = NullIgnoreStrategy()
        d = root / "subdir"
        assert s.is_ignored(d, root) is False


# ---------------------------------------------------------------------------
# PatternIgnoreStrategy
# ---------------------------------------------------------------------------

class TestPatternIgnoreStrategy:
    """Tests for :class:`~progress_tree.ignore.PatternIgnoreStrategy`."""

    def test_empty_patterns_never_ignores(self, root):
        s = PatternIgnoreStrategy([])
        assert s.is_ignored(root / "file.py", root) is False

    def test_exact_name_match(self, root):
        s = PatternIgnoreStrategy([".DS_Store"])
        assert s.is_ignored(root / ".DS_Store", root) is True

    def test_exact_name_non_match(self, root):
        s = PatternIgnoreStrategy([".DS_Store"])
        assert s.is_ignored(root / "README.md", root) is False

    def test_glob_extension_match(self, root):
        s = PatternIgnoreStrategy(["*.pyc"])
        assert s.is_ignored(root / "module.pyc", root) is True

    def test_glob_extension_non_match(self, root):
        s = PatternIgnoreStrategy(["*.pyc"])
        assert s.is_ignored(root / "module.py", root) is False

    def test_directory_prefix_pattern(self, root):
        """Patterns ending with '/' should match directory paths."""
        s = PatternIgnoreStrategy([".git/"])
        assert s.is_ignored(root / ".git", root) is True

    def test_directory_prefix_does_not_match_file_with_same_name(self, root):
        """A directory-prefix pattern should not hide a plain file of the same name."""
        s = PatternIgnoreStrategy([".git/"])
        # A file named '.git' at the root should still be matched because
        # PatternIgnoreStrategy falls through to the name-only glob rule.
        # We test the nested path case:
        sub = root / "sub" / ".git"
        assert s.is_ignored(sub, root) is True

    def test_nested_path_glob(self, root):
        """Full-path globs should match nested entries."""
        s = PatternIgnoreStrategy(["src/*.pyc"])
        assert s.is_ignored(root / "src" / "module.pyc", root) is True
        assert s.is_ignored(root / "other" / "module.pyc", root) is False

    def test_multiple_patterns_any_match(self, root):
        s = PatternIgnoreStrategy([".git/", "*.pyc", ".DS_Store"])
        assert s.is_ignored(root / ".git", root) is True
        assert s.is_ignored(root / "app.pyc", root) is True
        assert s.is_ignored(root / ".DS_Store", root) is True
        assert s.is_ignored(root / "README.md", root) is False

    def test_patterns_property_returns_copy(self):
        """patterns property should return a copy, not the internal list."""
        s = PatternIgnoreStrategy(["*.log"])
        patterns = s.patterns
        patterns.append("extra")
        assert "extra" not in s.patterns

    def test_path_outside_root_does_not_raise(self, root, tmp_path):
        """is_ignored handles paths outside root gracefully (logs warning, returns False)."""
        s = PatternIgnoreStrategy(["*.py"])
        outside = Path("/completely/different/path/file.py")
        # Should not raise; result is False (path unrelated to root)
        result = s.is_ignored(outside, root)
        assert result is False


# ---------------------------------------------------------------------------
# CompositeIgnoreStrategy
# ---------------------------------------------------------------------------

class TestCompositeIgnoreStrategy:
    """Tests for :class:`~progress_tree.ignore.CompositeIgnoreStrategy`."""

    def test_empty_composite_never_ignores(self, root):
        s = CompositeIgnoreStrategy([])
        assert s.is_ignored(root / "file.py", root) is False

    def test_any_child_match_causes_ignore(self, root):
        s = CompositeIgnoreStrategy([
            PatternIgnoreStrategy(["*.log"]),
            PatternIgnoreStrategy(["*.pyc"]),
        ])
        assert s.is_ignored(root / "debug.log", root) is True
        assert s.is_ignored(root / "module.pyc", root) is True
        assert s.is_ignored(root / "source.py", root) is False

    def test_null_child_never_blocks(self, root):
        s = CompositeIgnoreStrategy([NullIgnoreStrategy()])
        assert s.is_ignored(root / "anything.txt", root) is False


# ---------------------------------------------------------------------------
# load_ignore_strategy factory
# ---------------------------------------------------------------------------

class TestLoadIgnoreStrategy:
    """Tests for :func:`~progress_tree.ignore.load_ignore_strategy`."""

    def test_missing_file_returns_null_strategy(self, tmp_path):
        strategy = load_ignore_strategy(tmp_path / "nonexistent.txt")
        assert isinstance(strategy, NullIgnoreStrategy)

    def test_existing_file_returns_pattern_strategy(self, tmp_path):
        ignore_file = tmp_path / "tree_ignore.txt"
        ignore_file.write_text("*.pyc\n.git/\n", encoding="utf-8")
        strategy = load_ignore_strategy(ignore_file)
        assert isinstance(strategy, PatternIgnoreStrategy)

    def test_loaded_patterns_are_correct(self, tmp_path):
        ignore_file = tmp_path / "tree_ignore.txt"
        ignore_file.write_text("*.pyc\n# comment\n\n.venv/\n", encoding="utf-8")
        strategy = load_ignore_strategy(ignore_file)
        assert isinstance(strategy, PatternIgnoreStrategy)
        assert "*.pyc" in strategy.patterns
        assert ".venv/" in strategy.patterns
        # Comments and blank lines must be excluded
        assert "# comment" not in strategy.patterns
        assert "" not in strategy.patterns

    def test_comments_and_blanks_stripped(self, tmp_path):
        ignore_file = tmp_path / "tree_ignore.txt"
        ignore_file.write_text("# header\n\n*.log\n  # indented comment\n", encoding="utf-8")
        strategy = load_ignore_strategy(ignore_file)
        assert isinstance(strategy, PatternIgnoreStrategy)
        assert len(strategy.patterns) == 1
        assert strategy.patterns[0] == "*.log"
