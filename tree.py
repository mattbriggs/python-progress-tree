#!/usr/bin/env python3
"""
tree.py

Generates an ASCII tree representation of the current project directory and
writes a detailed report to a timestamped text file in the repository root.

Features:
- Reads ignore patterns from tree_ignore.txt (gitignore-style)
- Skips virtual environments, build artifacts, and other noise
- Shows live progress while scanning
- Prevents infinite recursion and symlink loops
- Produces:
  1. ASCII directory tree
  2. File and directory counts
  3. Estimated project size
  4. Total lines of code
  5. Timestamped audit record

This exists so you can *see* your architecture before you change it.
"""

from __future__ import annotations

import fnmatch
import time
from datetime import datetime
from pathlib import Path
from typing import List

# ------------------------------------------------------------
# Ignore handling
# ------------------------------------------------------------

def load_ignore_patterns(ignore_file: Path) -> List[str]:
    if not ignore_file.exists():
        return []

    patterns = []
    for line in ignore_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def is_ignored(path: Path, patterns: List[str], root: Path) -> bool:
    rel = path.relative_to(root).as_posix()

    for pattern in patterns:
        # Directory ignore
        if pattern.endswith("/") and rel.startswith(pattern[:-1]):
            return True

        # Glob ignore
        if fnmatch.fnmatch(rel, pattern):
            return True

    return False


# ------------------------------------------------------------
# Tree building and metrics
# ------------------------------------------------------------

file_count = 0
dir_count = 0
line_count = 0


def build_tree(path: Path, root: Path, ignore: List[str], prefix: str = "") -> List[str]:
    global file_count, dir_count, line_count

    lines = []

    try:
        entries = sorted(
            [
                e for e in path.iterdir()
                if not e.is_symlink() and not is_ignored(e, ignore, root)
            ],
            key=lambda p: (p.is_file(), p.name.lower()),
        )
    except PermissionError:
        return lines

    for index, entry in enumerate(entries):
        connector = "└── " if index == len(entries) - 1 else "├── "
        lines.append(f"{prefix}{connector}{entry.name}")

        if entry.is_dir():
            dir_count += 1
            extension = "    " if index == len(entries) - 1 else "│   "
            lines.extend(build_tree(entry, root, ignore, prefix + extension))
        else:
            file_count += 1
            try:
                with entry.open("r", encoding="utf-8", errors="ignore") as f:
                    line_count += sum(1 for _ in f)
            except Exception:
                pass

        # live heartbeat every ~200 files
        if file_count % 200 == 0 and file_count > 0:
            print(f"Scanning… {file_count} files, {dir_count} dirs, {line_count} lines")

    return lines


# ------------------------------------------------------------
# Main execution
# ------------------------------------------------------------

def main() -> None:
    global file_count, dir_count, line_count

    root = Path.cwd()
    ignore_file = root / "tree_ignore.txt"
    ignore_patterns = load_ignore_patterns(ignore_file)

    print("\nProject tree scan starting…")
    print("Ignore patterns loaded:", len(ignore_patterns))
    print("Root:", root)
    print("-" * 60)

    start = time.time()

    tree_lines = [root.name]
    tree_lines.extend(build_tree(root, root, ignore_patterns))

    elapsed = time.time() - start

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = root / f"project_tree_{timestamp}.txt"

    report = []
    report.append(f"Project Tree Report")
    report.append(f"Generated: {datetime.now().isoformat()}")
    report.append(f"Root: {root}")
    report.append("")
    report.append("ASCII TREE")
    report.append("=" * 60)
    report.extend(tree_lines)
    report.append("")
    report.append("PROJECT METRICS")
    report.append("=" * 60)
    report.append(f"Directories: {dir_count}")
    report.append(f"Files:       {file_count}")
    report.append(f"Lines of code: {line_count}")
    report.append(f"Scan time:    {elapsed:.2f} seconds")
    report.append("")
    report.append("Interpretation:")
    report.append(
        "This is a structural snapshot of your repository. "
        "It reflects architecture, complexity, and surface area. "
        "If this feels large, it’s because the project is doing real work."
    )

    output_file.write_text("\n".join(report), encoding="utf-8")

    print("\nScan complete.")
    print(f"Files: {file_count}")
    print(f"Dirs: {dir_count}")
    print(f"Lines: {line_count}")
    print(f"Time: {elapsed:.2f}s")
    print(f"Report written to: {output_file}\n")


if __name__ == "__main__":
    main()