import re
import pytest
import pandas as pd
from pyfian.yield_curves.credit_spread import CreditSpreadCurve, FlatCreditSpreadCurve
from pyfian.yield_curves.flat_curve import FlatCurveBEY
from pyfian.fixed_income.fixed_rate_bond import FixedRateBullet
import matplotlib
import warnings


class TestCreditSpreadCurve:
    @pytest.fixture(autouse=True)
    def setup_curve(self):
        self.curve_date = pd.Timestamp("2025-08-22")
        self.benchmark_curve = FlatCurveBEY(bey=0.02, curve_date=self.curve_date)
        self.spreads = {1.0: 0.01, 2.0: 0.015, 5.0: 0.02}
        self.curve = CreditSpreadCurve(
            curve_date=self.curve_date,
            benchmark_curve=self.benchmark_curve,
            spreads=self.spreads,
            yield_calculation_convention=self.benchmark_curve.yield_calculation_convention,
            day_count_convention=self.benchmark_curve.day_count_convention,
        )

    def test_get_rate(self):
        # Should return benchmark rate + spread for t=1.0
        rate = self.curve.get_rate(1.0)

        expected = self.benchmark_curve.get_rate(1.0) + self.spreads[1.0]
        # Default convention is Annual, so convert accordingly
        assert pytest.approx(rate) == expected

    def test_date_rate(self):
        # Should return benchmark rate + spread for a given date
        date = self.curve_date + pd.DateOffset(years=2)
        t = self.benchmark_curve.day_count_convention.fraction(
            start=self.benchmark_curve.curve_date, current=date
        )
        expected = self.benchmark_curve.get_rate(t) + self.curve.date_spread(date)
        rate = self.curve.date_rate(date)
        assert pytest.approx(rate) == expected

    # test calling get_rate with a curve that has no benchmark_curve
    def test_get_rate_no_benchmark(self):
        curve = CreditSpreadCurve(
            curve_date=self.curve_date,
            spreads=self.spreads,
        )
        with pytest.raises(
            ValueError,
            match=re.escape("Benchmark curve (benchmark_curve) is not defined."),
        ):
            curve.get_rate(1.0)

    # test calling date_rate with a curve that has no benchmark_curve
    def test_date_rate_no_benchmark(self):
        curve = CreditSpreadCurve(
            curve_date=self.curve_date,
            spreads=self.spreads,
        )
        with pytest.raises(
            ValueError,
            match=re.escape("Benchmark curve (benchmark_curve) is not defined."),
        ):
            curve.date_rate(pd.Timestamp("2026-08-22"))

    # test calling get_rate with a curve that has a benchmark_curve with different day_count_convention gives a warning
    def test_get_rate_different_day_count_convention(self):
        curve = CreditSpreadCurve(
            curve_date=self.curve_date,
            benchmark_curve=self.benchmark_curve,
            spreads=self.spreads,
        )
        with warnings.catch_warnings(record=True) as w:
            curve.get_rate(1.0)
            assert len(w) == 1
            assert (
                "Benchmark curve's day count convention is different from the spread curve's."
                in str(w[0].message)
            )

    # test _get_optimal_spread with next_date == None
    def test_get_optimal_spread_no_next_date(self):
        curve = CreditSpreadCurve(
            curve_date=self.curve_date,
            benchmark_curve=self.benchmark_curve,
            spreads=self.spreads,
        )
        with pytest.raises(ValueError, match=re.escape("next_date must not be None.")):
            curve._get_optimal_spread(next_date=None, non_valued_payments={})

    def test_spread_from_bonds(self):
        # Use the same bonds as in test_instantiation_with_bonds_and_benchmark_curve
        list_maturities_rates = [
            (pd.DateOffset(years=1), 4),
            (pd.DateOffset(years=2), 4),
            (pd.DateOffset(years=5), 4),
            (pd.DateOffset(years=7), 4),
            (pd.DateOffset(years=10), 4),
        ]
        date = pd.Timestamp("2025-08-22")
        one_year_offset = date + pd.DateOffset(years=1)
        bonds = []
        for offset, cpn in list_maturities_rates:
            not_zero_coupon = date + offset > one_year_offset
            bond = FixedRateBullet(
                issue_dt=date,
                maturity=date + offset,
                cpn_freq=2 if not_zero_coupon else 0,
                cpn=cpn if not_zero_coupon else 0,
                price=100 if not_zero_coupon else None,
                yield_to_maturity=None if not_zero_coupon else cpn / 100,
                settlement_date=date,
            )
            bonds.append(bond)
        benchmark_curve = FlatCurveBEY(
            bey=0.02, curve_date=self.curve_date, day_count_convention="30/360"
        )
        curve = CreditSpreadCurve.spread_from_bonds(
            benchmark_curve=benchmark_curve, bonds=bonds
        )
        assert isinstance(curve, CreditSpreadCurve)
        assert curve.bonds == bonds
        for s in curve.spreads.values():
            assert abs(s - 0.02) < 1e-7

    def test_as_dict(self):
        d = self.curve.as_dict()
        assert "spreads" in d
        assert d["spreads"] == self.spreads

    def testget_t(self):
        assert pytest.approx(self.curve.get_t(1.0)) == 0.01
        assert pytest.approx(self.curve.get_t(2.0, 0.005)) == 0.02

    def test_date_spread(self):
        date = self.curve_date + pd.DateOffset(years=2)
        spread = self.curve.date_spread(date)
        assert isinstance(spread, float)

    def test_linear_interpolation(self):
        # t between 2.0 and 5.0
        t = 3.5
        expected = 0.015 + (0.02 - 0.015) * (t - 2.0) / (5.0 - 2.0)
        assert pytest.approx(self.curve._get_t(t)) == expected

    def test_repr(self):
        r = repr(self.curve)
        assert "CreditSpreadCurve" in r

    def test_instantiation_without_spreads_and_bonds(self):
        with pytest.raises(
            ValueError,
            match="Either spreads or bonds and benchmark curve must be provided",
        ):
            CreditSpreadCurve(
                curve_date=self.curve_date,
                benchmark_curve=self.benchmark_curve,
            )

    def test_instantiation_without_spreads_and_benchmark_curve(self):
        # bonds attribute is not defined in setup, so use a dummy value
        bonds = None
        with pytest.raises(
            ValueError,
            match="Either spreads or bonds and benchmark curve must be provided",
        ):
            CreditSpreadCurve(
                curve_date=self.curve_date,
                bonds=bonds,
            )

    # Test instantiation with invalid day_count_convention
    def test_instantiation_with_invalid_day_count_convention(self):
        with pytest.raises(
            TypeError,
            match="day_count_convention must be either a string or a DayCountBase instance.",
        ):
            CreditSpreadCurve(
                curve_date=self.curve_date,
                benchmark_curve=self.benchmark_curve,
                spreads=self.spreads,
                day_count_convention=123,  # Invalid type
            )

    # test instantiation with bonds and benchmark curve
    def test_instantiation_with_bonds_and_benchmark_curve(self):
        list_maturities_rates = [
            (pd.DateOffset(years=1), 4),
            (pd.DateOffset(years=2), 4),
            (pd.DateOffset(years=5), 4),
            (pd.DateOffset(years=7), 4),
            (pd.DateOffset(years=10), 4),
        ]
        date = pd.Timestamp("2025-08-22")
        one_year_offset = date + pd.DateOffset(years=1)
        bonds = []
        for offset, cpn in list_maturities_rates:
            not_zero_coupon = date + offset > one_year_offset
            bond = FixedRateBullet(
                issue_dt=date,
                maturity=date + offset,
                cpn_freq=2 if not_zero_coupon else 0,  # Less than a year
                cpn=cpn if not_zero_coupon else 0,
                price=100 if not_zero_coupon else None,
                yield_to_maturity=None if not_zero_coupon else cpn / 100,
                settlement_date=date,
            )
            # self = bond
            bonds.append(bond)
        benchmark_curve = FlatCurveBEY(
            bey=0.02, curve_date=self.curve_date, day_count_convention="30/360"
        )
        curve = CreditSpreadCurve(
            curve_date=self.curve_date,
            benchmark_curve=benchmark_curve,
            bonds=bonds,
            yield_calculation_convention="BEY",
            day_count_convention="30/360",
        )
        assert curve.bonds == bonds

        # assert all values from curve.spreads close to 0.02
        for s in curve.spreads.values():
            assert abs(s - 0.02) < 1e-7

    def test_get_spread(self):
        assert self.curve.get_spread(1.0) == self.spreads[1.0]
        assert self.curve.get_spread(1.0, 0.005) == self.spreads[1.0] + 0.005


