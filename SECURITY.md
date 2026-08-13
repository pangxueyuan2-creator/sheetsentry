# Security policy

## Supported versions

| Version | Supported |
| --- | --- |
| 1.0.x | Yes |
| Earlier versions | No |

## Reporting a vulnerability

Please **do not** open a public issue for a suspected vulnerability. Instead, contact the repository owner through the GitHub account associated with this repository and include a clear description, affected version, proof-of-concept steps using synthetic data, and suggested mitigation if available.

A report will be acknowledged as soon as practical. Valid reports will be assessed for impact, reproducibility, and affected versions. The project aims to coordinate a fix and disclosure responsibly, but does not make a specific response-time guarantee.

## Security boundaries

SheetSentry processes local delimited text files and is designed not to execute formulas, commands, or embedded content. However, it is not a malware scanner, a sandbox, a PII redaction or compliance product, or a guarantee that a file is safe for every spreadsheet application. Formula-risk handling is policy-based and application-dependent; users should preserve sources and validate outputs in their receiving environment.

## Scope

Reports are particularly useful for issues involving unsafe input parsing, path handling, unintended overwrites, command execution, sensitive data exposure, denial of service in ordinary use, or a mismatch between documented and actual formula-handling behavior.
