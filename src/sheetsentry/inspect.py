"""Inspection routines for CSV/TSV files."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from .models import InspectionReport, Issue, Summary
from .policy import is_formula_like, looks_like_pii

_REPORT_SCHEMA_VERSION = "1.0"


def _sample(row: int, column: int, value: str) -> str:
    return f"row {row}, column {column}: {value!r}"


def _issue(
    code: str,
    severity: str,
    message: str,
    count: int,
    *,
    samples: list[str] | None = None,
) -> Issue | None:
    if count <= 0:
        return None
    return Issue(code, severity, message, count=count, samples=samples or [])


def _detect_delimiter(path: Path) -> str:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:8192]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",\t;|").delimiter
    except csv.Error:
        return "\t" if "\t" in sample else ","


def inspect_file(path: Path, delimiter: str | None = None) -> InspectionReport:
    delimiter = delimiter or _detect_delimiter(path)
    issues: list[Issue] = []

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        try:
            headers = next(reader)
        except StopIteration:
            summary = Summary(
                delimiter=delimiter,
                column_count=0,
                data_row_count=0,
                blank_row_count=0,
                blank_cell_count=0,
                duplicate_row_count=0,
                ragged_row_count=0,
                whitespace_cell_count=0,
                formula_like_cell_count=0,
                potential_pii_cell_count=0,
            )
            return InspectionReport(
                schema_version=_REPORT_SCHEMA_VERSION,
                summary=summary,
                headers=[],
                issues=[Issue("empty-file", "error", "The file contains no header row.")],
            )

        normalized_headers = [header.strip().casefold() for header in headers]
        blank_headers = sum(not header for header in normalized_headers)
        duplicate_headers = sum(
            count - 1
            for header, count in Counter(header for header in normalized_headers if header).items()
            if count > 1
        )
        formula_like_headers = [
            (column, header)
            for column, header in enumerate(headers, start=1)
            if is_formula_like(header)
        ]
        for candidate in (
            _issue(
                "blank-header",
                "error",
                "One or more column headers are blank after trimming whitespace.",
                blank_headers,
            ),
            _issue(
                "duplicate-header",
                "error",
                "One or more column headers repeat after case-insensitive normalization.",
                duplicate_headers,
            ),
            _issue(
                "formula-like-header",
                "warning",
                "One or more headers look like spreadsheet formulas. "
                "Spreadsheet applications may execute them.",
                len(formula_like_headers),
                samples=[_sample(1, column, header) for column, header in formula_like_headers][
                    :3
                ],
            ),
        ):
            if candidate:
                issues.append(candidate)

        data_row_count = 0
        blank_row_count = 0
        blank_cell_count = 0
        ragged_row_count = 0
        whitespace_cell_count = 0
        formula_like_cell_count = 0
        potential_pii_cell_count = 0
        duplicate_row_count = 0
        seen_rows: Counter[tuple[str, ...]] = Counter()

        for row_number, row in enumerate(reader, start=2):
            data_row_count += 1
            if not row or all(not cell.strip() for cell in row):
                blank_row_count += 1
            if len(row) != len(headers):
                ragged_row_count += 1

            normalized_row = tuple(cell.strip() for cell in row)
            seen_rows[normalized_row] += 1

            for column, cell in enumerate(row, start=1):
                stripped = cell.strip()
                if not stripped:
                    blank_cell_count += 1
                if cell != stripped and stripped:
                    whitespace_cell_count += 1
                if is_formula_like(stripped):
                    formula_like_cell_count += 1
                if looks_like_pii(stripped):
                    potential_pii_cell_count += 1

        duplicate_row_count = sum(count - 1 for count in seen_rows.values() if count > 1)

    for candidate in (
        _issue(
            "blank-row",
            "warning",
            "One or more data rows are completely blank.",
            blank_row_count,
        ),
        _issue(
            "blank-cell",
            "info",
            "One or more cells are blank after trimming whitespace.",
            blank_cell_count,
        ),
        _issue(
            "duplicate-row",
            "warning",
            "One or more data rows are duplicates after trimming whitespace.",
            duplicate_row_count,
        ),
        _issue(
            "ragged-row",
            "error",
            "One or more data rows have a different number of columns than the header.",
            ragged_row_count,
        ),
        _issue(
            "whitespace-cell",
            "info",
            "One or more cells contain leading or trailing whitespace.",
            whitespace_cell_count,
        ),
        _issue(
            "formula-like-cell",
            "warning",
            "One or more cells look like spreadsheet formulas and may execute when opened.",
            formula_like_cell_count,
        ),
        _issue(
            "potential-pii",
            "warning",
            "One or more cells appear to contain personally identifiable information.",
            potential_pii_cell_count,
        ),
    ):
        if candidate:
            issues.append(candidate)

    summary = Summary(
        delimiter=delimiter,
        column_count=len(headers),
        data_row_count=data_row_count,
        blank_row_count=blank_row_count,
        blank_cell_count=blank_cell_count,
        duplicate_row_count=duplicate_row_count,
        ragged_row_count=ragged_row_count,
        whitespace_cell_count=whitespace_cell_count,
        formula_like_cell_count=formula_like_cell_count,
        potential_pii_cell_count=potential_pii_cell_count,
    )
    return InspectionReport(
        schema_version=_REPORT_SCHEMA_VERSION,
        summary=summary,
        headers=headers,
        issues=issues,
    )
