# SheetSentry

> **Inspect and safely prepare CSV/TSV files before they enter spreadsheets, business systems, or AI workflows.**

[![CI](https://github.com/pangxueyuan2-creator/sheetsentry/actions/workflows/ci.yml/badge.svg)](https://github.com/pangxueyuan2-creator/sheetsentry/actions/workflows/ci.yml)
[![CodeQL](https://github.com/pangxueyuan2-creator/sheetsentry/actions/workflows/codeql.yml/badge.svg)](https://github.com/pangxueyuan2-creator/sheetsentry/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

SheetSentry is a **local-first, zero-runtime-dependency** command-line tool for CSV and TSV delivery checks. It detects common structural problems, highlights cells that could be interpreted as spreadsheet formulas, and can write a separately named, auditable cleaned copy. It never uploads a file, calls an external service, or overwrites the input path.

## Why SheetSentry?

Delimited files are deceptively easy to share and surprisingly easy to break. A supplier export, a CRM download, or a hand-edited list may contain duplicate headers, inconsistent row widths, hidden whitespace, duplicate records, or values that spreadsheet software treats as formulas. Formula injection is a recognized risk: spreadsheet applications can interpret cells beginning with certain characters as formulas, and there is no single mitigation that is correct for every downstream application. [1]

General-purpose tools such as [csvkit](https://csvkit.readthedocs.io/en/latest/) are excellent for conversion and tabular processing. SheetSentry focuses on an earlier and narrower question: **is this file safe and structurally ready to hand to another person, spreadsheet, application, or automation?**

| Capability | What SheetSentry does |
| --- | --- |
| Read-only inspection | Identifies blank or duplicate headers, ragged rows, blank rows/cells, repeated rows, and leading or trailing whitespace. |
| Spreadsheet-risk review | Flags cells whose leading content may be interpreted as a formula, including `=`, `+`, `-`, `@`, tab, and supported full-width variants. |
| Local processing | Reads one file from the local filesystem; no network access, telemetry, keys, or accounts are required. |
| Explicit sanitation | Creates a **new** output file only when you select transformations; the original is never overwritten. |
| Auditability | Reports transformations in terminal output or JSON so a human, script, or CI job can review what changed. |
| Automation-friendly validation | Returns portable exit codes for quality gates and produces a stable JSON report. |

## Quick start

SheetSentry requires **Python 3.10 or newer**. Clone this repository and install it into your active environment, preferably an isolated environment managed by `pipx`, `venv`, or your preferred package manager.

```bash
git clone https://github.com/pangxueyuan2-creator/sheetsentry.git
cd sheetsentry
python -m pip install .

# Inspect without changing your file
sheetsentry inspect exports/customers.csv
```

Use JSON when another program needs the report.

```bash
sheetsentry inspect exports/customers.csv --format json > customers-report.json
```

Create a new cleaned file only after reviewing the inspection. The following command normalizes headings, trims cells, removes fully blank rows and exact duplicates, and prefixes formula-like cells with an apostrophe. It leaves the source file untouched.

```bash
sheetsentry sanitize exports/customers.csv \
  --output exports/customers-reviewed.csv \
  --normalize-headers \
  --trim \
  --drop-blank-rows \
  --dedupe \
  --formula-policy apostrophe
```

> **Important:** Formula prevention is context-dependent. `apostrophe` is familiar to many spreadsheet users, while `tab` follows the Excel-oriented approach described by OWASP but adds a tab character to the underlying value. `report-only` preserves the original value. Keep the original source and choose the policy that fits the receiving application. [1]

## Commands

| Command | Purpose | Exit status |
| --- | --- | --- |
| `sheetsentry inspect FILE` | Read a file and print a human-readable or JSON report. | `0` on successful inspection, even if findings exist. |
| `sheetsentry validate FILE` | Inspect a file and enforce a severity threshold for scripts or CI. | `0` when below threshold, `1` when a finding meets it, `2` on invalid input or invocation. |
| `sheetsentry sanitize FILE --output OUTPUT …` | Write a separately named transformed CSV plus a summary of changes. | `0` on successful output, `2` on invalid input or unsafe invocation. |

Each command supports `--help`. Input delimiter detection considers comma, tab, semicolon, and pipe. Use `--delimiter '\t'` to override the detector for tab-separated files. The initial release accepts UTF-8, UTF-8 with BOM, and UTF-16 delimited text files.

## Validation in automation

`validate` is designed for a simple delivery gate. By default it fails only on error-level findings, such as duplicate/blank headings or ragged rows. Raise the strictness to warning level when your workflow should stop on formula-like cells or duplicate rows.

```bash
# Print a report and fail the step when a warning or error is present.
sheetsentry validate outbound/report.csv --fail-on warning

# Consume the complete report without scraping terminal text.
sheetsentry validate outbound/report.csv --format json > report.json
```

## What gets checked

| Finding | Severity | Interpretation |
| --- | --- | --- |
| `blank-header` / `duplicate-header` | Error | The data contract is ambiguous after normalizing header whitespace and case. |
| `ragged-row` | Error | A row has a different number of cells from the header. |
| `blank-row` / `duplicate-row` | Warning | A fully blank or exact duplicate data row exists. |
| `formula-like-cell` | Warning | A cell looks capable of being interpreted as a spreadsheet formula. Review before opening or distributing it. |
| `blank-cell` / `whitespace` | Info | A potential data hygiene concern was observed. |
| `potential-pii` | Info | A cell resembles an email address or telephone number. This is a heuristic signal, not a privacy or compliance assessment. |

## Safe sanitation model

SheetSentry intentionally makes changes opt-in. `sanitize` refuses to run unless at least one transformation has been selected and refuses to write over an existing destination unless `--force` is supplied. It also refuses a destination that is the same path as the input. Writes use a temporary file and replacement only after successful processing.

| Option | Effect | Trade-off |
| --- | --- | --- |
| `--trim` | Removes leading/trailing whitespace from cells. | May intentionally change user-visible values. |
| `--drop-blank-rows` | Removes rows whose cells are all blank after trimming. | A blank row used as a visual separator is lost. |
| `--dedupe` | Removes exact duplicate data rows. | Requires memory proportional to the number of unique rows. |
| `--normalize-headers` | Produces unique `snake_case` headers such as `customer_name` and `customer_name_2`. | Changes the column contract expected by downstream consumers. |
| `--formula-policy apostrophe` | Prefixes formula-like cells with `'`. | Behavior is application-dependent. |
| `--formula-policy tab` | Prefixes formula-like cells with a tab. | Adds a data character; intended for spreadsheet-viewing workflows. [1] |

## Architecture

The project is deliberately small and dependency-free. The CLI delegates to a typed library layer with separate modules for safe file reading, pure inspection, explicit sanitation, data models, and output rendering. The full design and threat model are documented in [`docs/architecture.md`](docs/architecture.md).

```text
CLI → reader → inspect → report
            └→ sanitize → audit
```

The project does not execute formulas, use `eval`, interpret cell values as commands, or send files over the network. It treats each input cell as untrusted data.

## Development

Create an environment, install the project in editable mode, and run the standard-library test suite.

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m unittest discover -s tests -v
```

For maintainers, the continuous-integration workflow runs tests, `ruff`, `bandit`, package build verification, and CodeQL. The project intentionally has no production dependencies.

## Roadmap

The first release focuses on a reliable, inspectable core. The next highest-value extensions are configurable schema rules, a pre-commit integration, and read-only XLSX inspection. See the issue tracker for the evolving roadmap and contribution opportunities.

## Contributing and security

Contributions are welcome. Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request and report vulnerabilities according to [`SECURITY.md`](SECURITY.md). All contributors are expected to follow the project’s collaborative and security-first approach.

## Limitations

SheetSentry is not a spreadsheet renderer, database, universal file converter, PII redaction product, or compliance certification tool. It does not parse `.xlsx` files in version 1.0.0. Formula-risk mitigation cannot be universal across spreadsheet products and downstream data consumers; always retain the source file and validate the final file in the receiving workflow. [1]

## License

SheetSentry is released under the [MIT License](LICENSE).

## References

[1] [OWASP, “CSV Injection.”](https://owasp.org/www-community/attacks/CSV_Injection)
