# Design Document — progress-tree

## Overview

`progress-tree` started as a single-file utility (`tree.py`) that walked a
directory and wrote an ASCII tree report.  This document describes the
architecture of the refactored package, the design patterns applied, the
reasoning behind each decision, and a module-by-module reference.

---

## Goals

| Goal | Rationale |
|------|-----------|
| Testable units | Each concern is isolated into a class/module that can be exercised independently with pytest. |
| Extensible ignore system | New ignore strategies (e.g. `.gitignore` parsing, remote rules) can be added without touching scan logic. |
| Separation of scan and output | Scanning produces a data structure; reporting consumes it.  They are never coupled. |
| Zero external dependencies | The tool runs anywhere Python 3.10+ is installed. |
| Full CLI | All behaviour is configurable at the command line without editing code. |

---

## Package Layout

```
progress_tree/
├── __init__.py     Public API surface + __version__
├── cli.py          Command-line interface (argparse)
├── ignore.py       Ignore-pattern Strategy hierarchy
├── models.py       ScanMetrics and ScanResult dataclasses
├── reporter.py     ReportBuilder (Builder pattern)
└── scanner.py      TreeScanner (recursive walk)
```

---

## Design Patterns

### 1. Strategy — `ignore.py`

**Problem:** The original script had a single `is_ignored()` function baked
directly into the tree walk.  Adding a new kind of ignore rule (e.g.
`.gitignore` parsing, regex patterns, remote blocklist) would require editing
`build_tree()`.

**Solution:** An `IgnoreStrategy` abstract base class with a single method:

```python
def is_ignored(self, path: Path, root: Path) -> bool: ...
```

Concrete implementations:

| Class | Behaviour |
|-------|-----------|
| `NullIgnoreStrategy` | Never ignores; safe default. |
| `PatternIgnoreStrategy` | Matches against a list of gitignore-style patterns. |
| `CompositeIgnoreStrategy` | Logical-OR chain of any number of strategies. |

`TreeScanner` accepts any `IgnoreStrategy` instance through its constructor.
This makes the scanner completely unaware of _how_ ignore decisions are made.

Adding a new strategy requires only a new class that satisfies the abstract
interface — no changes to scanner or CLI.

---

### 2. Builder — `reporter.py`

**Problem:** The original script assembled the report with a list of strings
and a series of `report.append(...)` calls interleaved with business logic.
The report structure was implicit and untestable.

**Solution:** `ReportBuilder` accumulates named sections through fluent setter
methods and defers rendering to a single `build()` call:

```python
report = (
    ReportBuilder()
    .set_header(root, timestamp)
    .set_tree(tree_lines, root_label)
    .set_metrics(metrics)
    .set_interpretation()
    .build()
)
```

Benefits:
- Each section is a discrete, independently testable unit.
- Callers can omit sections they do not need.
- Custom sections can be appended with `add_section(title, lines)`.
- The builder itself holds no I/O; it returns a pure string.

---

### 3. Dataclass models — `models.py`

**Problem:** The original script used three module-level mutable globals
(`file_count`, `dir_count`, `line_count`).  This made re-entrant calls
impossible and testing unreliable.

**Solution:** `ScanMetrics` is a `@dataclass` whose fields are updated through
named mutation methods:

```python
metrics.update_file(lines=42)  # increments file_count, adds to line_count
metrics.update_dir()           # increments dir_count
```

`ScanResult` bundles the root path, tree lines, and metrics into a single
return value.  Every call to `TreeScanner.scan()` creates a fresh
`ScanMetrics`, so multiple scans on the same instance produce independent
results.

---

## Module Reference

### `models.py`

| Symbol | Kind | Purpose |
|--------|------|---------|
| `ScanMetrics` | dataclass | Counters: files, dirs, lines, elapsed seconds. |
| `ScanResult` | dataclass | Return value of `TreeScanner.scan()`. |

---

### `ignore.py`

| Symbol | Kind | Purpose |
|--------|------|---------|
| `IgnoreStrategy` | ABC | Abstract contract for ignore decisions. |
| `NullIgnoreStrategy` | class | Always returns `False`. |
| `PatternIgnoreStrategy` | class | Gitignore-style pattern matching. |
| `CompositeIgnoreStrategy` | class | OR-chain of child strategies. |
| `load_ignore_strategy()` | function | Factory: reads a file, returns a strategy. |

**Pattern matching rules** (evaluated in priority order):

1. Directory prefix — pattern ends with `/`, matches path prefix.
2. Full-path glob — `fnmatch` against the complete relative POSIX path.
3. Name-only glob — `fnmatch` against the bare file or directory name.

---

### `scanner.py`

| Symbol | Kind | Purpose |
|--------|------|---------|
| `TreeScanner` | class | Recursive directory walk, tree rendering, metrics collection. |
| `ProgressCallback` | type alias | `Callable[[ScanMetrics], None]` — signature for progress hooks. |

