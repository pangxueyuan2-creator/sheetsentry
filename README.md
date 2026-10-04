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
- Malformed quoted CSV/TSV records are rejected instead of silently repaired. Valid quoted multiline cells and escaped quotes remain supported.
- Sanitization publishes the completed file atomically. Without `--force`, it also preserves output files created during processing. This uses a same-directory hard link; a filesystem that cannot create hard links refuses the operation.
- Not a full PII scanner or spreadsheet engine

MIT.
