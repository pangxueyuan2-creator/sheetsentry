from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sheetsentry.reader import _SAMPLE_BYTES, InputError, detect_encoding, open_rows


class ReaderEncodingTests(unittest.TestCase):
    def test_accepts_utf8_code_point_split_at_sample_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "boundary.csv"
            path.write_bytes(b"a" * (_SAMPLE_BYTES - 1) + "é".encode() + b"\n")

            self.assertEqual(detect_encoding(path), "utf-8")

    def test_wraps_invalid_utf8_beyond_sample_as_input_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "late-invalid.csv"
            path.write_bytes(b"column\n" + b"a" * _SAMPLE_BYTES + b"\xff\n")

            with self.assertRaisesRegex(InputError, "Unsupported text encoding"):
                with open_rows(path, ",") as opened_rows:
                    rows, _encoding, _delimiter, _handle = opened_rows
                    list(rows)


if __name__ == "__main__":
    unittest.main()
