import pytest

from pyfian.time_value.real_rates import (fisher_exact_real_rate,
                                          fisher_real_rate)


class TestFischerRate:
    def test_fisher_real_rate_typical(self):
        assert pytest.approx(fisher_real_rate(0.05, 0.02), 0.0001) == 0.03

    def test_fisher_exact_real_rate_typical(self):
        assert (
            pytest.approx(fisher_exact_real_rate(0.05, 0.02), 0.000001) == 0.02941176447
        )

    def test_zero_nominal_rate(self):
        assert pytest.approx(fisher_real_rate(0.0, 0.02), 0.0001) == -0.02
        assert (
            pytest.approx(fisher_exact_real_rate(0.0, 0.02), 0.000001) == -0.01960783137
        )

    def test_zero_inflation_rate(self):
        assert pytest.approx(fisher_real_rate(0.05, 0.0), 0.0001) == 0.05
        assert pytest.approx(fisher_exact_real_rate(0.05, 0.0), 0.0001) == 0.05

    def test_negative_inflation_rate(self):
        assert pytest.approx(fisher_real_rate(0.05, -0.02), 0.0001) == 0.07
        assert (
            pytest.approx(fisher_exact_real_rate(0.05, -0.02), 0.000001) == 0.0714285714
        )

    def test_negative_nominal_rate(self):
        assert pytest.approx(fisher_real_rate(-0.01, 0.02), 0.0001) == -0.03
        assert (
            pytest.approx(fisher_exact_real_rate(-0.01, 0.02), 0.000001)
            == -0.0294117647
        )

    def test_both_negative(self):
        assert pytest.approx(fisher_real_rate(-0.01, -0.02), 0.0001) == 0.01
        assert (
            pytest.approx(fisher_exact_real_rate(-0.01, -0.02), 0.000001)
            == 0.0102040816
        )

    def test_equal_nominal_and_inflation(self):
        assert pytest.approx(fisher_real_rate(0.03, 0.03), 0.0001) == 0.0
        assert pytest.approx(fisher_exact_real_rate(0.03, 0.03), 0.0001) == 0.0
