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
- For the selected delimiter, unterminated quoted cells and invalid quote endings are rejected instead of silently repaired. Valid quoted multiline cells and escaped quotes remain supported. This follows Python's CSV dialect, which can accept literal quotes inside unquoted cells; it is not full RFC 4180 validation.
- Automatic delimiter detection is heuristic. When the export format is known, pass `--delimiter ,` (or `--delimiter \\t`, `;`, `|`) explicitly for validation and sanitization: another plausible dialect can otherwise interpret damaged records as valid text.
- Inspection summaries include `parsed_rows_sha256`, a SHA-256 over canonical ASCII JSON lines of all parsed rows. Sanitization compares the inspected and consumed row fingerprints before publication and rejects a changed input; output is inspected before publication. This binds parsed cell data, including whitespace and ordering, rather than raw encoding/line-ending bytes or writer identity.
- JSON reports use Unicode escapes and remain lossless when decoded as JSON. Text reports escape characters unsupported by the current terminal codec, including emoji in Windows GBK pipes.
- Sanitization publishes the completed file atomically. Without `--force`, it also preserves output files created during processing. Windows uses a non-replacing rename; other platforms use a same-directory exclusive hard link, so filesystems without hard-link support refuse the operation. Filesystem errors return exit code 2; externally locked temporary files can remain for manual cleanup and are identified in the error.
- Not a full PII scanner or spreadsheet engine

MIT.
