# Tree Generator Utility

This script generates an ASCII tree representation of a project directory, writes it to a timestamped text file, and appends a summary report including file counts and total lines of code.

It exists to answer three questions quickly and reliably:
 1.	What is actually in this project?
 2.	How big is it?
 3.	What should be ignored so I don't waste time on noise?

It is intentionally boring.

What It Does

Given a root directory, the script:
 - Recursively walks the filesystem
 - Builds a clean ASCII tree
 - Skips ignored files and directories (like .gitignore)
 - 	Writes output to a timestamped text file in the working repo
 - Produces:
	- Project tree
	- File and directory counts
	- Total lines of code
	- Basic size estimation

## Why This Exists

Every real project eventually reaches the point where:
 - ls -R is unreadable
 - 	IDE trees lie by omission
 - Humans forget what they've built
 - AI forgets what is has built forget what it has built

This script gives you:
 - A snapshot of reality
 - A permanent artifact you can version
 - Something you can paste into documentation or ChatGPT without guesswork


## Output Example

The generated file will look roughly like:

```txt
Project Tree:
├── src
│   ├── main.py
│   └── utils.py
├── tests
│   └── test_main.py
└── pyproject.toml

Summary:
Directories: 12
Files: 84
Python files: 37
Total lines of code: 9,214
Generated: 2026-01-10 21:34:55
```

The exact format depends on configuration, but the structure is stable.


Ignore System

The script supports a tree_ignore.txt file in the project root.

This behaves like .gitignore.

Example:

```txt
.venv
__pycache__
node_modules
.site
.pytest_cache
*.log
```

Anything matching these patterns is skipped.

This keeps the tree meaningful instead of polluted.


## Usage

From the project root:

python tree.py

By default it:
 - Scans the current directory
 - Reads tree_ignore.txt if present
 - Writes output to something like: `project_tree_2026-01-10_21-34-55.txt`

You can safely commit this file or delete it. It has no side effects.

## Design Constraints

This script is intentionally:
 - Single-file
 - Zero dependencies
 - Deterministic
 - Safe to run on large repositories
 - Resistant to infinite loops and symlinks
 - Predictable in output

It is not meant to be clever.
It is meant to be trusted.


Intended Use Cases
 - Project onboarding
 - 	Architectural documentation
 - ChatGPT context sharing
 - Codebase audits
 - Sanity checks before refactors
 - Capturing historical snapshots


## Philosophy

This script is infrastructure for thinking.

It doesn't help you code.
It helps you understand what you already built.