# SheetSentry architecture

SheetSentry is a local-first command-line utility for inspecting and safely preparing delimited text files. Version 1 deliberately supports UTF-8, UTF-8 with BOM, and UTF-16 CSV/TSV-style files. It does not execute formulas, upload files, call external services, or modify an input path in place.

## Product contract

| Surface | Contract |
| --- | --- |
| `inspect` | Opens a single local file, auto-detects its delimiter from a bounded sample, streams rows, and prints a report. It makes no file changes. |
| `sanitize` | Requires both an explicit transformation flag and a separate output path. It writes a new CSV and, by default, an adjacent JSON audit log. |
| `validate` | Reuses inspection checks and returns `0` for a pass, `1` when a configured quality or safety violation is found, and `2` for invalid invocation or unreadable input. |
| JSON output | Uses a stable, documented, machine-readable shape so that scripts and CI can consume reports without scraping terminal text. |

## Modules

```text
cli.py       Command parsing, exit codes, output formatting
models.py    Typed report, issue, statistics and sanitization data structures
reader.py    Safe decoding, dialect detection and streamed row iteration
inspect.py   Pure inspection functions and heuristic issue detection
sanitize.py  Explicit transformations, formula policy, and audit construction
report.py    Human-readable and JSON report rendering
```

The library layer accepts paths and explicit configuration objects. The CLI is intentionally thin so that future GUI, pre-commit, and library integrations can reuse core behavior.

## Input safety and threat model

SheetSentry treats every cell as untrusted data. It never uses `eval`, never opens the file in a spreadsheet application, and never executes data-derived shell commands. Field values are rendered through JSON encoding or escaped terminal representations to avoid terminal-control ambiguity.

CSV formula injection is a primary risk. A cell that starts after leading whitespace with `=`, `+`, `-`, `@`, tab, carriage return, line feed, or a full-width variant is reported. Sanitization has three explicit policies:

| Policy | Behavior | Intended use |
| --- | --- | --- |
| `report-only` | Preserve original values; record the risk. | Data pipelines where data fidelity is more important than spreadsheet viewing. |
| `apostrophe` | Prefix formula-like values with `'`. | Common spreadsheet-focused workflow; compatibility depends on the downstream application. |
| `tab` | Prefix formula-like values with a tab. | Files deliberately prepared for Excel-style human viewing; adds a data character. |

The tool does not claim that any policy is universally safe across every application. The caller owns the trade-off and should preserve the original source file.

## Data quality checks

The inspector reports empty or duplicate headers, ragged rows, blank rows, blank cells, duplicate data rows, leading/trailing whitespace, potential formula cells, and potential email/phone values. PII detection is heuristic-only and not a compliance claim. To limit memory use, duplicate detection uses hashes of serialized rows; sanitization uses a set only when `--dedupe` is requested.

## Compatibility and limits

The initial release accepts delimited text files only; it does not parse `.xlsx`, convert dates, infer business schemas, or cleanse personal data. Dialect detection is intentionally bounded to a sample and users can override the delimiter. Large-file scanning is streaming, although duplicate removal stores hashes proportional to the distinct row count.

## Extension points

Future releases can add user-defined schema constraints, configurable detection rules, pre-commit support, native XLSX read-only inspection, and a browser-safe local report viewer without changing the current core contracts.
