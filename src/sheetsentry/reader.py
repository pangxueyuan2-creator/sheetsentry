"""Safe, bounded helpers for reading CSV and TSV-style text files."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

_SAMPLE_BYTES = 65_536
_ALLOWED_DELIMITERS = (",", "\t", ";", "|")


class InputError(ValueError):
    """Raised when an input file cannot be safely interpreted as delimited text."""


def _validate_path(path: Path) -> None:
    if not path.exists():
        raise InputError(f"Input file does not exist: {path}")
    if not path.is_file():
        raise InputError(f"Input path is not a regular file: {path}")


def detect_encoding(path: Path) -> str:
    """Identify supported Unicode encodings without silently corrupting input."""

    _validate_path(path)
    raw = path.read_bytes()[:_SAMPLE_BYTES]
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return "utf-16"
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InputError(
            "Unsupported text encoding. SheetSentry currently supports UTF-8 and UTF-16 files."
        ) from exc
    return "utf-8"


def validate_delimiter(delimiter: str) -> str:
    if len(delimiter) != 1 or delimiter in {"\r", "\n", '"'}:
        raise InputError("Delimiter must be one non-quote, non-newline character.")
    return delimiter


def detect_delimiter(path: Path, encoding: str, override: str | None = None) -> str:
    """Detect a common delimiter from a bounded sample, with a safe fallback."""

    if override is not None:
        return validate_delimiter(override)

    with path.open("r", encoding=encoding, newline="") as handle:
        sample = handle.read(_SAMPLE_BYTES)
    if not sample:
        return ","

    try:
        return csv.Sniffer().sniff(sample, delimiters="".join(_ALLOWED_DELIMITERS)).delimiter
    except csv.Error:
        lines = [line for line in sample.splitlines() if line.strip()][:20]
        if not lines:
            return ","
        return max(_ALLOWED_DELIMITERS, key=lambda value: sum(line.count(value) for line in lines))


@contextmanager
def open_rows(
    path: Path, delimiter: str | None = None
) -> Iterator[tuple[csv.reader, str, str, TextIO]]:
    """Open a supported text file and yield a configured CSV reader.

    The caller must consume the reader within the context manager. Opening uses
    ``newline=''`` as required by Python's csv module.
    """

    encoding = detect_encoding(path)
    actual_delimiter = detect_delimiter(path, encoding, delimiter)
    handle = path.open("r", encoding=encoding, newline="")
    try:
        yield csv.reader(handle, delimiter=actual_delimiter), encoding, actual_delimiter, handle
    except csv.Error as exc:
        raise InputError(f"Malformed delimited text in {path}: {exc}") from exc
    finally:
        handle.close()