**Constructor parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `root` | `Path` | `Path.cwd()` | Directory to scan. |
| `ignore_strategy` | `IgnoreStrategy` | `NullIgnoreStrategy()` | Determines which entries to skip. |
| `progress_interval` | `int` | `200` | Fire callback every N files. |
| `progress_callback` | `ProgressCallback \| None` | `None` | Invoked at each interval. |
| `count_lines` | `bool` | `True` | When `False`, line counting is skipped. |

`scan()` is stateless across calls: no instance variables are mutated.

---

### `reporter.py`

| Symbol | Kind | Purpose |
|--------|------|---------|
| `ReportBuilder` | class | Fluent builder for assembling the plain-text report. |

**Methods:**

| Method | Adds Section |
|--------|-------------|
| `set_header(root, timestamp)` | Title, timestamp, root path. |
| `set_tree(lines, root_label)` | ASCII TREE section. |
| `set_metrics(metrics)` | PROJECT METRICS section. |
| `set_interpretation()` | INTERPRETATION note. |
| `add_section(title, lines)` | Any custom section. |
| `build()` | Renders and returns the full string. |

---

### `cli.py`

| Symbol | Kind | Purpose |
|--------|------|---------|
| `build_parser()` | function | Constructs the `argparse.ArgumentParser`. |
| `configure_logging()` | function | Configures root logger (level + optional file handler). |
| `main(argv)` | function | Orchestrates parse → scan → report → write. Entry point. |

**Exit codes:**

| Code | Meaning |
|------|---------|
| `0` | Success. |
| `1` | Runtime error (bad root, unwritable output file). |
| `2` | Argument parsing error (argparse default). |

---

## Data Flow

```
CLI (cli.py)
    │
    ├── load_ignore_strategy(ignore_file)     → IgnoreStrategy
    │       (ignore.py)
    │
    ├── TreeScanner(root, ignore_strategy)
    │       .scan()                           → ScanResult
    │       (scanner.py)
    │           │
    │           └── is_ignored(path, root)    ← IgnoreStrategy
    │
    └── ReportBuilder()
            .set_header(...)
            .set_tree(result.tree_lines)
            .set_metrics(result.metrics)
            .build()                          → str
            (reporter.py)
                │
                └── write to file  or  print to stdout
```

---

## Key Decisions

### Why no external dependencies?

The tool is meant to run on any machine with Python 3.10+, including
restricted environments (CI, read-only containers, minimal Docker images).
All functionality (`fnmatch`, `argparse`, `logging`, `pathlib`, `dataclasses`)
is available in the standard library.

### Why Strategy instead of a simple function?

A plain `is_ignored(path, patterns)` function would work for the current use
case.  The Strategy class hierarchy costs very little and provides a clear
extension point: a future `GitignoreStrategy` (using `pathspec`) or a
`RegexIgnoreStrategy` can be dropped in without touching any other module.

### Why Builder instead of a template string?

Report structure changes frequently during development: sections get added,
reordered, or made conditional.  A builder makes each section independently
testable and composable.  A large f-string would require editing one monolithic
block for every structural change.

### Why are metrics a dataclass with mutation methods rather than a namedtuple?

`ScanMetrics` is accumulated incrementally during the walk.  Immutable
structures (namedtuple, frozen dataclass) would require creating a new object
for every file encountered.  Named mutation methods (`update_file`,
`update_dir`) communicate intent clearly at call sites.

### Why does `scan()` create fresh metrics each call?

This makes `TreeScanner` instances reusable and the test suite straightforward:
each test invocation gets a clean slate without having to reset any state.

---

## Testing Strategy

Tests are in `tests/` and require only `pytest`.

| File | What it tests |
|------|---------------|
| `test_models.py` | Dataclass defaults, mutation methods, instance independence. |
| `test_ignore.py` | All three strategy classes, factory function, edge cases. |
| `test_scanner.py` | File/dir/line counts, ignore integration, symlink handling, progress callback. |
| `test_reporter.py` | All builder sections, fluent chaining, section ordering. |
| `test_cli.py` | Argument defaults, flag parsing, `main()` return codes, file output, stdout mode. |

All tests use `tmp_path` (pytest built-in) to avoid touching the real
filesystem outside a temporary directory.

```bash
# Run full suite with coverage
pytest --cov=progress_tree --cov-report=term-missing
```

---

## Future Extensions

| Idea | Where to add it |
|------|-----------------|
| `.gitignore`-aware ignore | New `GitignoreStrategy` in `ignore.py` |
| JSON / Markdown report formats | New `JsonReportBuilder` / `MarkdownReportBuilder` in `reporter.py` |
| Parallel scanning | `concurrent.futures` inside `TreeScanner._walk` |
| File-type breakdown | Additional field on `ScanMetrics`, new section in `ReportBuilder` |
| Watch mode (re-scan on change) | New `watch` sub-command in `cli.py` using `watchfiles` |
