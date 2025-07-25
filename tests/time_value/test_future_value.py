import pytest

from pyfian.time_value import future_value

# Test for future_value_annuity


class TestFutureValueAnnuity:
    def test_example(self):
        result = future_value.future_value_annuity(1000, 0.05, 10)
        assert pytest.approx(result, 0.01) == 12577.892535548839

    def test_zero_rate(self):
        assert future_value.future_value_annuity(1000, 0.0, 10) == 10000

    def test_one_period(self):
        assert (
            pytest.approx(future_value.future_value_annuity(1000, 0.05, 1), 0.01)
            == 1000.0
        )
