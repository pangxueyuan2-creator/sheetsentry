from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from sheetsentry.cli import run
from sheetsentry.inspect import inspect_file
from sheetsentry.models import SanitizationOptions
from sheetsentry.reader import InputError
from sheetsentry.sanitize import sanitize_file


class CsvIntegrityTests(unittest.TestCase):
    def test_unicode_json_and_text_output_under_legacy_pipe_encoding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source😀.csv"
            source.write_text("name😀,note\nAlice,中文😀\n", encoding="utf-8")
            environment = os.environ.copy()
            environment.update(PYTHONUTF8="0", PYTHONIOENCODING="gbk:strict")
            for report_format in ("json", "text"):
                with self.subTest(report_format=report_format):
                    completed = subprocess.run(
                        [
                            sys.executable,
                            "-c",
                            "from sheetsentry.cli import main; main()",
                            "inspect",
                            str(source),
                            "--format",
                            report_format,
                        ],
                        capture_output=True,
                        env=environment,
                        check=False,
                        timeout=20,
                    )
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertEqual(completed.stderr, b"")
                    if report_format == "json":
                        self.assertEqual(
                            json.loads(completed.stdout)["headers"], ["name😀", "note"]
                        )
                    else:
                        self.assertIn("\\U0001f600", completed.stdout.decode("gbk"))

    def test_source_change_between_reads_preserves_target_and_rejects_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.csv"
            source.write_bytes(b"name\nAlice\n")
            output = Path(directory) / "output.csv"
            output.write_bytes(b"previous output")

            def inspect_then_change(path: Path, delimiter: str | None = None):
                report = inspect_file(path, delimiter)
                source.write_bytes(b"name\nBob\nCarol\n")
                return report

            with (
                patch("sheetsentry.sanitize.inspect_file", side_effect=inspect_then_change),
                self.assertRaisesRegex(InputError, "Input changed"),
            ):
                sanitize_file(source, output, SanitizationOptions(trim=True, force=True))
            self.assertEqual(output.read_bytes(), b"previous output")
            self.assertFalse(list(Path(directory).glob("*.tmp")))

    @unittest.skipUnless(os.name == "nt", "Windows sharing-lock semantics")
    def test_locked_temp_never_publishes_output_and_reports_recovery_path(self) -> None:
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        handles = []
        rename = os.rename

        def lock_before_rename(source: str, destination: Path) -> None:
            handle = kernel.CreateFileW(source, 0x80000000, 3, None, 3, 0x80, None)
            if handle == wintypes.HANDLE(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            handles.append(handle)
            rename(source, destination)

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.csv"
            source.write_bytes(b"name\n Alice \n")
            output = Path(directory) / "output.csv"
            stdout, stderr = StringIO(), StringIO()
            try:
                with (
                    patch("sheetsentry.sanitize.os.rename", side_effect=lock_before_rename),
                    redirect_stdout(stdout),
                    redirect_stderr(stderr),
                ):
                    code = run(["sanitize", str(source), "--output", str(output), "--trim"])
                self.assertEqual(code, 2)
                self.assertFalse(output.exists())
                self.assertEqual(stdout.getvalue(), "")
                self.assertIn("release external file locks", stderr.getvalue())
                leftovers = list(Path(directory).glob("*.tmp"))
                self.assertEqual(len(leftovers), 1)
                self.assertIn(str(leftovers[0]), stderr.getvalue())
                self.assertEqual(source.read_bytes(), b"name\n Alice \n")
            finally:
                for handle in handles:
                    kernel.CloseHandle(handle)
                for temporary in Path(directory).glob("*.tmp"):
                    temporary.unlink()

    def test_known_comma_format_rejects_damage_that_another_dialect_accepts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "ambiguous.csv"
            source.write_bytes(b'name,note;tag\nAlice,"un,finished;tag\nBob,second;tag\n')
            automatic = inspect_file(source)
            self.assertEqual(automatic.summary.delimiter, ";")
            with self.assertRaisesRegex(InputError, "Malformed delimited text"):
                inspect_file(source, ",")

    def test_filesystem_failure_is_a_cli_input_error_and_preserves_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.csv"
            source.write_bytes(b"name\n Alice \n")
            output = Path(directory) / "output.csv"
            output.write_bytes(b"previous output")
            stdout, stderr = StringIO(), StringIO()
            with (
                patch(
                    "sheetsentry.sanitize.os.replace", side_effect=PermissionError("file locked")
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                code = run(["sanitize", str(source), "--output", str(output), "--trim", "--force"])
            self.assertEqual(code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("Unable to publish", stderr.getvalue())
            self.assertEqual(output.read_bytes(), b"previous output")
            self.assertEqual(
                sorted(path.name for path in Path(directory).iterdir()),
                ["output.csv", "source.csv"],
            )

    def test_rejects_unterminated_or_invalid_quoted_cells(self) -> None:
        for text in ('name,note\nAlice,"unfinished\nBob,second\n', 'name\n"Alice"suffix\n'):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "source.csv"
                source.write_text(text, encoding="utf-8")
                with self.assertRaisesRegex(InputError, "Malformed delimited text"):
                    inspect_file(source, ",")

    def test_valid_multiline_and_escaped_quotes_remain_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.csv"
            source.write_text('name,note\nAlice,"first\nsecond ""quoted"""\n', encoding="utf-8")
            report = inspect_file(source, ",")
        self.assertEqual(report.summary.data_row_count, 1)
        self.assertEqual(report.summary.ragged_row_count, 0)

    def test_malformed_sanitize_preserves_source_and_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.csv"
            original = b'name,note\nAlice,"unfinished\n'
            source.write_bytes(original)
            output = Path(directory) / "output.csv"
            output.write_bytes(b"previous output")
            with self.assertRaises(InputError):
                sanitize_file(source, output, SanitizationOptions(trim=True, force=True))
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(output.read_bytes(), b"previous output")
            self.assertEqual(
                sorted(path.name for path in Path(directory).iterdir()),
                ["output.csv", "source.csv"],
            )

    def test_cli_returns_input_error_instead_of_malformed_success_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.csv"
            source.write_text('name\n"unfinished\n', encoding="utf-8")
            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = run(["validate", str(source), "--delimiter", ",", "--format", "json"])
        self.assertEqual(code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Malformed delimited text", stderr.getvalue())

    def test_no_force_does_not_replace_output_created_during_sanitization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.csv"
            source.write_bytes(b"name\n Alice \n")
            output = Path(directory) / "output.csv"
            with (
                patch(
                    "sheetsentry.sanitize.os.fsync",
                    side_effect=lambda _descriptor: output.write_bytes(b"concurrent output"),
                ),
                self.assertRaisesRegex(InputError, "Refusing to overwrite"),
            ):
                sanitize_file(source, output, SanitizationOptions(trim=True))
            self.assertEqual(output.read_bytes(), b"concurrent output")
            self.assertEqual(source.read_bytes(), b"name\n Alice \n")
            self.assertEqual(
                sorted(path.name for path in Path(directory).iterdir()),
                ["output.csv", "source.csv"],
            )

    def test_force_can_replace_output_created_during_sanitization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.csv"
            source.write_bytes(b"name\n Alice \n")
            output = Path(directory) / "output.csv"
            with patch(
                "sheetsentry.sanitize.os.fsync",
                side_effect=lambda _descriptor: output.write_bytes(b"concurrent output"),
            ):
                sanitize_file(source, output, SanitizationOptions(trim=True, force=True))
            self.assertEqual(output.read_bytes(), b"name\r\nAlice\r\n")
