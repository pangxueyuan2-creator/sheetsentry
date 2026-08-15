# SheetSentry

Local CLI for inspecting and cleaning CSV/TSV files before you share or import them.

Zero dependencies. Checks structure, flags formula-like cells, and can write a cleaned copy. Never uploads anything and never overwrites the original file.

## Quick start

Python 3.10+.

```bash
pip install .
sheetsentry inspect exports/customers.csv
```

Sanitize (writes a new file):

```bash
sheetsentry sanitize exports/customers.csv \
  --output exports/customers-clean.csv \
  --normalize-headers --trim --drop-blank-rows --dedupe \
  --formula-policy apostrophe
```

## Commands

```text
sheetsentry inspect FILE     report problems
sheetsentry validate FILE    same, but fail on threshold (for CI)
sheetsentry sanitize FILE    write a cleaned copy
```

## Notes

- Formula mitigation is not perfect across every spreadsheet app — keep the original and test the result
- Not a full PII scanner or spreadsheet engine

MIT.
