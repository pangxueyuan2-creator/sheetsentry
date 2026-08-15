# SheetSentry

**Inspect and safely prepare CSV/TSV files before sharing or import.**

Local-first, zero-dependency CLI. Checks structure, flags formula-like cells, and can write a cleaned copy. Never uploads anything and never overwrites the original.

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
sheetsentry inspect FILE     Report problems
sheetsentry validate FILE    Same, but fail on threshold (for CI)
sheetsentry sanitize FILE    Write a cleaned copy
```

## Notes

- Formula mitigation is not universal across spreadsheet apps — keep the original and test the result
- Not a full PII tool or spreadsheet engine

MIT License.
