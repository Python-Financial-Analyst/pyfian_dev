import pandas as pd
import pytest

from pyfian.fixed_income.bond import BulletBond
from pyfian.yield_curves.flat_curve import FlatCurveLog


class TestBulletBond:
    def test_make_payment_flow(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        payments = bond.make_payment_flow()
        assert pd.to_datetime("2025-01-01") in payments
        assert payments[pd.to_datetime("2025-01-01")] == pytest.approx(105)

    def test_filter_payment_flow(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        flows = bond.filter_payment_flow("2022-01-01")
        assert all(date >= pd.to_datetime("2022-01-01") for date in flows.keys())

    def test_calculate_time_to_payments(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        times = bond.calculate_time_to_payments("2022-01-01")
        assert all(isinstance(t, float) for t in times.keys())

    def test_value_with_curve(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        curve = FlatCurveLog(0.05, "2020-01-01")
        value, pv = bond.value_with_curve(curve)
        assert isinstance(value, float)
        assert isinstance(pv, dict)

    def test_yield_to_maturity(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        ytm = bond.yield_to_maturity(bond_price=95)
        assert isinstance(ytm, float)

    def test_filter_payment_flow_expired_bond(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        # Valuation date after maturity
        flows = bond.filter_payment_flow("2026-01-01")
        assert flows == {}, f"Expected empty dict for expired bond, got: {flows}"

    def test_repr(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        result = repr(bond)
        expected = (
            "BulletBond(issue_dt=2020-01-01 00:00:00, maturity=2025-01-01 00:00:00, "
            "cpn=5, cpn_freq=1)"
        )
        assert result == expected, f"__repr__ output mismatch: {result}"
