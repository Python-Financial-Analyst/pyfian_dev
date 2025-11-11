import numpy as np
import pytest
import pandas as pd
from pyfian.fixed_income.floating_rate_note import FloatingRateNote
from pyfian.time_value.irr import xirr_base
from pyfian.yield_curves.flat_curve import FlatCurveBEY, FlatCurveLog
from pyfian.yield_curves.zero_coupon_curve import ZeroCouponCurve
from pyfian.fixed_income.fixed_rate_bond import FixedRateBullet


class TestFloatingRateNote:
    @pytest.fixture(autouse=True)
    def setup_note(self):
        self.flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        self.zero_curve = ZeroCouponCurve(
            curve_date="2020-01-01",
            zero_rates={
                1 / 12: 0.0449,
                0.25: 0.0432,
                0.5: 0.0414,
                1.0: 0.0395,
                2.0: 0.0379,
                3.0: 0.0375,
                5.0: 0.0386,
                7.0: 0.0407,
                10.0: 0.0433,
                20.0: 0.0489,
                30.0: 0.0492,
            },
            yield_calculation_convention="BEY",
        )
        self.zero_curve_2020_01_05 = ZeroCouponCurve(
            curve_date="2020-01-05",
            zero_rates={
                1 / 12: 0.0449,
                0.25: 0.0432,
                0.5: 0.0414,
                1.0: 0.0395,
                2.0: 0.0379,
                3.0: 0.0375,
                5.0: 0.0386,
                7.0: 0.0407,
                10.0: 0.0433,
                20.0: 0.0489,
                30.0: 0.0492,
            },
            yield_calculation_convention="BEY",
        )
        self.note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=self.flat_curve,
            current_ref_rate=0.02,
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )

    # test initialization of FloatingRateNote with settlement_date
    def test_initialization_with_settlement_date(self):
        note_with_settlement = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            quoted_margin=50,
            cpn_freq=2,
            settlement_date="2020-01-05",
            notional=1000,
        )
        assert note_with_settlement.get_settlement_date() == pd.to_datetime(
            "2020-01-05"
        )

    # test set_settlement_date with None
    def test_set_settlement_date_none(self):
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        note.set_settlement_date(None)
        assert note.get_settlement_date() is None

    # test initialization of FloatingRateNote without settlement_date but with discount margin raises ValueError
    def test_initialization_without_settlement_date_with_discount_margin(self):
        with pytest.raises(
            ValueError,
            match="Settlement date must be set if discount margin is set.",
        ):
            FloatingRateNote(
                issue_dt="2020-01-01",
                maturity="2025-01-01",
                ref_rate_curve=self.flat_curve,
                current_ref_rate=0.02,
                quoted_margin=50,
                cpn_freq=2,
                discount_margin=0.01,
                notional=1000,
            )

    # test initialization with invalid day_count_convention
    def test_initialization_invalid_day_count_convention(self):
        with pytest.raises(
            TypeError,
            match="day_count_convention must be either a string or a DayCountBase instance.",
        ):
            FloatingRateNote(
                issue_dt="2020-01-01",
                maturity="2025-01-01",
                ref_rate_curve=self.flat_curve,
                current_ref_rate=0.02,
                quoted_margin=50,
                cpn_freq=2,
                day_count_convention=1234,
                notional=1000,
            )

    # test initialization with discount_margin and settlement_date
    def test_initialization_with_discount_margin_and_settlement_date(self):
        note_with_discount_margin = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            quoted_margin=50,
            cpn_freq=2,
            settlement_date="2020-01-05",
            discount_margin=0.01,
            notional=1000,
        )
        assert note_with_discount_margin.get_discount_margin() == 0.01

    # test initialization with price and settlement_date
    def test_initialization_with_price_and_settlement_date(self):
        note_with_price = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            quoted_margin=50,
            cpn_freq=2,
            settlement_date="2020-01-05",
            price=101.5,
            notional=1000,
        )
        assert note_with_price.get_price() == 101.5

    # test initialization with price but without settlement_date raises ValueError
    def test_initialization_with_price_without_settlement_date(self):
        with pytest.raises(
            ValueError,
            match="Settlement date must be set if price is set.",
        ):
            FloatingRateNote(
                issue_dt="2020-01-01",
                maturity="2025-01-01",
                ref_rate_curve=self.flat_curve,
                current_ref_rate=0.02,
                quoted_margin=50,
                cpn_freq=2,
                price=101.5,
                notional=1000,
            )

    # initialize FloatingRateNote with ref_rate_curve as ZeroCouponCurve and settlement_date
    def test_initialization_with_zero_coupon_curve_and_settlement_date(self):
        note_with_zero_curve = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=self.zero_curve_2020_01_05,
            current_ref_rate=0.02,
            quoted_margin=50,
            cpn_freq=2,
            settlement_date="2020-01-05",
            notional=1000,
            price=100.0,
        )
        assert isinstance(note_with_zero_curve.ref_rate_curve, ZeroCouponCurve)
        # It should have calculated yield to maturity
        assert note_with_zero_curve.get_yield_to_maturity() is not None, (
            "Yield to maturity should be calculated when using ZeroCouponCurve."
        )

    # test initialization with ref_rate_curve with a date different from settlement_date raises ValueError
    def test_initialization_with_ref_rate_curve_date_mismatch(self):
        with pytest.raises(
            ValueError,
            match="Settlement date must be the same as the curve date of the reference rate curve.",
        ):
            FloatingRateNote(
                issue_dt="2020-01-01",
                maturity="2025-01-01",
                ref_rate_curve=self.zero_curve,
                current_ref_rate=0.02,
                quoted_margin=50,
                cpn_freq=2,
                settlement_date="2020-01-05",
                notional=1000,
            )

    # test _should_calculate when current_ref_rate is not provided but self.current_ref_rate is None
    def test_should_calculate_without_current_ref_rate(self):
        note_without_current_ref_rate = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=self.flat_curve,
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        # Accessing protected member for testing purposes

        # When settlement date does not match resettlement date or issue date, it can not calculate
        should_calculate = note_without_current_ref_rate._should_calculate(
            settlement_date="2020-01-05",
            ref_rate_curve=self.zero_curve_2020_01_05,
            current_ref_rate=None,
        )
        assert not should_calculate[0], (
            "Should not calculate when current_ref_rate is not provided and self.current_ref_rate is None and it is not a coupon setting date."
        )

        should_calculate = note_without_current_ref_rate._should_calculate(
            settlement_date="2020-01-01",
            ref_rate_curve=self.flat_curve,
            current_ref_rate=None,
        )
        assert should_calculate[0], (
            "Should calculate when settlement date matches issue date despite current_ref_rate not being provided."
        )

    # test _should_calculate when ref_rate_curve date and settlement_date do not match
    def test_should_calculate_ref_rate_curve_date_mismatch(self):
        should_calculate = self.note._should_calculate(
            settlement_date="2020-01-01",
            ref_rate_curve=self.zero_curve_2020_01_05,
            current_ref_rate=0.02,
        )
        assert not should_calculate[0], (
            "Should not calculate when ref_rate_curve date and settlement_date do not match."
        )

    # test resetting settlement date erases discount margin and price
    def test_set_settlement_date_resets_discount_margin_and_price(self):
        note_with_discount_and_price = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=self.flat_curve,
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        note_with_discount_and_price.set_settlement_date("2020-01-01")
        note_with_discount_and_price.set_discount_margin(100)
        note_with_discount_and_price.set_price(101.5)
        note_with_discount_and_price.set_settlement_date("2020-06-01")
        assert note_with_discount_and_price.get_discount_margin() is None
        assert note_with_discount_and_price.get_price() is None

    # test set_settlement_date with date before issue date raises ValueError
    def test_set_settlement_date_before_issue_date(self):
        with pytest.raises(
            ValueError,
            match="Settlement date cannot be before issue date.",
        ):
            self.note.set_settlement_date("2019-12-31")

    def test_payment_flow(self):
        payments, spreads, amortization = self.note.make_payment_flow()
        assert isinstance(payments, dict)
        assert isinstance(spreads, dict)
        assert isinstance(amortization, dict)
        assert self.note.maturity in payments
        assert payments[self.note.maturity] > 0

    def test_accrued_interest(self):
        accrued = self.note.accrued_interest("2022-07-01")
        assert isinstance(accrued, float)
        assert accrued >= 0

    def test_value_with_flat_curve(self):
        value, pv = self.note.value_with_curve(self.flat_curve)
        assert isinstance(value, float)
        assert isinstance(pv, dict)
        assert value > 0

    def test_value_with_zero_curve(self):
        value, pv = self.note.value_with_curve(self.zero_curve)
        assert isinstance(value, float)
        assert isinstance(pv, dict)
        assert value > 0

    # test set_discount_margin without settlement_date raises ValueError
    def test_set_discount_margin_without_settlement_date(self):
        note_without_settlement = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=self.flat_curve,
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        with pytest.raises(
            ValueError,
            match="Settlement date must be set since there is no default settlement_date for the bond.",
        ):
            note_without_settlement.set_discount_margin(100)

    # test set_discount_margin to None after initializing with price and discount_margin
    def test_set_discount_margin_to_none(self):
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=self.flat_curve,
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        note.set_settlement_date("2020-01-01")
        note.set_discount_margin(100)
        note.set_price(101.5)
        note.set_discount_margin(None)
        assert note.get_discount_margin() is None
        assert note.get_price() is None

    # test set_price without settlement_date raises ValueError
    def test_set_price_without_settlement_date(self):
        note_without_settlement = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=self.flat_curve,
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        with pytest.raises(
            ValueError,
            match="Settlement date must be set since there is no default settlement_date for the bond.",
        ):
            note_without_settlement.set_price(101.5)

    # test set_price to None resets also discount_margin
    def test_set_price_to_none_resets_discount_margin(self):
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=self.flat_curve,
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        note.set_settlement_date("2020-01-01")
        note.set_discount_margin(100)
        note.set_price(101.5)
        note.set_price(None)
        assert note.get_price() is None
        assert note.get_discount_margin() is None

    # test _validate_yield_calculation_convention with invalid convention raises ValueError
    def test_validate_yield_calculation_convention_invalid(self):
        with pytest.raises(
            ValueError,
            match="Unsupported yield calculation convention: INVALID_CONVENTION",
        ):
            self.note._validate_yield_calculation_convention("INVALID_CONVENTION")

    # test _validate_following_coupons_day_count with invalid convention raises ValueError
    def test_validate_following_coupons_day_count_invalid(self):
        with pytest.raises(
            ValueError,
            match="Unsupported following coupons day count convention",
        ):
            self.note._validate_following_coupons_day_count("actual/actual-ISDA")

    # test make_expected_cash_flow without ref_rate_curve raises ValueError
    def test_make_expected_cash_flow_without_ref_rate_curve(self):
        note_without_ref_rate_curve = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )

        with pytest.raises(
            ValueError,
            match="Either ref_rate_curve or self.ref_rate_curve must be provided.",
        ):
            note_without_ref_rate_curve.make_expected_cash_flow(
                settlement_date="2022-01-01",
            )

    # test make_expected_cash_flow with different ref_rate_curve date and settlement_date raises ValueError
    def test_make_expected_cash_flow_ref_rate_curve_date_mismatch(self):
        with pytest.raises(
            ValueError,
            match="Settlement date must be the same as the curve date of the reference rate curve.",
        ):
            self.note.make_expected_cash_flow(
                ref_rate_curve=self.zero_curve_2020_01_05,
                settlement_date="2022-01-01",
            )

    # test make_expected_cash_flow with no current_ref_rate and self.current_ref_rate is None
    # raises ValueError if the date is not issue date or resettlement date
    def test_make_expected_cash_flow_without_current_ref_rate(self):
        flat_curve_with_not_resettlement = FlatCurveBEY(
            curve_date="2022-01-05", bey=0.03
        )
        note_without_current_ref_rate = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve_with_not_resettlement,
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        with pytest.raises(
            ValueError,
            match="Either current_ref_rate or self.current_ref_rate must be provided if issue_dt is not equal to settlement_date.",
        ):
            note_without_current_ref_rate.make_expected_cash_flow(
                ref_rate_curve=flat_curve_with_not_resettlement,
                settlement_date=flat_curve_with_not_resettlement.curve_date,
            )

    # test make_expected_cash_flow for a bond with 0 quoted margin
    def test_make_expected_cash_flow_zero_quoted_margin(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.025)
        note_zero_margin = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2023-01-01",
            ref_rate_curve=flat_curve,
            current_ref_rate=0.025,
            quoted_margin=0,
            cpn_freq=2,
            notional=1000,
        )
        cash_flows = note_zero_margin.make_expected_cash_flow(
            ref_rate_curve=flat_curve,
            settlement_date="2020-01-01",
        )
        coupon_amount = (
            flat_curve.bey / note_zero_margin.cpn_freq * note_zero_margin.notional
        )

        # All spread flows should be zero
        for d, spread in cash_flows.items():
            if d == note_zero_margin.maturity:
                assert spread == coupon_amount + note_zero_margin.notional, (
                    "Spread flow should equal coupon amount plus notional for zero quoted margin."
                )
            else:
                assert spread == coupon_amount, (
                    "Spread flow should equal coupon amount for zero quoted margin."
                )

    # test make_expected_cash_flow for a zero coupon floating rate note
    def test_make_expected_cash_flow_zero_coupon(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.03)
        note_zero_coupon = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2023-01-01",
            ref_rate_curve=flat_curve,
            quoted_margin=0,
            cpn_freq=0,
            notional=1000,
        )
        cash_flows = note_zero_coupon.make_expected_cash_flow(
            ref_rate_curve=flat_curve,
            settlement_date="2020-01-01",
        )

        # There should be only one cash flow at maturity
        assert len(cash_flows) == 1, (
            "There should be only one cash flow for a zero coupon floating rate note."
        )
        for d, flow in cash_flows.items():
            assert d == note_zero_coupon.maturity, (
                "The only cash flow should occur at maturity for a zero coupon floating rate note."
            )
            assert flow == note_zero_coupon.notional, (
                "The cash flow at maturity should equal the notional for a zero coupon floating rate note."
            )

    # test discount_margin
    def test_discount_margin(self):
        # Create a flat curve from the par rates
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.03)
        # Create a floating rate note
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        note.set_settlement_date("2020-01-01")
        note.set_price(1000.0)
        # Calculate the discount margin
        discount_margin = note.discount_margin(
            current_ref_rate=0.03, max_iter=None, tol=None
        )
        # Check discount margin should be very close to 0.005 (50 basis points)
        assert abs(discount_margin - 50) < 1e-8, (
            "Discount margin calculation is incorrect."
        )

    # test discount_margin without ref_rate_curve raises ValueError
    def test_discount_margin_without_ref_rate_curve(self):
        note_without_ref_rate_curve = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        note_without_ref_rate_curve.set_settlement_date("2020-01-01")
        note_without_ref_rate_curve.set_price(1000.0)
        with pytest.raises(
            ValueError,
            match="Either ref_rate_curve or self.ref_rate_curve must be provided.",
        ):
            note_without_ref_rate_curve.discount_margin(
                settlement_date="2020-01-01",
                ref_rate_curve=None,
                current_ref_rate=0.03,
            )

    # test discount_margin with price None raises ValueError with "Bond price must be set to calculate yield to maturity."
    def test_discount_margin_with_price_none(self):
        with pytest.raises(
            ValueError,
            match="Bond price must be set to calculate discount margin.",
        ):
            self.note.discount_margin(
                settlement_date="2020-01-01",
                price=None,
                ref_rate_curve=self.flat_curve,
                current_ref_rate=0.02,
            )

    # test expected_yield_to_maturity
    def test_expected_yield_to_maturity(self):
        # Create a flat curve from the par rates
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.03)
        # Create a floating rate note
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        note.set_settlement_date("2020-01-01")
        note.set_price(1000.0)
        # Calculate the yield to maturity
        ytm = note.expected_yield_to_maturity(
            ref_rate_curve=flat_curve,
            current_ref_rate=0.03,
            max_iter=None,
            tol=None,
        )
        # Check yield to maturity should be very close to 3.5% (0.035)
        assert abs(ytm - 0.035) < 1e-8, "Yield to maturity calculation is incorrect."

    # test yield_to_maturity
    def test_yield_to_maturity(self):
        # Create a flat curve from the par rates
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.03)
        # Create a floating rate note
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        note.set_settlement_date("2020-01-01")
        note.set_price(1000.0)
        # Calculate the yield to maturity
        ytm = note.yield_to_maturity(
            current_ref_rate=0.03,
            max_iter=None,
            tol=None,
        )
        # Check yield to maturity should be very close to 3.5% (0.035)
        assert abs(ytm - 0.035) < 1e-8, "Yield to maturity calculation is incorrect."

    # test expected_yield_to_maturity without price raises ValueError with "Bond price must be set to calculate expected yield to maturity."
    def test_expected_yield_to_maturity_without_price(self):
        with pytest.raises(
            ValueError,
            match="Bond price must be set to calculate expected yield to maturity.",
        ):
            self.note.expected_yield_to_maturity(
                settlement_date="2020-01-01",
                price=None,
                ref_rate_curve=self.flat_curve,
                current_ref_rate=0.02,
            )

    # test expected_yield_to_maturity with Continous compounding convention
    def test_expected_yield_to_maturity_continous_compounding(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.03)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        note.set_settlement_date("2020-01-01")
        note.set_price(1000.0)
        ytm = note.expected_yield_to_maturity(
            ref_rate_curve=flat_curve,
            current_ref_rate=0.03,
            max_iter=None,
            tol=None,
            yield_calculation_convention="CONTINUOUS",
        )
        timed_payments = note.calculate_time_to_payments(
            yield_calculation_convention="CONTINUOUS"
        )
        # add 1.5% of notional to every payment
        timed_payments = {
            k: v + 0.015 * note.notional for k, v in timed_payments.items()
        }
        timed_payments[0] = -note._price
        timed_payments = dict(sorted(timed_payments.items()))
        payment_flow = list(timed_payments.values())
        times = list(timed_payments.keys())
        initial_guess = 0.03
        tol = 1e-8
        max_iter = 1000

        result = xirr_base(
            cash_flows=payment_flow,
            times=times,
            guess=initial_guess,
            tol=tol,
            max_iter=max_iter,
        )
        # convert result to continuous compounding
        result = np.log(1 + result)
        assert abs(ytm - result) < 1e-8, (
            "Yield to maturity calculation with continuous compounding is incorrect."
        )

    # test yield_to_maturity without ref_rate_curve raises ValueError
    def test_yield_to_maturity_without_ref_rate_curve(self):
        note_without_ref_rate_curve = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        note_without_ref_rate_curve.set_settlement_date("2020-01-01")
        note_without_ref_rate_curve.set_price(1000.0)
        with pytest.raises(
            ValueError,
            match="Either ref_rate_curve or self.ref_rate_curve must be provided.",
        ):
            note_without_ref_rate_curve.yield_to_maturity(
                settlement_date="2020-01-01",
                ref_rate_curve=None,
                current_ref_rate=0.03,
            )

    # test accrued_interest with 0 coupon frequency returns 0
    def test_accrued_interest_zero_coupon_frequency(self):
        note_zero_coupon = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=self.flat_curve,
            current_ref_rate=0.02,
            quoted_margin=50,
            cpn_freq=0,
            notional=1000,
        )
        accrued = note_zero_coupon.accrued_interest("2022-07-01")
        assert accrued == 0, "Accrued interest should be 0 for zero coupon frequency."

    # test accrued_interest without current_ref_rate raises ValueError
    def test_accrued_interest_without_current_ref_rate(self):
        note_without_current_ref_rate = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=self.flat_curve,
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        with pytest.raises(
            ValueError,
            match="Either current_ref_rate or self.current_ref_rate must be provided.",
        ):
            note_without_current_ref_rate.accrued_interest("2022-07-01")

    # test accrued_interest before first coupon
    def test_accrued_interest_before_first_coupon(self):
        accrued = self.note.accrued_interest("2020-06-01")
        assert accrued >= 0, "Accrued interest should be non-negative."

    def test_accrued_interest_after_first_coupon(self):
        accrued = self.note.accrued_interest("2021-06-01")
        assert accrued >= 0, "Accrued interest should be non-negative."

    # test __repr__
    def test_repr(self):
        repr_str = repr(self.note)
        assert "FloatingRateNote" in repr_str
        assert "issue_dt=2020-01-01" in repr_str
        assert "maturity=2025-01-01" in repr_str
        assert "quoted_margin=50" in repr_str

    # test effective_duration
    def test_effective_duration(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        epsilon = 0.0000001
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            discount_margin=0,
        )
        note_plus = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=FlatCurveBEY(curve_date="2020-01-01", bey=0.02 + epsilon),
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            discount_margin=0,
        )
        note_minus = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=FlatCurveBEY(curve_date="2020-01-01", bey=0.02 - epsilon),
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            discount_margin=0,
        )

        eff_duration_calculated = note_minus.get_price() - note_plus.get_price()
        eff_duration_calculated /= 2 * epsilon * note.get_price()

        effective_duration_class = note.effective_duration()

        assert isinstance(eff_duration_calculated, float)
        # eff_duration_calculated equals effective_duration_class within margin of error
        assert abs(eff_duration_calculated - effective_duration_class) < 1e-8, (
            "Effective duration should equal calculated effective duration within margin of error."
        )

    # test modified_duration equals effective_duration
    def test_modified_duration_equals_effective_duration(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            discount_margin=0,
        )

        effective_duration = note.effective_duration()
        modified_duration = note.modified_duration()

        assert isinstance(modified_duration, float)
        assert abs(effective_duration - modified_duration) < 1e-8, (
            "Modified duration should equal effective duration."
        )

    # test modified_duration raises ValueError when
    # "Unable to resolve yield to maturity. You must input settlement_date and either yield_to_maturity or price. Previous information was not available."
    def test_modified_duration_without_yield_or_price(self):
        note_without_settlement = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=self.flat_curve,
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        with pytest.raises(
            ValueError,
            match="Unable to resolve yield to maturity. You must input settlement_date and either yield_to_maturity or price. Previous information was not available.",
        ):
            note_without_settlement.modified_duration()

    # test modified_duration with continuous compounding
    def test_modified_duration_continuous_compounding(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            discount_margin=0,
        )
        modified_duration = note.modified_duration(
            yield_calculation_convention="CONTINUOUS"
        )
        effective_duration = note.effective_duration(
            yield_calculation_convention="CONTINUOUS"
        )

        assert isinstance(modified_duration, float)
        assert abs(modified_duration - effective_duration) < 1e-8, (
            "Modified duration should equal effective duration with continuous compounding."
        )

    # test spread_duration equals effective_spread_duration
    def test_spread_duration_equals_effective_spread_duration(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            quoted_margin=100,
            discount_margin=100,
        )

        effective_spread_duration = note.effective_spread_duration()
        spread_duration = note.spread_duration()

        assert isinstance(spread_duration, float)
        assert abs(effective_spread_duration - spread_duration) < 1e-7, (
            "Spread duration should equal effective spread duration."
        )

    # test spread_duration with Continuous compounding
    def test_spread_duration_continuous_compounding(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            quoted_margin=100,
            discount_margin=100,
        )
        bond = FixedRateBullet(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            cpn=3,
            cpn_freq=2,
            settlement_date="2020-01-01",
            price=100,
        )
        modified_duration = bond.modified_duration(
            yield_calculation_convention="CONTINUOUS"
        )

        spread_duration = note.spread_duration(
            yield_calculation_convention="CONTINUOUS"
        )

        assert isinstance(spread_duration, float)
        assert abs(spread_duration - modified_duration) < 1e-8, (
            "Spread duration should equal modified duration with continuous compounding."
        )

    # test effective_spread_duration with Continuous compounding equals spread_duration
    def test_effective_spread_duration_continuous_compounding(self):
        flat_curve = FlatCurveLog(curve_date="2020-01-01", log_rate=0.02)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            cpn_freq=1,
            settlement_date="2020-01-01",
            quoted_margin=100,
            price=100,
        )

        effective_spread_duration = note.effective_spread_duration(
            yield_calculation_convention="CONTINUOUS"
        )
        spread_duration = note.spread_duration(
            yield_calculation_convention="CONTINUOUS"
        )

        assert isinstance(effective_spread_duration, float)
        assert abs(effective_spread_duration - spread_duration) < 1e-2, (
            "Effective spread duration should equal spread duration with continuous compounding."
        )

    # test effective_duration raises ValueError when you can not calculate yield to maturity
    def test_effective_duration_without_yield_or_price(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        note_without_settlement = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        with pytest.raises(
            ValueError,
            match="Unable to determine yield to maturity.",
        ):
            note_without_settlement.effective_duration()

    # test effective_spread_duration raises ValueError when you can not calculate yield to maturity
    def test_effective_spread_duration_without_yield_or_price(self):
        note_without_settlement = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        with pytest.raises(
            ValueError,
            match="There is not enough information to calculate prices to calculate spread duration.",
        ):
            note_without_settlement.effective_spread_duration()

    # test DV01
    def test_dv01(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            discount_margin=0,
        )
        dv01 = note.dv01()

        # Calculate DV01 manually
        epsilon = 0.0001
        note_up = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=FlatCurveBEY(curve_date="2020-01-01", bey=0.02 + epsilon),
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            discount_margin=0,
        )
        note_down = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=FlatCurveBEY(curve_date="2020-01-01", bey=0.02 - epsilon),
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            discount_margin=0,
        )
        dv01_calculated = (note_down.get_price() - note_up.get_price()) / 2

        assert isinstance(dv01, float)
        assert abs(dv01 - dv01_calculated) < 1e-6, (
            "DV01 should equal calculated DV01 within margin of error."
        )

    def test_dv01_without_yield_or_price(self):
        note_without_settlement = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        with pytest.raises(
            ValueError,
            match="Unable to resolve yield to maturity.",
        ):
            note_without_settlement.dv01()

    # test dv01 with continuous compounding
    def test_dv01_continuous_compounding(self):
        flat_curve = FlatCurveLog(curve_date="2020-01-01", log_rate=0.02)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            cpn_freq=1,
            settlement_date="2020-01-01",
            price=100,
            current_ref_rate=0.02,
        )
        dv01 = note.dv01(yield_calculation_convention="CONTINUOUS")

        # Calculate DV01 manually
        epsilon = 0.0001
        note_up = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=FlatCurveLog(
                curve_date="2020-01-01", log_rate=0.02 + epsilon
            ),
            cpn_freq=1,
            settlement_date="2020-01-01",
            discount_margin=0,
            current_ref_rate=0.02,
        )
        note_up._price
        note_down = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=FlatCurveLog(
                curve_date="2020-01-01", log_rate=0.02 - epsilon
            ),
            cpn_freq=1,
            settlement_date="2020-01-01",
            discount_margin=0,
            current_ref_rate=0.02,
        )
        dv01_calculated = (note_down.get_price() - note_up.get_price()) / 2

        assert isinstance(dv01, float)
        assert abs(dv01 - dv01_calculated) < 1e-3, (
            "DV01 should equal calculated DV01 within margin of error with continuous compounding."
        )

    # test spread_dv01 equals dv01 of FixedRateBullet with same price and settlement_date
    def test_spread_dv01_equals_fixed_rate_bullet_dv01(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            quoted_margin=100,
            discount_margin=100,
        )
        bond = FixedRateBullet(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            cpn=3,
            cpn_freq=2,
            settlement_date="2020-01-01",
            price=note.get_price(),
        )

        spread_dv01 = note.spread_dv01()
        fixed_rate_bullet_dv01 = bond.dv01()

        assert isinstance(spread_dv01, float)
        assert abs(spread_dv01 - fixed_rate_bullet_dv01) < 1e-8, (
            "Spread DV01 should equal Fixed Rate Bullet DV01."
        )

    # test spread_dv01 raises ValueError when you can not calculate yield to maturity
    def test_spread_dv01_without_yield_or_price(self):
        note_without_settlement = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        with pytest.raises(
            ValueError,
            match="There is not enough information to calculate prices to calculate spread duration.",
        ):
            note_without_settlement.spread_dv01()

    # test _resolve_ytm_and_price with price but None discount_margin
    def test_resolve_ytm_and_price(self):
        settlement_date = self.note._resolve_settlement_date(None)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self.note._resolve_valuation_parameters(
            None,
            None,
            None,
            None,
        )
        ytm, price = self.note._resolve_ytm_and_price(
            settlement_date=settlement_date,
            discount_margin=None,
            price=101.5,
            ref_rate_curve=self.flat_curve,
            current_ref_rate=0.02,
            adjust_to_business_days=adjust_to_business_days,
            day_count_convention=day_count_convention,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
        )
        assert isinstance(ytm, float)
        assert isinstance(price, float)
        assert price == 101.5

        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            quoted_margin=0,
            cpn_freq=2,
            notional=100,
        )

        ytm, price = note._resolve_ytm_and_price(
            settlement_date=settlement_date,
            discount_margin=0,
            price=100,
            ref_rate_curve=self.flat_curve,
            current_ref_rate=0.02,
            adjust_to_business_days=adjust_to_business_days,
            day_count_convention=day_count_convention,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
        )
        assert price == 100
        # assert ytm is approximately equal to current_ref_rate + quoted_margin
        assert abs(ytm - (0.02 + 0)) < 1e-8

        ytm, price = note._resolve_ytm_and_price(
            settlement_date=settlement_date,
            discount_margin=0,
            price=100,
            ref_rate_curve=None,
            current_ref_rate=None,
            adjust_to_business_days=adjust_to_business_days,
            day_count_convention=day_count_convention,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
        )
        assert price == 100
        # assert ytm is None since there is no ref_rate_curve or current_ref_rate
        assert ytm is None

        # inconsistent inputs: both price and discount_margin provided
        with pytest.raises(
            ValueError,
            match="Bond price calculated by yield to maturity does not match the given bond price.",
        ):
            self.note._resolve_ytm_and_price(
                settlement_date=settlement_date,
                price=100,
                discount_margin=0,
                ref_rate_curve=self.flat_curve,
                current_ref_rate=0.02,
                adjust_to_business_days=adjust_to_business_days,
                day_count_convention=day_count_convention,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
            )

    def test_resolve_ytm_and_price_can_not_calculate(self):
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            quoted_margin=0,
            cpn_freq=2,
            notional=100,
        )
        settlement_date = note._resolve_settlement_date(None)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = note._resolve_valuation_parameters(
            None,
            None,
            None,
            None,
        )

        ytm, price = note._resolve_ytm_and_price(
            settlement_date=settlement_date,
            discount_margin=0,
            price=None,
            ref_rate_curve=None,
            current_ref_rate=None,
            adjust_to_business_days=adjust_to_business_days,
            day_count_convention=day_count_convention,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
        )
        # Nothing can be calculated
        assert price is None
        # assert ytm is None since there is no ref_rate_curve or current_ref_rate
        assert ytm is None

    def test_resolve_ytm_and_price_with_discount_margin_but_no_price(self):
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            quoted_margin=100,
            cpn_freq=2,
            notional=100,
        )
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.03)
        settlement_date = note._resolve_settlement_date(None)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = note._resolve_valuation_parameters(
            None,
            None,
            None,
            None,
        )

        ytm, price = note._resolve_ytm_and_price(
            settlement_date=settlement_date,
            discount_margin=100,
            price=None,
            ref_rate_curve=flat_curve,
            current_ref_rate=0.03,
            adjust_to_business_days=adjust_to_business_days,
            day_count_convention=day_count_convention,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
        )

    # test _resolve_ytm_and_price with negative price raises ValueError
    def test_resolve_ytm_and_price_negative_price(self):
        settlement_date = self.note._resolve_settlement_date(None)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self.note._resolve_valuation_parameters(
            None,
            None,
            None,
            None,
        )
        with pytest.raises(
            ValueError,
            match="Bond price cannot be negative.",
        ):
            self.note._resolve_ytm_and_price(
                settlement_date=settlement_date,
                price=-100,
                discount_margin=None,
                ref_rate_curve=self.flat_curve,
                current_ref_rate=0.02,
                adjust_to_business_days=adjust_to_business_days,
                day_count_convention=day_count_convention,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
            )

        with pytest.raises(
            ValueError,
            match="Bond price cannot be negative.",
        ):
            self.note._resolve_ytm_and_price(
                settlement_date=settlement_date,
                price=-100,
                discount_margin=0,
                ref_rate_curve=self.flat_curve,
                current_ref_rate=0.02,
                adjust_to_business_days=adjust_to_business_days,
                day_count_convention=day_count_convention,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
            )

    # test _resolve_discount_margin_and_price with price but None discount_margin
    def test_resolve_discount_margin_and_price_none_discount_margin(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.03)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            quoted_margin=100,
            cpn_freq=2,
            notional=100,
        )
        settlement_date = note._resolve_settlement_date(None)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = note._resolve_valuation_parameters(
            None,
            None,
            None,
            None,
        )
        discount_margin, price = note._resolve_discount_margin_and_price(
            settlement_date=settlement_date,
            discount_margin=None,
            price=100.0,
            ref_rate_curve=flat_curve,
            current_ref_rate=0.03,
            adjust_to_business_days=adjust_to_business_days,
            day_count_convention=day_count_convention,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
        )
        assert isinstance(discount_margin, float)
        assert isinstance(price, float)
        assert price == 100.0

    def test_resolve_discount_margin_and_price_negative_price(self):
        settlement_date = self.note._resolve_settlement_date(None)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self.note._resolve_valuation_parameters(
            None,
            None,
            None,
            None,
        )
        with pytest.raises(
            ValueError,
            match="Bond price cannot be negative.",
        ):
            self.note._resolve_discount_margin_and_price(
                settlement_date=settlement_date,
                price=-100,
                discount_margin=None,
                ref_rate_curve=self.flat_curve,
                current_ref_rate=0.02,
                adjust_to_business_days=adjust_to_business_days,
                day_count_convention=day_count_convention,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
            )

        with pytest.raises(
            ValueError,
            match="Bond price cannot be negative.",
        ):
            self.note._resolve_discount_margin_and_price(
                settlement_date=settlement_date,
                price=-100,
                discount_margin=0,
                ref_rate_curve=self.flat_curve,
                current_ref_rate=0.02,
                adjust_to_business_days=adjust_to_business_days,
                day_count_convention=day_count_convention,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
            )

    def test_resolve_discount_margin_and_price_with_both(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.03)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            quoted_margin=100,
            cpn_freq=2,
            notional=100,
        )
        settlement_date = note._resolve_settlement_date(None)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = note._resolve_valuation_parameters(
            None,
            None,
            None,
            None,
        )
        discount_margin, price = note._resolve_discount_margin_and_price(
            settlement_date=settlement_date,
            discount_margin=100.0,
            price=100.0,
            ref_rate_curve=flat_curve,
            current_ref_rate=0.03,
            adjust_to_business_days=adjust_to_business_days,
            day_count_convention=day_count_convention,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
        )
        assert isinstance(discount_margin, float)
        assert isinstance(price, float)
        assert price == 100.0

        # without ref_rate_curve it should return None for discount_margin
        discount_margin, price = note._resolve_discount_margin_and_price(
            settlement_date=settlement_date,
            discount_margin=100.0,
            price=100.0,
            ref_rate_curve=None,
            current_ref_rate=0.03,
            adjust_to_business_days=adjust_to_business_days,
            day_count_convention=day_count_convention,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
        )

        assert discount_margin is None
        assert isinstance(price, float)

        # inconsistent inputs: both price and discount_margin provided
        with pytest.raises(
            ValueError,
            match="Bond price calculated by discount margin does not match the given bond price.",
        ):
            note._resolve_discount_margin_and_price(
                settlement_date=settlement_date,
                price=100,
                discount_margin=0,
                ref_rate_curve=flat_curve,
                current_ref_rate=0.03,
                adjust_to_business_days=adjust_to_business_days,
                day_count_convention=day_count_convention,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
            )

    # test _resolve_discount_margin_and_price with discount margin but no price
    def test_resolve_discount_margin_and_price_with_discount_margin_no_price(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.03)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            quoted_margin=100,
            cpn_freq=2,
            notional=100,
        )
        settlement_date = note._resolve_settlement_date(None)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = note._resolve_valuation_parameters(
            None,
            None,
            None,
            None,
        )
        discount_margin, price = note._resolve_discount_margin_and_price(
            settlement_date=settlement_date,
            discount_margin=100.0,
            price=None,
            ref_rate_curve=flat_curve,
            current_ref_rate=0.03,
            adjust_to_business_days=adjust_to_business_days,
            day_count_convention=day_count_convention,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
        )
        assert isinstance(discount_margin, float)
        assert isinstance(price, float)

    # test _resolve_discount_margin_and_price where nothing can be calculated
    def test_resolve_discount_margin_and_price_nothing_can_be_calculated(self):
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            quoted_margin=100,
            cpn_freq=2,
            notional=100,
        )
        settlement_date = note._resolve_settlement_date(None)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = note._resolve_valuation_parameters(
            None,
            None,
            None,
            None,
        )
        discount_margin, price = note._resolve_discount_margin_and_price(
            settlement_date=settlement_date,
            discount_margin=None,
            price=None,
            ref_rate_curve=None,
            current_ref_rate=None,
            adjust_to_business_days=adjust_to_business_days,
            day_count_convention=day_count_convention,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
        )
        assert discount_margin is None
        assert price is None

    # test macaulay_duration
    def test_macaulay_duration(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            discount_margin=0,
        )

        macaulay_duration = note.macaulay_duration()

        assert isinstance(macaulay_duration, float)
        # macaulay_duration equals half a year within margin of error
        assert abs(macaulay_duration - 0.5) < 1e-8, (
            "Macaulay duration should equal half a year."
        )

        # test with continuous
        macaulay_duration_continuous = note.macaulay_duration(
            yield_calculation_convention="CONTINUOUS"
        )
        t = next(iter(note.make_expected_cash_flow())) - note.get_settlement_date()
        t = t.days / 365

        assert isinstance(macaulay_duration_continuous, float)
        assert abs(macaulay_duration_continuous - t) < 1e-8, (
            "Macaulay duration with continuous compounding should equal days/365."
        )

    # test macaulay_duration raises ValueError when you can not calculate yield to maturity
    def test_macaulay_duration_without_yield_or_price(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        note_without_settlement = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        with pytest.raises(
            ValueError,
            match="Unable to resolve yield to maturity.",
        ):
            note_without_settlement.macaulay_duration()

    # test convexity
    def test_convexity(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            discount_margin=0,
        )

        convexity = note.convexity()
        assert isinstance(convexity, float)
        assert convexity > 0, "Convexity should be positive for normal bonds."

        # test convexity with continuous
        convexity_continuous = note.convexity(yield_calculation_convention="CONTINUOUS")
        assert isinstance(convexity_continuous, float)
        assert convexity_continuous > 0, (
            "Convexity should be positive for normal bonds with continuous compounding."
        )

    def test_convexity_without_yield_or_price(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        note_without_settlement = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        with pytest.raises(
            ValueError,
            match="Unable to resolve yield to maturity.",
        ):
            note_without_settlement.convexity()

    # test to_dataframe
    def test_to_dataframe(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            discount_margin=0,
        )

        df = note.to_dataframe(price=100)

        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "Expected Cash Flows" in df.columns
        # amortization should equal notional
        assert df["Amortization"].sum() == note.notional
        # values with positive coupon should equal quoted margin plus 2%
        expected_coupon = (
            note.notional * (0.02 + note.quoted_margin / 10000) / note.cpn_freq
        )
        coupon_flows = df[df["Expected Coupon"] > 0]["Expected Coupon"]
        assert (coupon_flows == expected_coupon).all(), (
            "Coupon flows should equal expected coupon amount."
        )

    # test to_dataframe raises errors when there is no price
    def test_to_dataframe_raises_error_without_ref_rate_curve(self):
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            quoted_margin=50,
            cpn_freq=2,
            notional=1000,
        )
        with pytest.raises(
            ValueError,
            match="Either ref_rate_curve or self.ref_rate_curve must be provided.",
        ):
            note.to_dataframe()

    # test to_dataframe with no price nor discount_margin
    def test_to_dataframe_without_price_or_discount_margin(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            cpn_freq=2,
            current_ref_rate=0.02,
            notional=1000,
        )
        df = note.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "Expected Cash Flows" in df.columns
        # amortization should equal notional
        assert df["Amortization"].sum() == note.notional
        # values with positive coupon should equal quoted margin plus 2%
        expected_coupon = (
            note.notional * (0.02 + note.quoted_margin / 10000) / note.cpn_freq
        )
        coupon_flows = df[df["Expected Coupon"] > 0]["Expected Coupon"]
        assert (coupon_flows == expected_coupon).all(), (
            "Coupon flows should equal expected coupon amount."
        )

    # test plot_cash_flows
    @pytest.mark.filterwarnings("ignore::UserWarning")
    def test_plot_cash_flows(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            discount_margin=0,
        )

        fig = note.plot_cash_flows()

        assert fig is not None

    # test z_spread equals discount_margin when both calculated
    def test_z_spread_equals_discount_margin(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            quoted_margin=100,
            discount_margin=100,
        )

        z_spread = note.z_spread(
            tol=None,
            max_iter=None,
        )

        assert isinstance(z_spread, float)
        assert abs(z_spread * 10000 - note._discount_margin) < 1e-8, (
            "Z-spread should equal discount margin when both are calculated."
        )

    # test z_spread raises ValueError when you cannot calculate discount_margin
    def test_z_spread_without_discount_margin(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            quoted_margin=100,
        )
        with pytest.raises(
            ValueError,
            match="Bond price must be set to calculate spread.",
        ):
            note.z_spread()

        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            quoted_margin=100,
        )
        with pytest.raises(
            ValueError,
            match="Either ref_rate_curve or self.ref_rate_curve must be provided.",
        ):
            note.z_spread(tol=1e-6, max_iter=100, price=100)

        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            quoted_margin=100,
            price=100,
        )
        note.z_spread(ref_rate_curve=flat_curve)

    # test i_spread equals quoted_margin when both calculated
    def test_i_spread_equals_quoted_margin(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            quoted_margin=150,
            discount_margin=150,
        )

        i_spread = note.i_spread(benchmark_curve=flat_curve)

        assert isinstance(i_spread, float)
        assert abs(i_spread - note.quoted_margin) < 1e-8, (
            "I-spread should equal quoted margin when both are calculated."
        )

    # test g_spread equals quoted_margin when both calculated
    def test_g_spread_equals_quoted_margin(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            quoted_margin=200,
            discount_margin=200,
        )

        g_spread = note.g_spread(benchmark_curve=flat_curve)

        assert isinstance(g_spread, float)
        assert abs(g_spread - note.quoted_margin) < 1e-8, (
            "G-spread should equal quoted margin when both are calculated."
        )

        g_spread = note.g_spread(benchmark_ytm=0.02)

        assert isinstance(g_spread, float)
        assert abs(g_spread - note.quoted_margin) < 1e-8, (
            "G-spread should equal quoted margin when both are calculated."
        )

    # test g_spread raises ValueError when neither benchmark_ytm or benchmark_curve were not provided
    def test_g_spread_without_benchmark(self):
        flat_curve = FlatCurveBEY(curve_date="2020-01-01", bey=0.02)
        note = FloatingRateNote(
            issue_dt="2020-01-01",
            maturity="2025-01-01",
            ref_rate_curve=flat_curve,
            cpn_freq=2,
            current_ref_rate=0.02,
            settlement_date="2020-01-01",
            quoted_margin=200,
        )
        with pytest.raises(
            ValueError,
            match="Either benchmark_ytm or benchmark_curve must be provided.",
        ):
            note.g_spread()
