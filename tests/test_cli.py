"""
test_cli.py
===========

Unit tests for :mod:`progress_tree.cli`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from progress_tree.cli import build_parser, main


# ---------------------------------------------------------------------------
# build_parser() – argument defaults
# ---------------------------------------------------------------------------

class TestBuildParser:
    """Tests for the argument parser produced by :func:`~progress_tree.cli.build_parser`."""

    def setup_method(self):
        self.parser = build_parser()

    def test_root_defaults_to_none(self):
        args = self.parser.parse_args([])
        assert args.root is None

    def test_output_defaults_to_none(self):
        args = self.parser.parse_args([])
        assert args.output is None

    def test_ignore_file_defaults_to_none(self):
        args = self.parser.parse_args([])
        assert args.ignore_file is None

    def test_log_level_defaults_to_warning(self):
        args = self.parser.parse_args([])
        assert args.log_level == "WARNING"

    def test_stdout_defaults_to_false(self):
        args = self.parser.parse_args([])
        assert args.stdout is False

    def test_quiet_defaults_to_false(self):
        args = self.parser.parse_args([])
        assert args.quiet is False

    def test_no_lines_defaults_to_false(self):
        args = self.parser.parse_args([])
        assert args.no_lines is False

    def test_progress_interval_defaults_to_200(self):
        args = self.parser.parse_args([])
        assert args.progress_interval == 200

    # ---- Explicit values -----------------------------------------------

    def test_root_long_flag(self, tmp_path):
        args = self.parser.parse_args(["--root", str(tmp_path)])
        assert args.root == tmp_path

    def test_root_short_flag(self, tmp_path):
        args = self.parser.parse_args(["-r", str(tmp_path)])
        assert args.root == tmp_path

    def test_output_long_flag(self, tmp_path):
        out = tmp_path / "report.txt"
        args = self.parser.parse_args(["--output", str(out)])
        assert args.output == out

    def test_output_short_flag(self, tmp_path):
        out = tmp_path / "report.txt"
        args = self.parser.parse_args(["-o", str(out)])
        assert args.output == out

    def test_log_level_debug(self):
        args = self.parser.parse_args(["--log-level", "DEBUG"])
        assert args.log_level == "DEBUG"

    def test_log_level_short_flag(self):
        args = self.parser.parse_args(["-l", "INFO"])
        assert args.log_level == "INFO"

    def test_invalid_log_level_raises(self):
        with pytest.raises(SystemExit):
            self.parser.parse_args(["--log-level", "VERBOSE"])

    def test_stdout_flag(self):
        args = self.parser.parse_args(["--stdout"])
        assert args.stdout is True

    def test_quiet_long_flag(self):
        args = self.parser.parse_args(["--quiet"])
        assert args.quiet is True

    def test_quiet_short_flag(self):
        args = self.parser.parse_args(["-q"])
        assert args.quiet is True

    def test_no_lines_flag(self):
        args = self.parser.parse_args(["--no-lines"])
        assert args.no_lines is True

    def test_progress_interval_flag(self):
        args = self.parser.parse_args(["--progress-interval", "50"])
        assert args.progress_interval == 50

    def test_ignore_file_flag(self, tmp_path):
        f = tmp_path / "custom_ignore.txt"
        args = self.parser.parse_args(["--ignore-file", str(f)])
        assert args.ignore_file == f


# ---------------------------------------------------------------------------
# main() – integration
# ---------------------------------------------------------------------------

class TestMain:
    """Integration tests for :func:`~progress_tree.cli.main`."""

    def test_returns_zero_on_success(self, tmp_path):
        (tmp_path / "file.py").write_text("x = 1\n", encoding="utf-8")
        code = main(["--root", str(tmp_path), "--stdout", "--quiet"])
        assert code == 0

    def test_returns_one_for_nonexistent_root(self, tmp_path):
        bad = tmp_path / "does_not_exist"
        code = main(["--root", str(bad), "--quiet"])
        assert code == 1

    def test_returns_one_for_file_as_root(self, tmp_path):
        f = tmp_path / "notadir.txt"
        f.write_text("hello\n", encoding="utf-8")
        code = main(["--root", str(f), "--quiet"])
        assert code == 1

    def test_writes_report_file(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("pass\n", encoding="utf-8")
        output = tmp_path / "report.txt"
        code = main(["--root", str(tmp_path), "--output", str(output), "--quiet"])
        assert code == 0
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "Project Tree Report" in content

    def test_stdout_mode_prints_to_stdout(self, tmp_path, capsys):
        (tmp_path / "a.py").write_text("pass\n", encoding="utf-8")
        code = main(["--root", str(tmp_path), "--stdout", "--quiet"])
        assert code == 0
        captured = capsys.readouterr()
        assert "Project Tree Report" in captured.out

    def test_no_file_created_in_stdout_mode(self, tmp_path):
        (tmp_path / "a.py").write_text("pass\n", encoding="utf-8")
        main(["--root", str(tmp_path), "--stdout", "--quiet"])
        txt_files = list(tmp_path.glob("project_tree_*.txt"))
        assert len(txt_files) == 0

    def test_report_contains_metrics(self, tmp_path):
        (tmp_path / "hello.py").write_text("a\nb\nc\n", encoding="utf-8")
        output = tmp_path / "out.txt"
        main(["--root", str(tmp_path), "--output", str(output), "--quiet"])
        content = output.read_text(encoding="utf-8")
        assert "PROJECT METRICS" in content
        assert "Files" in content

    def test_no_lines_flag_sets_zero_line_count(self, tmp_path, capsys):
        (tmp_path / "big.py").write_text("line\n" * 100, encoding="utf-8")
        code = main(["--root", str(tmp_path), "--stdout", "--quiet", "--no-lines"])
        assert code == 0
        captured = capsys.readouterr()
        # Line count should be 0 when --no-lines is passed
        assert "Lines of code : 0" in captured.out

    def test_ignore_file_is_respected(self, tmp_path):
        (tmp_path / "keep.py").write_text("x\n", encoding="utf-8")
        (tmp_path / "ignore.log").write_text("noise\n", encoding="utf-8")
        ignore_file = tmp_path / "my_ignore.txt"
        ignore_file.write_text("*.log\n", encoding="utf-8")
        output = tmp_path / "report.txt"
        main([
            "--root", str(tmp_path),
            "--ignore-file", str(ignore_file),
            "--output", str(output),
            "--quiet",
        ])
        content = output.read_text(encoding="utf-8")
        assert "ignore.log" not in content
        assert "keep.py" in content
