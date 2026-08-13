# Changelog

All notable changes to this project are documented in this file. The project follows [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-08-13

### Added

- A local-first `inspect` command for UTF-8 and UTF-16 CSV/TSV-style files.
- Checks for blank and duplicate headers, ragged rows, blank rows/cells, duplicate rows, leading/trailing whitespace, formula-like cells, and heuristic email/phone signals.
- A `validate` command with stable exit codes and JSON output for automation.
- An explicit `sanitize` command that writes a separate CSV file and audit summary.
- Opt-in transformations for trimming, dropping blank rows, exact deduplication, header normalization, and two formula-prefix policies.
- A standard-library test suite covering core behavior, invalid input, safety refusals, and command-line behavior.
- GitHub Actions CI, CodeQL analysis, Dependabot configuration, issue templates, pull-request template, security policy, and contribution guide.

### Security

- Formula-like cells are highlighted before spreadsheet import or sharing.
- Sanitization never overwrites the input path and refuses existing outputs without an explicit `--force` option.
- The core runtime uses no network calls or third-party runtime dependencies.
