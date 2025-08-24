import pytest
import pandas as pd
from pyfian.yield_curves.zero_coupon_curve import ZeroCouponCurve, ZeroCouponCurveByDate


class TestZeroCouponCurve:
    def setup_method(self):
        self.zero_rates = {1.0: 0.02, 2.0: 0.025, 3.0: 0.03}
        self.curve_date = "2025-08-24"
        self.curve = ZeroCouponCurve(
            zero_rates=self.zero_rates,
            curve_date=self.curve_date,
            day_count_convention="actual/365",
            yield_calculation_convention="Annual",
        )

    def test_as_dict(self):
        expected = {
            "zero_rates": self.curve.zero_rates,
            "curve_date": self.curve.curve_date,
            "day_count_convention": self.curve.day_count_convention,
            "yield_calculation_convention": self.curve.yield_calculation_convention,
        }
        assert self.curve.as_dict() == expected

    # Test making a zero coupon curve without a valid day_count_convention, neither str nor DayCountBase
    def test_invalid_day_count_convention(self):
        with pytest.raises(
            TypeError,
            match="day_count_convention must be either a string or a DayCountBase instance",
        ):
            ZeroCouponCurve(
                zero_rates=self.zero_rates,
                curve_date=self.curve_date,
                day_count_convention=None,
                yield_calculation_convention="Annual",
            )

    def test_discount_t(self):
        pv = self.curve.discount_t(2.0)
        expected = 1 / (1 + 0.025) ** 2.0
        assert pytest.approx(pv, rel=1e-6) == expected

    def test_discount_to_rate(self):
        df = self.curve.discount_t(2.0)
        rate = self.curve.discount_to_rate(df, 2.0, 0)
        assert pytest.approx(rate, rel=1e-6) == 0.025

    def test_discount_date(self):
        date = pd.Timestamp("2027-08-24")
        pv = self.curve.discount_date(date)
        t = 2.0  # actual/365, exactly 2 years
        expected = 1 / (1 + 0.025) ** t
        assert pytest.approx(pv, rel=1e-6) == expected

    def test_call(self):
        rate = self.curve(2.0)
        assert pytest.approx(rate, rel=1e-6) == 0.025

    def test_date_rate(self):
        date = pd.Timestamp("2027-08-24")
        rate = self.curve.date_rate(date)
        assert pytest.approx(rate, rel=1e-6) == 0.025

    def test_linear_interpolation(self):
        # Between 2 and 3 years
        t = 2.5
        expected = 0.025 + (0.03 - 0.025) * (t - 2.0) / (3.0 - 2.0)
        rate = self.curve(t)
        assert pytest.approx(rate, rel=1e-6) == expected

    def test_date_below(self):
        date = pd.Timestamp("2025-08-24")
        rate = self.curve.date_rate(date)
        assert pytest.approx(rate, rel=1e-6) == 0.02

    def test_date_above(self):
        date = pd.Timestamp("2029-08-24")
        rate = self.curve.date_rate(date)
        assert pytest.approx(rate, rel=1e-6) == 0.03


class TestZeroCouponCurveByDate:
    def setup_method(self):
        self.curve_date = pd.Timestamp("2025-08-24")
        self.zero_rates_dates = {
            pd.Timestamp("2026-08-24"): 0.02,
            pd.Timestamp("2027-08-24"): 0.025,
            pd.Timestamp("2028-08-24"): 0.03,
        }
        self.curve = ZeroCouponCurveByDate(
            zero_rates_dates=self.zero_rates_dates,
            curve_date=self.curve_date,
            day_count_convention="actual/365",
            yield_calculation_convention="Annual",
        )

    def test_invalid_day_count_convention(self):
        with pytest.raises(
            TypeError,
            match="day_count_convention must be either a string or a DayCountBase instance.",
        ):
            ZeroCouponCurveByDate(
                zero_rates_dates=self.zero_rates_dates,
                curve_date=self.curve_date,
                day_count_convention=None,
                yield_calculation_convention="Annual",
            )

    def test_discount_date(self):
        date = pd.Timestamp("2027-08-24")
        pv = self.curve.discount_date(date)
        t = 2.0  # actual/365, exactly 2 years
        expected = 1 / (1 + 0.025) ** t
        assert pytest.approx(pv, rel=1e-6) == expected

    def test_date_rate(self):
        date = pd.Timestamp("2027-08-24")
        rate = self.curve.date_rate(date)
        assert pytest.approx(rate, rel=1e-6) == 0.025

    def test_linear_interpolation(self):
        # Between 2027-08-24 and 2028-08-24
        date = pd.Timestamp("2027-11-24")

        t1 = self.curve.day_count_convention.fraction(
            self.curve_date, pd.Timestamp("2027-08-24")
        )
        t2 = self.curve.day_count_convention.fraction(
            self.curve_date, pd.Timestamp("2028-08-24")
        )
        t = self.curve.day_count_convention.fraction(self.curve_date, date)

        r1 = 0.025
        r2 = 0.03
        expected = r1 + (r2 - r1) * (t - t1) / (t2 - t1)
        rate = self.curve.date_rate(date)
        assert pytest.approx(rate, rel=1e-6) == expected

    def test_repr(self):
        assert "ZeroCouponCurve" in repr(self.curve)

    def test_as_dict(self):
        expected = {
            "zero_rates_dates": self.curve.zero_rates_dates,
            "curve_date": self.curve.curve_date,
            "day_count_convention": self.curve.day_count_convention,
            "yield_calculation_convention": self.curve.yield_calculation_convention,
        }
        assert self.curve.as_dict() == expected
