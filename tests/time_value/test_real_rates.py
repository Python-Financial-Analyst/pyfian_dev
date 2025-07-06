import unittest
from pyfian.time_value.real_rates import fisher_real_rate, fisher_exact_real_rate

class TestRealRates(unittest.TestCase):

    def test_fisher_real_rate_typical(self):
        self.assertAlmostEqual(fisher_real_rate(0.05, 0.02), 0.03)

    def test_fisher_exact_real_rate_typical(self):
        self.assertAlmostEqual(fisher_exact_real_rate(0.05, 0.02), 0.029412, places=6)

    def test_zero_nominal_rate(self):
        self.assertAlmostEqual(fisher_real_rate(0.0, 0.02), -0.02)
        self.assertAlmostEqual(fisher_exact_real_rate(0.0, 0.02), -0.019608, places=6)

    def test_zero_inflation_rate(self):
        self.assertAlmostEqual(fisher_real_rate(0.05, 0.0), 0.05)
        self.assertAlmostEqual(fisher_exact_real_rate(0.05, 0.0), 0.05)

    def test_negative_inflation_rate(self):
        self.assertAlmostEqual(fisher_real_rate(0.05, -0.02), 0.07)
        self.assertAlmostEqual(fisher_exact_real_rate(0.05, -0.02), 0.068627, places=6)

    def test_negative_nominal_rate(self):
        self.assertAlmostEqual(fisher_real_rate(-0.01, 0.02), -0.03)
        self.assertAlmostEqual(fisher_exact_real_rate(-0.01, 0.02), -0.029412, places=6)

    def test_both_negative(self):
        self.assertAlmostEqual(fisher_real_rate(-0.01, -0.02), 0.01)
        self.assertAlmostEqual(fisher_exact_real_rate(-0.01, -0.02), 0.010204, places=6)

    def test_equal_nominal_and_inflation(self):
        self.assertAlmostEqual(fisher_real_rate(0.03, 0.03), 0.0)
        self.assertAlmostEqual(fisher_exact_real_rate(0.03, 0.03), 0.0)

if __name__ == '__main__':
    unittest.main()
