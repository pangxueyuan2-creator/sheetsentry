from __future__ import annotations

import csv
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from sheetsentry.cli import run
from sheetsentry.inspect import inspect_file, is_formula_like
from sheetsentry.models import SanitizationOptions
from sheetsentry.reader import InputError
from sheetsentry.sanitize import sanitize_file

FIXTURES = Path(__file__).parent / "fixtures"


class FormulaDetectionTests(unittest.TestCase):
    def test_detects_ascii_and_full_width_formula_prefixes(self) -> None:
        for value in ("=1+1", "+SUM(A1)", "-1", "@SUM(A1)", "  \uff1d1+1", "\t+1"):
            self.assertTrue(is_formula_like(value))
        self.assertFalse(is_formula_like("plain text"))
        self.assertFalse(is_formula_like("  plain text"))


class InspectionTests(unittest.TestCase):
    def test_inspect_finds_quality_and_safety_issues(self) -> None:
        report = inspect_file(FIXTURES / "messy_contacts.csv")
        summary = report.summary
        self.assertEqual(summary.column_count, 4)
        self.assertEqual(summary.data_row_count, 6)
        self.assertEqual(summary.blank_row_count, 1)
        self.assertEqual(summary.ragged_row_count, 1)
        self.assertEqual(summary.duplicate_row_count, 1)
        self.assertEqual(summary.formula_like_cell_count, 4)
        self.assertGreaterEqual(summary.potential_pii_cell_count, 4)
        codes = {issue.code for issue in report.issues}
        self.assertTrue(
            {
                "duplicate-header",
                "blank-row",
                "ragged-row",
                "duplicate-row",
                "formula-like-cell",
                "potential-pii",
            }.issubset(codes)
        )

    def test_detects_tab_delimited_file_and_json_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "items.tsv"
            path.write_text("item\tquantity\nwidget\t2\n", encoding="utf-8")
            report = inspect_file(path)
        self.assertEqual(report.summary.delimiter, "\t")
        self.assertEqual(report.to_dict()["schema_version"], "1.0")

    def test_rejects_unsupported_encoding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.csv"
            path.write_bytes(b"name\n\xff\n")
            with self.assertRaises(InputError):
                inspect_file(path)

    def test_blank_only_file_reports_missing_header_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "blank.csv"
            path.write_bytes(b"\n")
            report = inspect_file(path)
        self.assertEqual([issue.code for issue in report.issues], ["empty-file"])
        self.assertEqual(report.summary.column_count, 0)
        self.assertEqual(report.summary.total_row_count, 0)

    def test_multiple_blank_lines_report_missing_header_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "blanks.csv"
            path.write_bytes(b"\n\n")
            report = inspect_file(path)
        self.assertEqual([issue.code for issue in report.issues], ["empty-file"])

    def test_whitespace_only_line_reports_missing_header_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "spaces.csv"
            path.write_bytes(b"  \t\n")
            report = inspect_file(path)
        self.assertEqual([issue.code for issue in report.issues], ["empty-file"])

    def test_refuses_blank_only_input_without_header_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "blank.csv"
            source.write_bytes(b"\n")
            output = Path(directory) / "clean.csv"
            with self.assertRaises(InputError):
                sanitize_file(source, output, SanitizationOptions(trim=True))
            self.assertFalse(output.exists())


class SanitizationTests(unittest.TestCase):
    def test_sanitize_writes_separate_auditable_output(self) -> None:
        source = FIXTURES / "messy_contacts.csv"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "clean.csv"
            audit = sanitize_file(
                source,
                output,
                SanitizationOptions(
                    trim=True,
                    drop_blank_rows=True,
                    dedupe=True,
                    normalize_headers=True,
                    formula_policy="apostrophe",
                ),
            )
            with output.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
            output_report = inspect_file(output)

        self.assertEqual(rows[0], ["name", "name_2", "email", "note"])
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[1][0], "Alice")
        self.assertEqual(rows[1][3], '\'=HYPERLINK("https://example.test","Open")')
        self.assertEqual(rows[3][3], "'@SUM(1,2)")
        self.assertEqual(audit.modifications["blank_rows_dropped"], 1)
        self.assertEqual(audit.modifications["duplicate_rows_dropped"], 1)
        self.assertEqual(audit.modifications["formula_cells_prefixed"], 4)
        self.assertEqual(output_report.summary.formula_like_cell_count, 0)
        self.assertEqual(
            source.read_text(encoding="utf-8"),
            (FIXTURES / "messy_contacts.csv").read_text(encoding="utf-8"),
        )

    def test_refuses_output_equal_to_input(self) -> None:
        source = FIXTURES / "messy_contacts.csv"
        with self.assertRaises(InputError):
            sanitize_file(source, source, SanitizationOptions(trim=True))

    def test_refuses_existing_output_without_force(self) -> None:
        source = FIXTURES / "messy_contacts.csv"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "existing.csv"
            output.write_text("preserve me", encoding="utf-8")
            with self.assertRaises(InputError):
                sanitize_file(source, output, SanitizationOptions(trim=True))
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve me")


class HeaderFormulaInjectionTests(unittest.TestCase):
    def test_sanitize_neutralizes_formula_like_headers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "evil_headers.csv"
            source.write_text(
                'name,"=HYPERLINK(""http://evil.test"",""x"")","@SUM(1,2)"\nalice,1,2\n',
                encoding="utf-8",
            )
            output = Path(directory) / "clean.csv"
            audit = sanitize_file(source, output, SanitizationOptions(formula_policy="apostrophe"))
            with output.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
            output_report = inspect_file(output)

        self.assertEqual(
            rows[0],
            ["name", '\'=HYPERLINK("http://evil.test","x")', "'@SUM(1,2)"],
        )
        self.assertEqual(audit.modifications["formula_cells_prefixed"], 2)
        self.assertEqual(output_report.summary.formula_like_cell_count, 0)

    def test_inspect_reports_formula_like_headers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evil_headers.csv"
            path.write_text(
                'name,"=HYPERLINK(""http://evil.test"",""x"")"\nalice,1\n',
                encoding="utf-8",
            )
            report = inspect_file(path)
        codes = {issue.code for issue in report.issues}
        self.assertIn("formula-like-header", codes)
        self.assertEqual(report.summary.formula_like_cell_count, 0)


class CommandLineTests(unittest.TestCase):
    def _run_quietly(self, arguments: list[str]) -> tuple[int, str, str]:
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = run(arguments)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_validate_returns_nonzero_when_threshold_is_met(self) -> None:
        code, stdout, stderr = self._run_quietly(
            ["validate", str(FIXTURES / "messy_contacts.csv"), "--fail-on", "warning"]
        )
        self.assertEqual(code, 1)
        self.assertIn("formula-like-cell", stdout)
        self.assertEqual(stderr, "")

    def test_inspect_json_is_machine_readable(self) -> None:
        code, stdout, stderr = self._run_quietly(
            ["inspect", str(FIXTURES / "messy_contacts.csv"), "--format", "json"]
        )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout)["summary"]["data_row_count"], 6)

    def test_sanitize_requires_an_explicit_transformation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "clean.csv"
            code, _stdout, stderr = self._run_quietly(
                ["sanitize", str(FIXTURES / "messy_contacts.csv"), "--output", str(output)]
            )
        self.assertEqual(code, 2)
        self.assertIn("No transformation selected", stderr)


if __name__ == "__main__":
    unittest.main()
