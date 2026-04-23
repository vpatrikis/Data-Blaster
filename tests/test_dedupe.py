import io
import unittest

from dedupe import dedupe_lines, write_output


class DedupeLinesTests(unittest.TestCase):
    def test_preserves_first_seen_order(self) -> None:
        lines = ["apple\n", "banana\n", "apple\n", "pear\n"]

        result = dedupe_lines(lines)

        self.assertEqual(result, ["apple", "banana", "pear"])

    def test_supports_ignore_case(self) -> None:
        lines = ["Apple\n", "apple\n", "APPLE\n"]

        result = dedupe_lines(lines, ignore_case=True)

        self.assertEqual(result, ["Apple"])

    def test_supports_strip_whitespace(self) -> None:
        lines = ["  apple  \n", "apple\n"]

        result = dedupe_lines(lines, strip_whitespace=True)

        self.assertEqual(result, ["  apple  "])

    def test_drops_empty_lines_by_default(self) -> None:
        lines = ["\n", "apple\n", "\n"]

        result = dedupe_lines(lines)

        self.assertEqual(result, ["apple"])

    def test_keeps_first_empty_line_when_requested(self) -> None:
        lines = ["\n", "\n", "apple\n"]

        result = dedupe_lines(lines, keep_empty=True)

        self.assertEqual(result, ["", "apple"])


class WriteOutputTests(unittest.TestCase):
    def test_writes_trailing_newline(self) -> None:
        handle = io.StringIO()

        write_output(["apple", "banana"], handle)

        self.assertEqual(handle.getvalue(), "apple\nbanana\n")


if __name__ == "__main__":
    unittest.main()
