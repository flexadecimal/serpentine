import unittest

class FooTest(unittest.TestCase):
    def test_big(self):
        self.assertAlmostEqual(1.01, 1.02)