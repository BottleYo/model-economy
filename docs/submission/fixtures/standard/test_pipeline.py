import unittest

from parser import parse_names
from renderer import render_names


class PipelineTests(unittest.TestCase):
    def test_whitespace_is_removed_before_rendering(self):
        self.assertEqual(render_names(parse_names("alpha, beta")), "ALPHA / BETA")


if __name__ == "__main__":
    unittest.main()
