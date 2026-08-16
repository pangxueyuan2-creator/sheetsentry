"""Explicit, auditable transformations for delimited text files."""

from __future__ import annotations

import csv
import os
import re
import tempfile
import unicodedata
from collections import defaultdict
from pathlib import Path

from .inspect import inspect_file, is_formula_like
from .models import SanitizationAudit, SanitizationOptions
from .reader import InputError, open_rows

_ALLOWED_FORMULA_POLICIES = {"report-only", "apostrophe", "tab"}


def _normalize_header(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    normalized = re.sub(r"[^\w]+", "_", normalized, flags=re.UNICODE).strip("_")
    return normalized or "unnamed_column"


def _unique_headers(headers: list[str]) -> list[str]:
    seen: defaultdict[str, int] = defaultdict(int)
    result: list[str] = []
    for header in headers:
        base = _normalize_header(header)
        seen[base] += 1
        result.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
    return result


def _apply_formula_policy(value: str, policy: str) -> tuple[str, bool]:
    if policy == "report-only" or not is_formula_like(value):
        return value, False
    if policy == "apostrophe":
        return f"'{value}", True
    if policy == "tab":
        return f"\t{value}", True
    raise InputError(f"Unsupported formula policy: {policy}")


def _validate_paths(input_path: Path, output_path: Path, force: bool) -> None:
    if input_path.resolve() == output_path.resolve():
        raise InputError("Output path must be different from the input path.")
    if not output_path.parent.exists():
        raise InputError(f"Output directory does not exist: {output_path.parent}")
    if output_path.exists() and not force:
        raise InputError(
            f"Refusing to overwrite existing output: {output_path}. Pass --force to replace it."
        )


def sanitize_file(
    input_path: Path, output_path: Path, options: SanitizationOptions
) -> SanitizationAudit:
    """Write a separately named sanitized CSV file and return an audit record."""

    if options.formula_policy not in _ALLOWED_FORMULA_POLICIES:
        raise InputError("Formula policy must be one of: report-only, apostrophe, tab.")
    _validate_paths(input_path, output_path, options.force)
    input_report = inspect_file(input_path, options.input_delimiter)
    modifications = {
        "headers_normalized": 0,
        "cells_trimmed": 0,
        "blank_rows_dropped": 0,
        "duplicate_rows_dropped": 0,
        "formula_cells_prefixed": 0,
    }
    temp_name: str | None = None

    try:
        with open_rows(input_path, options.input_delimiter) as opened_rows:
            reader, _encoding, _delimiter, _handle = opened_rows
            headers = next(reader, None)
            if headers is None or not any(cell.strip() for cell in headers):
                raise InputError("Cannot sanitize an empty file without a header row.")
            output_headers = headers
            if options.normalize_headers:
                output_headers = _unique_headers(headers)
                modifications["headers_normalized"] = sum(
                    original != normalized
                    for original, normalized in zip(headers, output_headers, strict=True)
                )
            # Spreadsheet applications execute formulas in header cells too, so the
            # formula policy must cover the header row, not only data rows.
            neutralized_headers: list[str] = []
            for cell in output_headers:
                current, prefixed = _apply_formula_policy(cell, options.formula_policy)
                if prefixed:
                    modifications["formula_cells_prefixed"] += 1
                neutralized_headers.append(current)

            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                prefix=f".{output_path.name}.",
                suffix=".tmp",
                dir=output_path.parent,
                delete=False,
            ) as temporary:
                temp_name = temporary.name
                writer = csv.writer(temporary, delimiter=options.output_delimiter)
                writer.writerow(neutralized_headers)
                seen_rows: set[tuple[str, ...]] = set()

                for row in reader:
                    if options.drop_blank_rows and not any(cell.strip() for cell in row):
                        modifications["blank_rows_dropped"] += 1
                        continue

                    transformed: list[str] = []
                    for cell in row:
                        current = cell
                        if options.trim:
                            stripped = current.strip()
                            if stripped != current:
                                modifications["cells_trimmed"] += 1
                                current = stripped
                        current, prefixed = _apply_formula_policy(current, options.formula_policy)
                        if prefixed:
                            modifications["formula_cells_prefixed"] += 1
                        transformed.append(current)

                    signature = tuple(transformed)
                    if options.dedupe and signature in seen_rows:
                        modifications["duplicate_rows_dropped"] += 1
                        continue
                    if options.dedupe:
                        seen_rows.add(signature)
                    writer.writerow(transformed)

        os.replace(temp_name, output_path)
        temp_name = None
    finally:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)

    output_report = inspect_file(output_path, options.output_delimiter)
    return SanitizationAudit(
        schema_version="1.0",
        input_path=str(input_path),
        output_path=str(output_path),
        formula_policy=options.formula_policy,
        output_delimiter=options.output_delimiter,
        modifications=modifications,
        input_summary=input_report.summary,
        output_summary=output_report.summary,
    )
