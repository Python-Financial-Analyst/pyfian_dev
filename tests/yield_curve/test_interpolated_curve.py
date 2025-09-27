"""
Unit tests for InterpolatedCurve class in interpolated_curve.py
"""

import pytest
import pandas as pd
from pyfian.yield_curves.interpolated_curve import InterpolatedCurve
from pyfian.fixed_income.fixed_rate_bond import FixedRateBullet


class TestInterpolatedCurve:
    def setup_method(self):
        # Example zero rates
        self.zero_rates = {
            1: 0.04,
            2: 0.042,
            5: 0.045,
        }
        self.curve_date = pd.Timestamp("2025-08-22")
        self.curve = InterpolatedCurve(
            curve_date=self.curve_date, zero_rates=self.zero_rates
        )

    def test_discount_t(self):
        df = self.curve.discount_t(1)
        assert 0 < df < 1

    def test_get_rate(self):
        rate = self.curve.get_rate(1)
        assert isinstance(rate, float)

    def test_as_dict(self):
        d = self.curve.as_dict()
        assert "curve_date" in d
        assert "zero_rates" in d

    def test_repr(self):
        s = repr(self.curve)
        assert "InterpolatedCurve" in s

    def test_zero_rates_monotonic(self):
        for r in self.curve.zero_rates.values():
            assert r >= 0

    def test_invalid_init(self):
        with pytest.raises(TypeError):
            InterpolatedCurve(
                curve_date="2025-08-22", zero_rates=None, day_count_convention=object()
            )

    def test_invalid_day_count_convention(self):
        with pytest.raises(TypeError):
            InterpolatedCurve(
                curve_date="2025-08-22",
                zero_rates=self.zero_rates,
                day_count_convention=object(),
            )

    def test_initialize_with_bonds(self):
        # Use bonds to infer zero rates
        date = pd.Timestamp("2025-08-22")
        list_maturities_rates = [
            (pd.DateOffset(years=1), 1, 3.95),
            (pd.DateOffset(years=2), 2, 3.79),
            (pd.DateOffset(years=5), 5, 3.86),
            (pd.DateOffset(years=10), 10, 4.33),
            # (pd.DateOffset(years=30), 30, 4.92),
        ]
        one_year_offset = date + pd.DateOffset(years=1)
        bonds = []
        maturities = []
        for offset, maturity, cpn in list_maturities_rates:
            not_zero_coupon = date + offset > one_year_offset
            maturities.append(maturity)
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
        curve = InterpolatedCurve(curve_date=date, bonds=bonds, maturities=maturities)
        assert isinstance(curve.zero_rates, dict)
        assert all(isinstance(r, float) for r in curve.zero_rates.values())

    def test_initialize_with_bonds_50_year(self):
        # Use bonds to infer zero rates
        date = pd.Timestamp("2025-08-22")
        list_maturities_rates = [
            (pd.DateOffset(years=1), 1, 3.95),
            (pd.DateOffset(years=2), 2, 3.79),
            (pd.DateOffset(years=5), 5, 3.86),
            (pd.DateOffset(years=10), 10, 4.33),
            (pd.DateOffset(years=30), 30, 4.92),
            (pd.DateOffset(years=50), 50, 5.0),
        ]
        one_year_offset = date + pd.DateOffset(years=1)
        bonds = []
        maturities = []
        for offset, maturity, cpn in list_maturities_rates:
            not_zero_coupon = date + offset > one_year_offset
            maturities.append(maturity)
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

        curve = InterpolatedCurve(curve_date=date, bonds=bonds)
        assert isinstance(curve.zero_rates, dict)
        assert all(isinstance(r, float) for r in curve.zero_rates.values())

    def test_initialize_with_bond_with_no_price(self):
        date = pd.Timestamp("2025-08-22")
        list_maturities_rates = [
            (pd.DateOffset(years=1), 1, 3.95),
            (pd.DateOffset(years=2), 2, 3.79),
            (pd.DateOffset(years=5), 5, 3.86),
            (pd.DateOffset(years=10), 10, 4.33),
            (pd.DateOffset(years=30), 30, 4.92),
            (pd.DateOffset(years=50), 50, 5.0),
        ]
        one_year_offset = date + pd.DateOffset(years=1)
        bonds = []
        maturities = []
        for offset, maturity, cpn in list_maturities_rates:
            not_zero_coupon = date + offset > one_year_offset
            maturities.append(maturity)
            bond = FixedRateBullet(
                issue_dt=date,
                maturity=date + offset,
                cpn_freq=2 if not_zero_coupon else 0,
                cpn=cpn if not_zero_coupon else 0,
                settlement_date=date,
            )
            bonds.append(bond)

        # This should raise a ValueError because one bond has no price
        with pytest.raises(
            ValueError, match="All bonds must have a price to infer zero rates."
        ):
            InterpolatedCurve(curve_date=date, bonds=bonds)

    def test_initialize_with_zero_rates(self):
        zero_rates = {m: 0 for m in self.curve.maturities}
        curve = InterpolatedCurve(curve_date="2025-08-22", zero_rates=zero_rates)
        assert curve.zero_rates == zero_rates
