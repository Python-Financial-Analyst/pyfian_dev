import re
import pytest
import pandas as pd
from pyfian.yield_curves.flat_curve import FlatCurveAER
from pyfian.yield_curves.credit_spread import FlatCreditSpreadCurve
from pyfian.yield_curves.curve_combination import CombinedCurve


class TestCombinedCurve:
    @pytest.fixture
    def curve_data(self):
        curve_date = pd.Timestamp("2023-01-01")
        benchmark_curve = FlatCurveAER(aer=0.04, curve_date=curve_date)
        spread_curve = FlatCreditSpreadCurve(spread=0.03, curve_date=curve_date)
        combined_curve = CombinedCurve(benchmark_curve, spread_curve)
        return curve_date, benchmark_curve, spread_curve, combined_curve

    def test_get_rate(self, curve_data):
        _, _, _, combined_curve = curve_data
        rate = combined_curve.get_rate(1.0)
        assert pytest.approx(rate, abs=1e-6) == 0.07

    # test get_t
    def test_get_t(self, curve_data):
        _, _, _, combined_curve = curve_data
        r = combined_curve.get_t(t=1.0)
        assert pytest.approx(r, abs=1e-6) == 0.07

    def test__get_t(self, curve_data):
        _, _, _, combined_curve = curve_data
        r = combined_curve._get_t(t=1.0)
        assert pytest.approx(r, abs=1e-6) == 0.07

    def test_date_rate(self, curve_data):
        _, _, _, combined_curve = curve_data
        date = pd.Timestamp("2024-01-01")
        rate = combined_curve.date_rate(date)
        assert isinstance(rate, float)

    def test_as_dict_and_from_dict(self, curve_data):
        _, _, _, combined_curve = curve_data
        curve_dict = combined_curve.as_dict()
        new_curve = CombinedCurve.from_dict(curve_dict)
        assert new_curve.curve_date == combined_curve.curve_date
        assert isinstance(
            new_curve.benchmark_curve, type(combined_curve.benchmark_curve)
        )
        assert isinstance(new_curve.spread_curve, type(combined_curve.spread_curve))

    def test_repr(self, curve_data):
        _, _, _, combined_curve = curve_data
        rep = repr(combined_curve)
        assert "CombinedCurve" in rep

    def test_curve_date_match(self, curve_data):
        curve_date, benchmark_curve, _, _ = curve_data
        wrong_date = pd.Timestamp("2022-01-01")
        with pytest.raises(AssertionError):
            CombinedCurve(
                benchmark_curve,
                FlatCreditSpreadCurve(spread=0.03, curve_date=wrong_date),
            )

    # test initialization with invalid day_count_convention
    def test_invalid_day_count_convention(self, curve_data):
        curve_date, benchmark_curve, _, _ = curve_data
        with pytest.raises(
            TypeError,
            match=re.escape(
                "day_count_convention must be either a string or a DayCountBase instance."
            ),
        ):
            CombinedCurve(
                benchmark_curve,
                FlatCreditSpreadCurve(spread=0.03, curve_date=curve_date),
                day_count_convention=123,
            )
