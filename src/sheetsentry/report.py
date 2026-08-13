"""Rendering helpers for terminal and JSON output."""

from __future__ import annotations

import json
from typing import Any

from .models import InspectionReport, SanitizationAudit


def to_json(data: dict[str, Any]) -> str:
    """Render stable, UTF-8-friendly JSON for scripts and CI."""

    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _display_delimiter(delimiter: str) -> str:
    return {"\t": "TAB", ",": "COMMA", ";": "SEMICOLON", "|": "PIPE"}.get(
        delimiter, repr(delimiter)
    )


def render_inspection(report: InspectionReport) -> str:
    """Render a concise human-readable inspection report."""

    summary = report.summary
    lines = [
        "SheetSentry inspection report",
        "=" * 28,
        f"File: {summary.path}",
        f"Encoding: {summary.encoding}",
        f"Delimiter: {_display_delimiter(summary.delimiter)}",
        f"Columns: {summary.column_count}",
        f"Data rows: {summary.data_row_count}",
        "",
        "Observed counts",
        "-" * 15,
        f"Blank rows: {summary.blank_row_count}",
        f"Ragged rows: {summary.ragged_row_count}",
        f"Blank cells: {summary.blank_cell_count}",
        f"Duplicate rows: {summary.duplicate_row_count}",
        f"Whitespace cells: {summary.whitespace_cell_count}",
        f"Formula-like cells: {summary.formula_like_cell_count}",
        f"Potential PII cells: {summary.potential_pii_cell_count}",
        "",
        "Findings",
        "-" * 8,
    ]
    if not report.issues:
        lines.append("No configured issues found.")
    else:
        for issue in report.issues:
            lines.append(
                f"[{issue.severity.upper()}] {issue.code} ({issue.count}): {issue.message}"
            )
            lines.extend(f"  - {sample}" for sample in issue.samples)
    return "\n".join(lines) + "\n"


def render_audit(audit: SanitizationAudit) -> str:
    """Render an auditable summary after a successful sanitize operation."""

    lines = [
        "SheetSentry sanitization complete",
        "=" * 31,
        f"Input: {audit.input_path}",
        f"Output: {audit.output_path}",
        f"Formula policy: {audit.formula_policy}",
        f"Output delimiter: {_display_delimiter(audit.output_delimiter)}",
        "",
        "Applied modifications",
        "-" * 21,
    ]
    lines.extend(f"{key.replace('_', ' ')}: {value}" for key, value in audit.modifications.items())
    lines.extend(
        (
            "",
            f"Output rows: {audit.output_summary.data_row_count}",
            f"Remaining formula-like cells: {audit.output_summary.formula_like_cell_count}",
        )
    )
    return "\n".join(lines) + "\n"
