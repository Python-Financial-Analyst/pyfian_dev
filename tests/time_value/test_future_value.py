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

    def test_annuity(self):
        payment = 100
        rate = 0.05
        periods = 10
        expected = (
            (1 + rate) ** periods * payment * ((1 - (1 + rate) ** -periods) / rate)
        )
        assert (
            pytest.approx(
                future_value.future_value_annuity(payment, rate, periods), rel=1e-9
            )
            == expected
        )


class TestFutureValueGrowingAnnuity:
    def test_growing_annuity(self):
        payment = 100
        rate = 0.05
        growth = 0.02
        periods = 10
        if rate == growth:
            expected = (1 + rate) ** periods * sum(
                payment * ((1 + growth) / (1 + rate)) ** k
                for k in range(1, periods + 1)
            )
        else:
            expected = (
                payment
                * (1 + growth)
                * ((1 - ((1 + growth) / (1 + rate)) ** periods) / (rate - growth))
                * (1 + rate) ** periods
            )

        assert (
            pytest.approx(
                future_value.future_value_growing_annuity(
                    payment, rate, periods, growth
                ),
                rel=1e-9,
            )
            == expected
        )


class TestFutureValueAnnuityAnnual:
    def test_annual(self):
        payment = 100
        rate = 0.05
        year = 10
        payments_per_year = 12

        assert (
            pytest.approx(
                future_value.future_value_annuity_annual(
                    payment, rate, year, payments_per_year
                ),
                rel=1e-9,
            )
            == 15528.22794456672
        )
