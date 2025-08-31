import re
import pandas as pd
import pytest
from pyfian.fixed_income.custom_flow_bond import CustomFlowBond


class TestCustomFlowBond:
    def test_custom_coupons_override(self):
        dt1 = pd.Timestamp("2025-01-01")
        dt2 = pd.Timestamp("2026-01-01")
        bond = CustomFlowBond(
            issue_dt="2024-01-01",
            maturity="2026-01-01",
            notional=100,
            custom_amortization={dt1: 10, dt2: 90},
            custom_coupons={dt1: 5, dt2: 2},
            custom_coupon_rates=10.0,
        )
        # Coupon values should override percent
        assert bond.coupon_flow[dt1] == 5
        assert bond.coupon_flow[dt2] == 2

    def test_custom_coupon_rates_float(self):
        dt1 = pd.Timestamp("2025-01-01")
        dt2 = pd.Timestamp("2026-01-01")
        bond = CustomFlowBond(
            issue_dt="2024-01-01",
            maturity="2026-01-01",
            notional=100,
            custom_amortization={dt1: 10, dt2: 90},
            custom_coupon_rates=10.0,
        )
        # First period: 10% of 100, second: 10% of 90
        assert bond.coupon_flow[dt1] == 10.0
        assert bond.coupon_flow[dt2] == 9.0

    def test_custom_coupon_rates_dict(self):
        dt1 = pd.Timestamp("2025-01-01")
        dt2 = pd.Timestamp("2026-01-01")
        bond = CustomFlowBond(
            issue_dt="2024-01-01",
            maturity="2026-01-01",
            notional=100,
            custom_amortization={dt1: 10, dt2: 90},
            custom_coupon_rates={dt1: 5.0, dt2: 2.0},
        )
        # First period: 5% of 100, second: 2% of 90
        assert bond.coupon_flow[dt1] == 5.0
        assert bond.coupon_flow[dt2] == 1.8

    def test_amortization_flow(self):
        dt1 = pd.Timestamp("2025-01-01")
        dt2 = pd.Timestamp("2026-01-01")
        bond = CustomFlowBond(
            issue_dt="2024-01-01",
            maturity="2026-01-01",
            notional=100,
            custom_amortization={dt1: 10, dt2: 90},
            custom_coupon_rates=0.0,
        )
        assert bond.amortization_flow[dt1] == 10
        assert bond.amortization_flow[dt2] == 90

    def test_payment_flow_sum(self):
        dt1 = pd.Timestamp("2025-01-01")
        dt2 = pd.Timestamp("2026-01-01")
        bond = CustomFlowBond(
            issue_dt="2024-01-01",
            maturity="2026-01-01",
            notional=100,
            custom_amortization={dt1: 10, dt2: 90},
            custom_coupon_rates=10.0,
        )
        # Payment = coupon + amortization
        assert bond.payment_flow[dt1] == 10.0 + 10
        assert bond.payment_flow[dt2] == 9.0 + 90

    def test_payment_flow_without_custom_amortization_nor_coupon_rates(self):
        maturity = pd.Timestamp("2026-01-01")
        bond = CustomFlowBond(
            issue_dt="2024-01-01",
            maturity="2026-01-01",
            notional=100,
        )
        # Payment = coupon + amortization
        assert bond.payment_flow[maturity] == 100.0

    def test_payment_flow_with_custom_amortization_not_coupon_rates_or_coupon(self):
        dt1 = pd.Timestamp("2025-01-01")
        dt2 = pd.Timestamp("2026-01-01")
        bond = CustomFlowBond(
            issue_dt="2024-01-01",
            maturity="2026-01-01",
            notional=100,
            custom_amortization={dt1: 50, dt2: 50},
        )
        # Payment = coupon + amortization
        assert bond.payment_flow[dt1] == 50.0
        assert bond.payment_flow[dt2] == 50.0

    def test_payment_flow_with_custom_amortization_not_equal_notional(self):
        dt1 = pd.Timestamp("2025-01-01")
        dt2 = pd.Timestamp("2026-01-01")

        with pytest.raises(
            ValueError, match=re.escape("Total amortization does not equal notional")
        ):
            CustomFlowBond(
                issue_dt="2024-01-01",
                maturity="2026-01-01",
                notional=100,
                custom_amortization={dt1: 50, dt2: 40},
            )
