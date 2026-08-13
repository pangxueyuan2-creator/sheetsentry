"""Command-line interface for SheetSentry."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .inspect import inspect_file
from .models import SanitizationOptions
from .reader import InputError, validate_delimiter
from .report import render_audit, render_inspection, to_json
from .sanitize import sanitize_file

_SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2}


def _delimiter_argument(value: str) -> str:
    if value == "\\t":
        value = "\t"
    try:
        return validate_delimiter(value)
    except InputError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _add_input_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("file", type=Path, help="Path to a UTF-8 or UTF-16 CSV/TSV-style file.")
    parser.add_argument(
        "--delimiter",
        type=_delimiter_argument,
        help="Input delimiter. Use \\t for a tab. Auto-detected by default.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the public CLI parser."""

    parser = argparse.ArgumentParser(
        prog="sheetsentry",
        description="Inspect and safely prepare CSV/TSV files before sharing or import.",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect", help="Read-only quality and safety inspection."
    )
    _add_input_options(inspect_parser)
    inspect_parser.add_argument(
        "--format", choices=("text", "json"), default="text", help="Output format (default: text)."
    )

    validate_parser = subparsers.add_parser(
        "validate", help="Inspect and return a CI-friendly status code."
    )
    _add_input_options(validate_parser)
    validate_parser.add_argument(
        "--fail-on",
        choices=tuple(_SEVERITY_ORDER),
        default="error",
        help="Exit with 1 when a finding reaches this severity (default: error).",
    )
    validate_parser.add_argument(
        "--format", choices=("text", "json"), default="text", help="Output format (default: text)."
    )

    sanitize_parser = subparsers.add_parser(
        "sanitize", help="Write a separately named, explicitly transformed CSV file."
    )
    _add_input_options(sanitize_parser)
    sanitize_parser.add_argument(
        "--output", "-o", required=True, type=Path, help="New output file path."
    )
    sanitize_parser.add_argument(
        "--trim", action="store_true", help="Trim leading/trailing cell whitespace."
    )
    sanitize_parser.add_argument(
        "--drop-blank-rows", action="store_true", help="Drop rows where every cell is blank."
    )
    sanitize_parser.add_argument(
        "--dedupe", action="store_true", help="Drop exact duplicate data rows."
    )
    sanitize_parser.add_argument(
        "--normalize-headers",
        action="store_true",
        help="Normalize headers to unique snake_case names.",
    )
    sanitize_parser.add_argument(
        "--formula-policy",
        choices=("report-only", "apostrophe", "tab"),
        default="report-only",
        help="How to treat formula-like cells (default: report-only).",
    )
    sanitize_parser.add_argument(
        "--output-delimiter",
        type=_delimiter_argument,
        default=",",
        help="Output delimiter; use \\t for a tab (default: comma).",
    )
    sanitize_parser.add_argument(
        "--force", action="store_true", help="Allow replacing an existing output path."
    )
    sanitize_parser.add_argument(
        "--format", choices=("text", "json"), default="text", help="Output format (default: text)."
    )
    return parser


def _emit_inspection(report_format: str, report: object) -> None:
    if report_format == "json":
        print(to_json(report.to_dict()), end="")  # type: ignore[attr-defined]
    else:
        print(render_inspection(report), end="")  # type: ignore[arg-type]


def run(arguments: Sequence[str] | None = None) -> int:
    """Run the CLI and return a portable process exit code."""

    parser = build_parser()
    args = parser.parse_args(arguments)
    try:
        if args.command == "inspect":
            report = inspect_file(args.file, args.delimiter)
            _emit_inspection(args.format, report)
            return 0

        if args.command == "validate":
            report = inspect_file(args.file, args.delimiter)
            _emit_inspection(args.format, report)
            threshold = _SEVERITY_ORDER[args.fail_on]
            return int(any(_SEVERITY_ORDER[issue.severity] >= threshold for issue in report.issues))

        if args.command == "sanitize":
            options = SanitizationOptions(
                trim=args.trim,
                drop_blank_rows=args.drop_blank_rows,
                dedupe=args.dedupe,
                normalize_headers=args.normalize_headers,
                formula_policy=args.formula_policy,
                force=args.force,
                input_delimiter=args.delimiter,
                output_delimiter=args.output_delimiter,
            )
            if not options.has_transformations():
                raise InputError(
                    "No transformation selected. Add --trim, --drop-blank-rows, --dedupe, "
                    "--normalize-headers, or a non-default --formula-policy."
                )
            audit = sanitize_file(args.file, args.output, options)
            if args.format == "json":
                print(to_json(audit.to_dict()), end="")
            else:
                print(render_audit(audit), end="")
            return 0
    except InputError as exc:
        print(f"sheetsentry: error: {exc}", file=sys.stderr)
        return 2
    return 2


def main() -> None:
    """Console-script entry point."""

    raise SystemExit(run())
