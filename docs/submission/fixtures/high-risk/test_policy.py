import unittest

from policy import Grant, is_allowed


class PolicyTests(unittest.TestCase):
    def test_exact_grant_is_required(self):
        grants = [Grant("reviewer", "read")]
        self.assertTrue(is_allowed(grants, "reviewer", "read"))
        self.assertFalse(is_allowed(grants, "reviewer", "write"))


if __name__ == "__main__":
    unittest.main()
