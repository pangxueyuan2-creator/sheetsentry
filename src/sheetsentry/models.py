"""Typed data models used by SheetSentry's inspection and sanitization APIs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Issue:
    """A detected data-quality or security concern."""

    code: str
    severity: str
    message: str
    count: int = 1
    samples: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FileSummary:
    """Basic facts observed while scanning a delimited text file."""

    path: str
    encoding: str
    delimiter: str
    column_count: int
    data_row_count: int
    total_row_count: int
    blank_row_count: int
    blank_cell_count: int
    duplicate_row_count: int
    ragged_row_count: int
    whitespace_cell_count: int
    formula_like_cell_count: int
    potential_pii_cell_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class InspectionReport:
    """A complete, serializable result of a read-only file inspection."""

    schema_version: str
    summary: FileSummary
    headers: list[str]
    issues: list[Issue]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "summary": self.summary.to_dict(),
            "headers": self.headers,
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True)
class SanitizationOptions:
    """Explicit, opt-in transformations available to the sanitize command."""

    trim: bool = False
    drop_blank_rows: bool = False
    dedupe: bool = False
    normalize_headers: bool = False
    formula_policy: str = "report-only"
    force: bool = False
    input_delimiter: str | None = None
    output_delimiter: str = ","

    def has_transformations(self) -> bool:
        return any(
            (
                self.trim,
                self.drop_blank_rows,
                self.dedupe,
                self.normalize_headers,
                self.formula_policy != "report-only",
            )
        )


@dataclass(frozen=True)
class SanitizationAudit:
    """An auditable description of a sanitization run."""

    schema_version: str
    input_path: str
    output_path: str
    formula_policy: str
    output_delimiter: str
    modifications: dict[str, int]
    input_summary: FileSummary
    output_summary: FileSummary

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "input_path": self.input_path,
            "output_path": self.output_path,
            "formula_policy": self.formula_policy,
            "output_delimiter": self.output_delimiter,
            "modifications": self.modifications,
            "input_summary": self.input_summary.to_dict(),
            "output_summary": self.output_summary.to_dict(),
        }
