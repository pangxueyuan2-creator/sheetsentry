# Contributing to SheetSentry

Thank you for helping make delimited-file handling safer and less error-prone. SheetSentry values focused improvements, clear tests, predictable command-line behavior, and documentation that describes both capability and limitation accurately.

## Before you start

Please search existing issues before proposing a feature or reporting a defect. A good issue states the operating system, Python version, exact command, a minimal non-sensitive input example, the expected behavior, and the observed behavior. Do not upload real customer records, credentials, or personal data in an issue, pull request, or test fixture.

## Development setup

Use Python 3.10 or newer. The project intentionally has no runtime dependencies and uses the standard library for its core behavior.

```bash
git clone https://github.com/pangxueyuan2-creator/sheetsentry.git
cd sheetsentry
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## Quality checks

Every pull request should include tests for behavior changes and leave the following checks passing. The project CI executes these same categories of checks on supported Python versions.

```bash
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
bandit -q -r src
python -m build
```

When adding a user-visible command, preserve the existing exit-code contract: `0` for a successful operation, `1` for a validation finding that meets the configured threshold, and `2` for an invalid invocation or unreadable input.

## Design expectations

Changes should keep the tool local-first, transparent, and safe by default. Do not introduce network calls, telemetry, formula execution, or automatic in-place modification. When a feature changes file contents, require an explicit flag, preserve the input path, produce explainable output, and add tests covering both the intended transformation and refusal behavior.

The tool’s PII and formula signals are deliberately conservative heuristics. Do not describe them as legal, compliance, privacy, or security guarantees. If changing formula-handling behavior, document the compatibility trade-off across spreadsheet applications and cite an authoritative source where appropriate.

## Pull request process

Keep pull requests narrowly scoped and write a concise explanation of the problem, approach, tests, and user-facing changes. Update the README, architecture document, changelog, and help text when applicable. A maintainer will review correctness, compatibility, safety boundaries, tests, and documentation before merge.

## Code of conduct

Be respectful, constructive, and considerate of other contributors. Harassment, discriminatory behavior, and disclosure of private information are not acceptable in this project.
