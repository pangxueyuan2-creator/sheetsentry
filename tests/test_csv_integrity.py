from __future__ import annotations

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
