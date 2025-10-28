import pytest
import pandas as pd
from pyfian.fixed_income.floating_rate_note import FloatingRateNote
from pyfian.yield_curves.flat_curve import FlatCurveBEY
from pyfian.yield_curves.zero_coupon_curve import ZeroCouponCurve


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
        note_with_discount_and_price.set_discount_margin(0.01)
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
