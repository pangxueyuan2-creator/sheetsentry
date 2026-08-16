"""Read-only checks for common delimited-file quality and safety concerns."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .models import FileSummary, InspectionReport, Issue
from .reader import open_rows

_REPORT_SCHEMA_VERSION = "1.0"
_FORMULA_PREFIXES = (
    "=",
    "+",
    "-",
    "@",
    "\t",
    "\r",
    "\n",
    "\uff1d",
    "\uff0b",
    "\uff0d",
    "\uff20",
)
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9 .()/-]{6,}[0-9]$")


def is_formula_like(value: str) -> bool:
    """Return whether a cell could be interpreted as a spreadsheet formula."""

    return value.lstrip(" \f\v").startswith(_FORMULA_PREFIXES)


def _is_potential_pii(value: str) -> bool:
    trimmed = value.strip()
    return bool(_EMAIL_PATTERN.fullmatch(trimmed) or _PHONE_PATTERN.fullmatch(trimmed))


def _sample(row_number: int, column_number: int, value: str) -> str:
    safe_value = value[:80].replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    return f"row {row_number}, column {column_number}: {safe_value!r}"


def _issue(
    code: str, severity: str, message: str, count: int, samples: list[str] | None = None
) -> Issue | None:
    if count == 0:
        return None
    return Issue(code=code, severity=severity, message=message, count=count, samples=samples or [])


def inspect_file(path: Path, delimiter: str | None = None) -> InspectionReport:
    """Inspect one local CSV/TSV-style file without modifying it."""

    issues: list[Issue] = []
    with open_rows(path, delimiter) as (reader, encoding, actual_delimiter, _handle):
        headers = next(reader, None)
        if headers is None or not any(cell.strip() for cell in headers):
            summary = FileSummary(
                path=str(path),
                encoding=encoding,
                delimiter=actual_delimiter,
                column_count=0,
                data_row_count=0,
                total_row_count=0,
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
        formula_like_headers = [header for header in headers if is_formula_like(header)]
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
                samples=[
                    _sample(1, column, header)
                    for column, header in enumerate(formula_like_headers, start=1)
                ][:3],
            ),
        ):
            if candidate:
                issues.append(candidate)

        data_row_count = 0
        blank_row_count = 0
        blank_cell_count = 0
        duplicate_row_count = 0
        ragged_row_count = 0
        whitespace_cell_count = 0
        formula_like_cell_count = 0
        potential_pii_cell_count = 0
        formula_samples: list[str] = []
        pii_samples: list[str] = []
        ragged_samples: list[str] = []
        seen_rows: set[tuple[str, ...]] = set()

        for row_number, row in enumerate(reader, start=2):
            data_row_count += 1
            if not any(cell.strip() for cell in row):
                blank_row_count += 1
            if len(row) != len(headers):
                ragged_row_count += 1
                if len(ragged_samples) < 3:
                    ragged_samples.append(
                        f"row {row_number}: expected {len(headers)} columns, found {len(row)}"
                    )
            signature = tuple(row)
            if signature in seen_rows:
                duplicate_row_count += 1
            else:
                seen_rows.add(signature)

            for column_number, cell in enumerate(row, start=1):
                if not cell.strip():
                    blank_cell_count += 1
                if cell != cell.strip():
                    whitespace_cell_count += 1
                if is_formula_like(cell):
                    formula_like_cell_count += 1
                    if len(formula_samples) < 3:
                        formula_samples.append(_sample(row_number, column_number, cell))
                if _is_potential_pii(cell):
                    potential_pii_cell_count += 1
                    if len(pii_samples) < 3:
                        pii_samples.append(_sample(row_number, column_number, cell))

    for candidate in (
        _issue(
            "blank-row",
            "warning",
            "Blank data rows were found.",
            blank_row_count,
        ),
        _issue(
            "ragged-row",
            "error",
            "Data rows do not all match the header column count.",
            ragged_row_count,
            ragged_samples,
        ),
        _issue(
            "blank-cell",
            "info",
            "Blank or whitespace-only cells were found.",
            blank_cell_count,
        ),
        _issue(
            "duplicate-row",
            "warning",
            "Exact duplicate data rows were found.",
            duplicate_row_count,
        ),
        _issue(
            "whitespace",
            "info",
            "Cells with leading or trailing whitespace were found.",
            whitespace_cell_count,
        ),
        _issue(
            "formula-like-cell",
            "warning",
            "Cells with formula-like leading characters were found. "
            "Review before opening in a spreadsheet.",
            formula_like_cell_count,
            formula_samples,
        ),
        _issue(
            "potential-pii",
            "info",
            "Cells resembling email addresses or phone numbers were found. This is heuristic only.",
            potential_pii_cell_count,
            pii_samples,
        ),
    ):
        if candidate:
            issues.append(candidate)

    summary = FileSummary(
        path=str(path),
        encoding=encoding,
        delimiter=actual_delimiter,
        column_count=len(headers),
        data_row_count=data_row_count,
        total_row_count=data_row_count + 1,
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
