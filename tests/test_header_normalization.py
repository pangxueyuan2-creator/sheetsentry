from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from sheetsentry.models import SanitizationOptions
from sheetsentry.sanitize import sanitize_file


class HeaderNormalizationTests(unittest.TestCase):
    def test_normalization_keeps_suffix_collisions_unique(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "headers.csv"
            source.write_text("Name,Name,name_2\na,b,c\n", encoding="utf-8")
            output = Path(directory) / "clean.csv"

            sanitize_file(
                source,
                output,
                SanitizationOptions(normalize_headers=True),
            )

            with output.open(newline="", encoding="utf-8") as handle:
                headers = next(csv.reader(handle))

        self.assertEqual(headers, ["name", "name_2", "name_2_2"])
        self.assertEqual(len(headers), len(set(headers)))


if __name__ == "__main__":
    unittest.main()
