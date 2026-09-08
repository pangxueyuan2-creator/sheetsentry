from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sheetsentry.inspect import inspect_file


class FormulaHeaderSampleTests(unittest.TestCase):
    def test_samples_preserve_original_header_column_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "headers.csv"
            path.write_text(
                "safe,also_safe,=1+1,plain,@SUM(A1)\n1,2,3,4,5\n",
                encoding="utf-8",
            )
            report = inspect_file(path)

        issue = next(
            issue for issue in report.issues if issue.code == "formula-like-header"
        )
        self.assertEqual(issue.count, 2)
        self.assertEqual(len(issue.samples), 2)
        self.assertIn("row 1, column 3", issue.samples[0])
        self.assertIn("row 1, column 5", issue.samples[1])


if __name__ == "__main__":
    unittest.main()
