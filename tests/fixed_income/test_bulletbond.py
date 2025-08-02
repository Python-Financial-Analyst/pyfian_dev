import pandas as pd
import pytest

from pyfian.fixed_income.bond import BulletBond
from pyfian.yield_curves.flat_curve import FlatCurveLog


class TestBulletBond:
    def test_make_payment_flow(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        dict_payments, dict_coupons, dict_amortization = bond.make_payment_flow()
        assert pd.to_datetime("2025-01-01") in dict_payments
        assert dict_payments[pd.to_datetime("2025-01-01")] == pytest.approx(105)

    def test_set_valuation_date(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        val_date = bond.set_valuation_date("2022-01-01")
        assert val_date == pd.to_datetime("2022-01-01")

    def test_set_yield_to_maturity_and_set_bond_price(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1, valuation_date="2022-01-01")
        bond.set_yield_to_maturity(0.05, "2022-01-01")
        assert isinstance(bond._bond_price, float)
        bond.set_bond_price(100, "2022-01-01")
        assert isinstance(bond._yield_to_maturity, float)

    def test_modified_duration(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        duration = bond.modified_duration(yield_to_maturity=0.05)
        assert isinstance(duration, float)

    def test_convexity(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        conv = bond.convexity(yield_to_maturity=0.05)
        assert isinstance(conv, float)

    def test_accrued_interest(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        accrued = bond.accrued_interest("2023-06-01")
        assert isinstance(accrued, float)

    def test_clean_and_dirty_price(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        dirty = bond.dirty_price(100, "2023-06-01")
        clean = bond.clean_price(dirty, "2023-06-01")
        assert pytest.approx(clean, 0.1) == 100

    def test_price_from_yield(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        price = bond.price_from_yield(0.05)
        assert isinstance(price, float)

    def test_cash_flows(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        flows = bond.cash_flows("2022-01-01")
        assert isinstance(flows, list)
        assert all(isinstance(f, float) for f in flows)

    def test_next_previous_coupon_date(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        next_date = bond.next_coupon_date("2023-06-01")
        prev_date = bond.previous_coupon_date("2023-06-01")
        assert isinstance(next_date, pd.Timestamp) or next_date is None
        assert isinstance(prev_date, pd.Timestamp) or prev_date is None

    def test_dv01_works(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        dv = bond.dv01(0.05)
        assert isinstance(dv, float)

    @pytest.mark.filterwarnings("ignore::UserWarning")
    def test_plot_cash_flows_smoke(self):
        import matplotlib

        matplotlib.use("Agg")  # Use non-interactive backend for test
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        # Should not raise
        bond.plot_cash_flows("2022-01-01")

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

    def test_notional_in_payment_flow(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1, notional=1000)
        dict_payments, dict_coupons, dict_amortization = bond.make_payment_flow()
        assert dict_payments[pd.Timestamp("2025-01-01")] == 1000 + (5 / 1) * 1000 / 100
        assert all(
            v == 50.0
            for k, v in dict_payments.items()
            if k != pd.Timestamp("2025-01-01")
        )

    def test_accrued_interest_positive(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 12, 1, notional=1000)
        valuation_date = pd.Timestamp("2020-07-01")
        accrued = bond.accrued_interest(valuation_date)
        assert accrued > 0

    def test_accrued_interest_zero_coupon(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 0, 0, notional=1000)
        valuation_date = pd.Timestamp("2020-07-01")
        accrued = bond.accrued_interest(valuation_date)
        assert accrued == 0

    def test_clean_dirty_price(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 10, 1, notional=1000)
        dirty = 1050
        clean = bond.clean_price(dirty, "2022-01-01")
        assert dirty == pytest.approx(bond.dirty_price(clean, "2022-01-01"))

    def test_to_dataframe(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1, notional=500)
        df = bond.to_dataframe()
        assert (
            "Cost" in df.columns
            and "Amortization" in df.columns
            and "Coupon" in df.columns
        )
        assert df["Flows"].iloc[-1] == 500 + (5 / 1) * 500 / 100

    def test_next_previous_coupon(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1, notional=100)
        d = pd.Timestamp("2023-06-01")
        next_cpn = bond.next_coupon_date(d)
        prev_cpn = bond.previous_coupon_date(d)
        assert next_cpn > d
        assert prev_cpn <= d

    def test_dv01(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1, notional=1000)
        ytm = 0.05
        dv01 = bond.dv01(ytm)
        # DV01 should be negative for a standard bond (price decreases as yield increases)
        assert dv01 < 0
        # Should be a small value in magnitude
        assert abs(dv01) < 5

    # Test error for positive coupon with zero frequency
    def test_positive_coupon_zero_frequency(self):
        with pytest.raises(
            ValueError,
            match="Coupon frequency must be greater than zero for positive coupons.",
        ):
            BulletBond("2020-01-01", "2025-01-01", 5, 0, notional=1000)

    # Test set input for yield_to_maturity but no valuation date
    def test_set_yield_to_maturity_no_valuation_date(self):
        with pytest.raises(
            ValueError, match="Valuation date must be set if yield to maturity is set."
        ):
            _ = BulletBond(
                "2020-01-01", "2025-01-01", 5, 1, notional=1000, yield_to_maturity=0.05
            )

    # Test set input for bond_price but no valuation date
    def test_set_bond_price_no_valuation_date(self):
        with pytest.raises(
            ValueError, match="Valuation date must be set if bond_price is set."
        ):
            BulletBond("2020-01-01", "2025-01-01", 5, 1, notional=1000, bond_price=95)

    # Test input bond with yield_to_maturity and valuation_date
    def test_bond_with_yield_to_maturity_and_valuation_date(self):
        bond = BulletBond(
            "2020-01-01",
            "2025-01-01",
            5,
            1,
            valuation_date="2022-01-01",
            yield_to_maturity=0.05,
        )
        assert bond._yield_to_maturity == 0.05
        assert bond._valuation_date == pd.to_datetime("2022-01-01")

    # Test input bond with yield_to_maturity and valuation_date
    def test_bond_with_bond_price_and_valuation_date(self):
        bond = BulletBond(
            "2020-01-01", "2025-01-01", 5, 1, valuation_date="2022-01-01", bond_price=95
        )
        assert bond._bond_price == 95
        assert bond._valuation_date == pd.to_datetime("2022-01-01")

    # Test input bond with yield_to_maturity and bond_price not compatible
    def test_bond_with_yield_to_maturity_and_bond_price_not_compatible(self):
        with pytest.raises(
            ValueError,
            match="Bond price calculated by yield to maturity does not match the current bond price.",
        ):
            BulletBond(
                "2020-01-01",
                "2025-01-01",
                5,
                1,
                valuation_date="2022-01-01",
                yield_to_maturity=0.05,
                bond_price=95,
            )

    # Test input bond with yield_to_maturity and bond_price compatible
    def test_bond_with_yield_to_maturity_and_bond_price_compatible(self):
        BulletBond(
            "2020-01-01",
            "2025-01-01",
            5,
            1,
            valuation_date="2022-01-01",
            yield_to_maturity=0.05,
            bond_price=100.0139744,
        )

    # Test set a new valuation date
    def test_set_new_valuation_date(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1, valuation_date="2022-01-01")
        new_date = bond.set_valuation_date("2023-01-01")
        assert new_date == pd.to_datetime("2023-01-01")
        assert bond._valuation_date == pd.to_datetime("2023-01-01")

    # Test set a new valuation date but not resetting yield_to_maturity
    def test_set_new_valuation_date_not_resetting_yield_to_maturity(self):
        bond = BulletBond(
            "2020-01-01",
            "2025-01-01",
            5,
            1,
            valuation_date="2022-01-01",
            yield_to_maturity=0.05,
        )
        new_date = bond.set_valuation_date("2023-01-01", reset_yield_to_maturity=False)
        assert new_date == pd.to_datetime("2023-01-01")
        assert bond._valuation_date == pd.to_datetime("2023-01-01")
        assert bond._yield_to_maturity == 0.05

    # Test set a valuation date as None, and check that _bond_price is None and _yield_to_maturity is None as well
    def test_set_valuation_date_none(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        bond.set_valuation_date(None)
        assert bond._bond_price is None
        assert bond._yield_to_maturity is None

    # Test set yield to maturity to None
    def test_set_yield_to_maturity_none(self):
        bond = BulletBond(
            "2020-01-01",
            "2025-01-01",
            5,
            1,
            valuation_date="2022-01-01",
            yield_to_maturity=0.05,
        )
        bond.set_yield_to_maturity(None)
        assert bond._yield_to_maturity is None

    # Test set yield to maturity but there was no valuation date
    def test_set_yield_to_maturity_none_no_valuation_date(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        with pytest.raises(
            ValueError,
            match="Valuation date must be set since there is no default valuation_date for the bond.",
        ):
            bond.set_yield_to_maturity(0.05)

    # Test set bond price to None
    def test_set_bond_price_none(self):
        bond = BulletBond(
            "2020-01-01",
            "2025-01-01",
            5,
            1,
            valuation_date="2022-01-01",
            bond_price=100,
        )
        bond.set_bond_price(None)
        assert bond._bond_price is None

    # Test set bond price but there is no valuation date
    def test_set_bond_price_none_no_valuation_date(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1)
        with pytest.raises(
            ValueError,
            match="Valuation date must be set since there is no default valuation_date for the bond.",
        ):
            bond.set_bond_price(100)

    # Test modified_duration for a bond with yield to maturity already set
    def test_modified_duration_with_yield(self):
        bond = BulletBond(
            "2020-01-01",
            "2025-01-01",
            5,
            1,
            valuation_date="2022-01-01",
            yield_to_maturity=0.05,
        )
        bond.modified_duration()

    # Test modified_duration for a bond setting a price
    def test_modified_duration_with_price(self):
        bond = BulletBond("2020-01-01", "2025-01-01", 5, 1, valuation_date="2022-01-01")
        bond.modified_duration(bond_price=100)