class TestFlatCreditSpreadCurve:
    @pytest.fixture(autouse=True)
    def setup_curve(self):
        self.curve_date = pd.Timestamp("2025-08-22")
        self.spread = 0.01
        self.curve = FlatCreditSpreadCurve(
            spread=self.spread,
            curve_date=self.curve_date,
        )

    def test_get_spread(self):
        assert self.curve.get_spread(1.0) == self.spread
        assert self.curve.get_spread(1.0, 0.005) == self.spread + 0.005

    def test_get_rate(self):
        # FlatCreditSpreadCurve does not have a benchmark, so just returns spread
        rate = self.curve.get_t(1.0)
        assert rate == self.spread

    def test_date_rate(self):
        # Should return spread for any date
        date = self.curve_date + pd.DateOffset(years=1)
        rate = self.curve.date_spread(date)
        assert rate == self.spread

    def test_as_dict(self):
        d = self.curve.as_dict()
        assert d["spread"] == self.spread
        assert d["curve_date"] == self.curve_date

    def testget_t(self):
        assert self.curve.get_t(1.0) == self.spread
        assert self.curve.get_t(1.0, 0.005) == self.spread + 0.005

    def test_date_spread(self):
        date = self.curve_date + pd.DateOffset(years=1)
        assert self.curve.date_spread(date) == self.spread
        assert self.curve.date_spread(date, 0.002) == self.spread + 0.002

    def test_repr(self):
        r = repr(self.curve)
        assert "FlatCreditSpreadCurve" in r

    def test_plot_curve(self):
        matplotlib.use("Agg")
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                category=UserWarning,
                message="FigureCanvasAgg is non-interactive, and thus cannot be shown",
            )
            self.curve.plot_curve()

    def test_plot_curve_discount(self):
        with pytest.raises(ValueError):
            self.curve.plot_curve(kind="discount")
