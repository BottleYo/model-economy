import unittest

import settings


class SettingsTests(unittest.TestCase):
    def test_timeout_is_positive(self):
        self.assertGreater(settings.REQUEST_TIMEOUT_SECONDS, 0)


if __name__ == "__main__":
    unittest.main()
