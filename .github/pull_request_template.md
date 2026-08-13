# Summary

Describe the user problem and the change in a few complete sentences.

## Changes

Explain the implementation, including any CLI, report, documentation, or compatibility changes.

## Validation

State the commands you ran and their results. Include automated tests for behavior changes.

```text
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
bandit -q -r src
```

## Safety and data impact

Describe whether this change reads new input types, changes output data, affects formula-risk handling, or alters file-write behavior. Confirm that it introduces no network call, telemetry, secret, or automatic in-place modification.

## Checklist

- [ ] I used synthetic or redacted data only.
- [ ] I added or updated tests where behavior changed.
- [ ] I updated documentation, help text, and the changelog where appropriate.
- [ ] I ran the relevant quality checks locally.
- [ ] I considered backward compatibility and the documented safety model.
