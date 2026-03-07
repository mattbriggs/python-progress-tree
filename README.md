# progress-tree

An ASCII directory tree generator with project metrics.

Recursively walks a filesystem, builds a clean ASCII tree, collects
file/directory/line-count metrics, and writes a timestamped report.

It exists to answer three questions quickly and reliably:

1. What is actually in this project?
2. How big is it?
3. What should be ignored so I do not waste time on noise?

---

## Features

- Recursive ASCII directory tree with box-drawing characters
- File count, directory count, and total lines-of-code metrics
- Gitignore-style ignore patterns via `tree_ignore.txt`
- Symlink-safe (symlinks are silently skipped)
- Live progress heartbeat every N files (configurable)
- Full CLI with `--help`, logging, custom input/output paths
- Zero runtime dependencies (stdlib only)
- Full unit-test suite (pytest)

---

## Installation

```bash
# Clone and install in editable mode
git clone https://github.com/your-org/python-progress-tree.git
cd python-progress-tree
pip install -e ".[dev]"
```

After installation the `progress-tree` command is available on your PATH.

---

## Quick Start

```bash
# Scan the current directory, write a timestamped report file
progress-tree

# Scan a specific directory and print to stdout
progress-tree --root ~/projects/my-app --stdout

# Skip line counting for a faster pass on a large repo
progress-tree --no-lines

# Use a custom ignore file and log at DEBUG level
progress-tree --ignore-file .treeignore --log-level DEBUG

# Write the report to a specific file, suppress the summary banner
progress-tree --output /tmp/tree_report.txt --quiet
```

---

## CLI Reference

```
usage: progress-tree [-h] [--version] [--root DIR] [--output FILE]
                     [--ignore-file FILE] [--no-lines]
                     [--progress-interval N] [--stdout] [--quiet]
                     [--log-level LEVEL] [--log-file FILE]

Generate an ASCII directory tree with project metrics and write a
timestamped report.

input / output:
  --root DIR, -r DIR       Root directory to scan. Defaults to cwd.
  --output FILE, -o FILE   Path for the report file. Defaults to
                           project_tree_<timestamp>.txt in the root.
  --ignore-file FILE, -i FILE
                           Path to the ignore-patterns file (gitignore
                           style). Defaults to <root>/tree_ignore.txt.

scan behaviour:
  --no-lines               Skip line counting. Faster for very large repos.
  --progress-interval N    Print a progress update every N files.
                           Set to 0 to silence. (default: 200)

output mode:
  --stdout                 Print the report to stdout instead of a file.
  --quiet, -q              Suppress the summary banner.

logging:
  --log-level LEVEL, -l LEVEL
                           One of DEBUG | INFO | WARNING | ERROR | CRITICAL.
                           (default: WARNING)
  --log-file FILE          Write log output to FILE instead of stderr.
```

---

## Ignore File

Place a `tree_ignore.txt` file in the root you are scanning (or point to one
with `--ignore-file`).  Syntax is a subset of gitignore:

```text
# Python artefacts
__pycache__/
*.pyc

# Version control
.git/

# Virtual environments
.venv/
venv/

# Build output
dist/
build/
*.egg-info/

# IDE files
.vscode/
.idea/
.DS_Store
```

Rules evaluated in order:

| Rule | Example | Matches |
|------|---------|---------|
| Directory prefix (`/` suffix) | `.git/` | Any path starting with `.git` |
| Full-path glob | `src/*.pyc` | Glob over the full relative path |
| Name-only glob | `*.log` | Glob over the bare file/dir name |

---

## Output Example

```
Project Tree Report
Generated : 2026-03-06T14:22:10
Root      : /Users/matt/projects/my-app

ASCII TREE
============================================================
my-app
├── progress_tree
│   ├── __init__.py
│   ├── cli.py
│   ├── ignore.py
│   ├── models.py
│   ├── reporter.py
│   └── scanner.py
├── tests
│   ├── __init__.py
│   ├── test_cli.py
│   ├── test_ignore.py
│   ├── test_models.py
│   ├── test_reporter.py
│   └── test_scanner.py
├── pyproject.toml
├── README.md
└── tree_ignore.txt

PROJECT METRICS
============================================================
Directories   : 2
Files         : 14
Lines of code : 1,842
Scan time     : 0.04s

INTERPRETATION
============================================================
This is a structural snapshot of your repository...
```

---

## Python API

The package can also be used programmatically:

```python
from pathlib import Path
from progress_tree import TreeScanner, ReportBuilder
from progress_tree.ignore import load_ignore_strategy

strategy = load_ignore_strategy(Path("tree_ignore.txt"))

scanner = TreeScanner(
    root=Path("."),
    ignore_strategy=strategy,
    progress_interval=500,
    count_lines=True,
)

result = scanner.scan()

report = (
    ReportBuilder()
    .set_header(result.root)
    .set_tree(result.tree_lines, root_label=result.root.name)
    .set_metrics(result.metrics)
    .set_interpretation()
    .build()
)

print(report)
print(f"Scanned {result.metrics.file_count} files in {result.metrics.elapsed:.2f}s")
```

---

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=progress_tree --cov-report=term-missing

# Run a specific test file
pytest tests/test_scanner.py -v
```

---

## Project Structure

```
python-progress-tree/
├── progress_tree/
│   ├── __init__.py      Package entry point and public API
│   ├── cli.py           Argparse CLI (progress-tree command)
│   ├── ignore.py        Strategy pattern: ignore-rule matching
│   ├── models.py        ScanMetrics and ScanResult dataclasses
│   ├── reporter.py      Builder pattern: report assembly
│   └── scanner.py       TreeScanner: recursive filesystem walk
├── tests/
│   ├── test_cli.py
│   ├── test_ignore.py
│   ├── test_models.py
│   ├── test_reporter.py
│   └── test_scanner.py
├── tree_ignore.txt      Default ignore patterns
├── pyproject.toml
├── DESIGN.md
└── README.md
```

---

## Design

See [DESIGN.md](DESIGN.md) for a description of the architecture, design
patterns applied, and key decisions.

---

## Philosophy

This tool is infrastructure for thinking.

It does not help you code.  It helps you understand what you already built.
