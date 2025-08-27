"""
Unit tests for ParCurve class in par_curve.py

Examples
--------
>>> from pyfian.yield_curves.par_curve import ParCurve
>>> curve = ParCurve(curve_date="2025-08-22", par_rates=par_rates)
>>> curve.discount_t(1)
... # returns discount factor for 1 year
>>> curve.get_rate(1)
... # returns par rate for 1 year
"""

import pytest
import pandas as pd
from pyfian.yield_curves.par_curve import ParCurve


class TestParCurve:
    def setup_method(self):
        # Example par rates from the docstring
        list_maturities_rates = [
            (pd.DateOffset(months=1), 4.49),
            (pd.DateOffset(months=3), 4.32),
            (pd.DateOffset(months=6), 4.14),
            (pd.DateOffset(years=1), 3.95),
            (pd.DateOffset(years=2), 3.79),
            (pd.DateOffset(years=3), 3.75),
            (pd.DateOffset(years=5), 3.86),
            (pd.DateOffset(years=7), 4.07),
            (pd.DateOffset(years=10), 4.33),
            (pd.DateOffset(years=20), 4.89),
            (pd.DateOffset(years=30), 4.92),
        ]
        date = pd.Timestamp("2025-08-22")
        one_year_offset = date + pd.DateOffset(years=1)
        par_rates = {}
        for offset, cpn in list_maturities_rates:
            not_zero_coupon = date + offset > one_year_offset
            bond = {
                "cpn_freq": 2 if not_zero_coupon else 0,
                "cpn": cpn if not_zero_coupon else 0,
                "bond_price": 100 if not_zero_coupon else None,
                "yield_to_maturity": None if not_zero_coupon else cpn / 100,
            }
            par_rates[offset] = bond
        self.curve = ParCurve(curve_date=date, par_rates=par_rates)

    def test_discount_t(self):
        # Test discount factor for 1 year
        df = self.curve.discount_t(1)
        assert 0 < df < 1

    def test_get_rate(self):
        # Test par rate for 1 year
        rate = self.curve.get_rate(1)
        assert isinstance(rate, float)

    def test_as_dict(self):
        d = self.curve.as_dict()
        assert "curve_date" in d
        assert "par_rates" in d
        assert "zero_rates" in d

    def test_repr(self):
        s = repr(self.curve)
        assert "SpotCurve" in s

    def test_zero_rates_monotonic(self):
        # Spot rates should be non-negative
        for r in self.curve.zero_rates.values():
            assert r >= 0

    def test_invalid_init(self):
        with pytest.raises(ValueError):
            ParCurve(curve_date="2025-08-22")

    def test_invalid_day_count_convention(self):
        with pytest.raises(TypeError):
            ParCurve(curve_date="2025-08-22", par_rates={}, day_count_convention=None)
