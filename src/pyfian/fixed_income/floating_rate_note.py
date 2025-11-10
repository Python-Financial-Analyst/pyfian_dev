"""
floating_rate_note.py

Module for fixed income floating rate note analytics, including FloatingRateNote class for payment flows,
valuation, and yield calculations.
"""

from collections import defaultdict
from typing import Optional, Union
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta  # type: ignore
from scipy import optimize  # type: ignore

from pyfian.fixed_income.base_fixed_income import BaseFixedIncomeInstrument
from pyfian.time_value import rate_conversions as rc
from pyfian.time_value.irr import xirr_base
from pyfian.time_value.rate_conversions import get_time_adjustment
from pyfian.utils.day_count import DayCountBase, get_day_count_convention
from pyfian.yield_curves.base_curve import YieldCurveBase
from pyfian.yield_curves.flat_curve import FlatCurveBEY


class FloatingRateNote(BaseFixedIncomeInstrument):
    _yield_to_maturity: Optional[float] = None

    def __init__(
        self,
        issue_dt: Union[str, pd.Timestamp],
        maturity: Union[str, pd.Timestamp],
        ref_rate_curve: Optional[YieldCurveBase] = None,
        current_ref_rate: Optional[float] = None,
        quoted_margin: float = 0.0,
        cpn_freq: int = 1,
        notional: float = 100,
        settlement_convention_t_plus: int = 1,
        record_date_t_minus: int = 1,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        discount_margin: Optional[float] = None,
        price: Optional[float] = None,
        adjust_to_business_days: bool = False,
        day_count_convention: str | DayCountBase = "actual/actual-Bond",
        following_coupons_day_count: str | DayCountBase = "30/360",
        yield_calculation_convention: str = "BEY",
    ) -> None:
        self.issue_dt: pd.Timestamp = pd.to_datetime(issue_dt)
        self.maturity: pd.Timestamp = pd.to_datetime(maturity)
        self.ref_rate_curve = ref_rate_curve
        self.current_ref_rate = current_ref_rate
        self.quoted_margin = quoted_margin / 10000  # Convert from bps to decimal
        self.cpn_freq = cpn_freq
        self.notional = notional
        self.settlement_convention_t_plus = settlement_convention_t_plus
        self.record_date_t_minus = record_date_t_minus
        if not isinstance(day_count_convention, (str, DayCountBase)):
            raise TypeError(
                "day_count_convention must be either a string or a DayCountBase instance."
            )
        self.day_count_convention: DayCountBase = (
            get_day_count_convention(day_count_convention)
            if isinstance(day_count_convention, str)
            else day_count_convention
        )
        self.adjust_to_business_days: bool = adjust_to_business_days
        self._validate_following_coupons_day_count(following_coupons_day_count)
        self.following_coupons_day_count: DayCountBase = (
            get_day_count_convention(following_coupons_day_count)
            if isinstance(following_coupons_day_count, str)
            else following_coupons_day_count
        )
        self.yield_calculation_convention: str = (
            self._validate_yield_calculation_convention(yield_calculation_convention)
        )
        dict_payments, dict_spreads, dict_amortization = self.make_payment_flow()
        self.payment_flow: dict[pd.Timestamp, float] = dict_payments
        self.coupon_flow: dict[pd.Timestamp, float] = dict_spreads
        self.spread_flow: dict[pd.Timestamp, float] = dict_spreads
        self.amortization_flow: dict[pd.Timestamp, float] = dict_amortization
        self._settlement_date: Optional[pd.Timestamp] = None
        self._validate_price(price=price)
        if settlement_date is not None:
            self.set_settlement_date(
                settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                day_count_convention=day_count_convention,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
            )

        if self._settlement_date is not None and ref_rate_curve is not None:
            if self._settlement_date != ref_rate_curve.curve_date:
                raise ValueError(
                    "Settlement date must be the same as the curve date of the reference rate curve."
                )

        if discount_margin is not None:
            if self._settlement_date is None:
                raise ValueError(
                    "Settlement date must be set if discount margin is set."
                )
            self.set_discount_margin(
                discount_margin,
                settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                day_count_convention=day_count_convention,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                ref_rate_curve=ref_rate_curve,
                current_ref_rate=current_ref_rate,
            )
        else:
            self._discount_margin: Optional[float] = None

        if price is not None:
            if self._settlement_date is None:
                raise ValueError("Settlement date must be set if price is set.")
            self.set_price(
                price,
                settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
            )
        elif discount_margin is None:
            self._price: Optional[float] = None

        calculate, ref_rate_curve, current_ref_rate = self._should_calculate(
            settlement_date, ref_rate_curve, current_ref_rate
        )
        if calculate and self._price:
            self._yield_to_maturity = self.yield_to_maturity(
                settlement_date=self._settlement_date,
                price=self._price,
                ref_rate_curve=ref_rate_curve,
                current_ref_rate=current_ref_rate,
            )
        else:
            self._yield_to_maturity = None

    def get_yield_to_maturity(self) -> Optional[float]:
        """
        Get the current yield to maturity of the bond.

        Returns
        -------
        float, optional
            The current yield to maturity as a decimal, or None if not set.
        """
        return self._yield_to_maturity

    def _should_calculate(self, settlement_date, ref_rate_curve, current_ref_rate):
        """
        Helper to determine if calculation should proceed based on settlement_date, ref_rate_curve, and current_ref_rate.
        Returns (calculate: bool, ref_rate_curve, current_ref_rate)
        """
        calculate = True

        if settlement_date is None:
            settlement_date = self._settlement_date
        if settlement_date is None:
            calculate = False
        if calculate and ref_rate_curve is None:
            if self.ref_rate_curve is None:
                calculate = False
            else:
                ref_rate_curve = self.ref_rate_curve
        if calculate and (pd.Timestamp(settlement_date) != ref_rate_curve.curve_date):
            calculate = False
        if calculate and current_ref_rate is None:
            if self.current_ref_rate is None:
                if (
                    self.issue_dt == pd.Timestamp(settlement_date)
                    or pd.Timestamp(settlement_date) in self.spread_flow
                ):
                    calculate = True
                else:
                    calculate = False
            else:
                current_ref_rate = self.current_ref_rate
        return calculate, ref_rate_curve, current_ref_rate

    def get_discount_margin(self) -> Optional[float]:
        """
        Get the current discount margin of the bond.

        Returns
        -------
        float, optional
            The current discount margin in basis points, or None if not set.
        """
        return self._discount_margin

    def set_settlement_date(
        self,
        settlement_date: Optional[Union[str, pd.Timestamp]],
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> pd.Timestamp:
        """
        Set the default settlement date for the bond.

        Parameters
        ----------
        settlement_date : Union[str, pd.Timestamp], optional
            The settlement date to set.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.

        Returns
        -------
        pd.Timestamp
            The updated settlement date.

        Raises
        ------
        ValueError
            If the settlement date is not set when the bond price is set.
        If the settlement date is changed, resets the bond price and yield to maturity if reset_yield_to_maturity is True.
        """
        old_settlement_date = self._settlement_date
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        if settlement_date is not None:
            settlement_date = pd.to_datetime(settlement_date)
            if settlement_date < self.issue_dt:
                raise ValueError("Settlement date cannot be before issue date.")
            if (
                old_settlement_date is not None
                and settlement_date != old_settlement_date
            ):
                # If the settlement date is changed, reset related attributes
                self._price = None
                self._discount_margin = None

            self._settlement_date = pd.to_datetime(settlement_date)
        else:
            self._settlement_date = None
            # If no settlement date is set, reset bond price and discount margin
            self._price = None
            self._discount_margin = None
        return self._settlement_date

    def set_discount_margin(
        self,
        discount_margin: Optional[float],
        settlement_date: Optional[Union[str, pd.Timestamp, None]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
        current_ref_rate: Optional[float] = None,
    ) -> None:
        """
        Set the default discount_margin for the bond. Updates bond price accordingly if reference rate curve is provided.

        Parameters
        ----------
        discount_margin : float, optional
            The discount margin to set in basis points.
        settlement_date : Union[str, pd.Timestamp], optional
            The settlement date to set.
        adjust_to_business_days : bool, optional
            Whether to adjust the settlement date to the next business day.
        day_count_convention : str or DayCountBase, optional
            The day count convention to use.
        following_coupons_day_count : str or DayCountBase, optional
            The following coupons day count convention to use.
        yield_calculation_convention : str, optional
            The yield calculation convention to use.
        ref_rate_curve : YieldCurveBase, optional
            The reference rate curve to use.
        current_ref_rate : float, optional
            The current reference rate to use.

        Raises
        ------
        ValueError
            If the settlement date is not set when the yield to maturity is set.

        If the discount margin is set, it will also update the bond price based on the discount margin.
        """
        self._discount_margin = discount_margin
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        if settlement_date is not None:
            settlement_date = self.set_settlement_date(
                settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                day_count_convention=day_count_convention,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
            )
        # Since discount_margin is set, update bond price
        if discount_margin is not None:
            settlement_date = self._settlement_date
            if settlement_date is None:
                raise ValueError(
                    "Settlement date must be set since there is no default settlement_date for the bond."
                )

            calculate, ref_rate_curve, current_ref_rate = self._should_calculate(
                settlement_date, ref_rate_curve, current_ref_rate
            )
            if calculate:
                self._price = self._price_from_discount_margin_and_clean_parameters(
                    discount_margin=discount_margin,
                    settlement_date=settlement_date,
                    adjust_to_business_days=adjust_to_business_days,
                    following_coupons_day_count=following_coupons_day_count,
                    yield_calculation_convention=yield_calculation_convention,
                    day_count_convention=day_count_convention,
                    ref_rate_curve=ref_rate_curve,
                    current_ref_rate=current_ref_rate,
                )
            else:
                self._price = None

        else:
            # If no discount margin is set, reset bond price and discount margin
            self._price = None
            self._discount_margin = None

    def set_price(
        self,
        price: Optional[float],
        settlement_date: Optional[Union[str, pd.Timestamp, None]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
        current_ref_rate: Optional[float] = None,
    ) -> None:
        """
        Set the default discount margin for the bond. Updates bond price accordingly.

        Parameters
        ----------
        discount_margin : float, optional
            The discount margin to set in basis points.
        settlement_date : Union[str, pd.Timestamp], optional
            The settlement date to set.
        adjust_to_business_days : bool, optional
            Whether to adjust the settlement date to the next business day.
        day_count_convention : str or DayCountBase, optional
            The day count convention to use.
        following_coupons_day_count : str or DayCountBase, optional
            The following coupons day count convention to use.
        yield_calculation_convention : str, optional
            The yield calculation convention to use.
        ref_rate_curve : YieldCurveBase, optional
            The reference rate curve to use.
        current_ref_rate : float, optional
            The current reference rate to use.

        Raises
        ------
        ValueError
            If the settlement date is not set when the discount margin is set.

        If the discount margin is set, it will also update the bond price based on the discount margin.
        """
        self._validate_price(price=price)
        self._price = price
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        if settlement_date is not None:
            settlement_date = self.set_settlement_date(
                settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                day_count_convention=day_count_convention,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
            )
        # Since bond price is set, update discount margin
        if price is not None:
            settlement_date = self._settlement_date
            if settlement_date is None:
                raise ValueError(
                    "Settlement date must be set since there is no default settlement_date for the bond."
                )
            calculate, ref_rate_curve, current_ref_rate = self._should_calculate(
                settlement_date, ref_rate_curve, current_ref_rate
            )
            if calculate:
                self._discount_margin = (
                    self._get_spread_from_price(
                        price=price,
                        settlement_date=settlement_date,
                        ref_rate_curve=ref_rate_curve,
                        current_ref_rate=current_ref_rate,
                    )
                    * 10000
                )
            else:
                self._discount_margin = None
        else:
            # If no discount margin is set, reset bond price and discount margin
            self._price = None
            self._discount_margin = None

    def _price_from_discount_margin_and_clean_parameters(
        self,
        discount_margin: float,
        settlement_date: Optional[Union[str, pd.Timestamp]],
        adjust_to_business_days: bool,
        following_coupons_day_count: DayCountBase,
        yield_calculation_convention: str,
        day_count_convention: DayCountBase,
        ref_rate_curve: YieldCurveBase,
        current_ref_rate: Optional[float] = None,
        curve_delta: float = 0.0,
    ) -> float:
        dated_payment_flow = self.make_expected_cash_flow(
            price=None,
            settlement_date=settlement_date,
            ref_rate_curve=ref_rate_curve,
            current_ref_rate=current_ref_rate,
            curve_delta=curve_delta,
        )

        # Calculate present value of each cash flow
        pv = {
            d: ref_rate_curve.discount_date(
                d, spread=discount_margin / 10000 + curve_delta
            )
            * value
            for d, value in dated_payment_flow.items()
        }
        return sum(pv.values())

    def _validate_yield_calculation_convention(
        self, yield_calculation_convention: str
    ) -> str:
        valid_conventions_dict = {
            "bey": "BEY",
            "annual": "Annual",
            "continuous": "Continuous",
            "bey-q": "BEY-Q",
            "bey-m": "BEY-M",
            "bey-s": "BEY",
        }
        if yield_calculation_convention.lower() not in valid_conventions_dict:
            raise ValueError(
                f"Unsupported yield calculation convention: {yield_calculation_convention}. "
                f"Supported conventions: {valid_conventions_dict}"
            )
        return valid_conventions_dict[yield_calculation_convention.lower()]

    def _validate_following_coupons_day_count(
        self, following_coupons_day_count: str | DayCountBase
    ) -> DayCountBase:
        """
        Validate the following coupons day count convention.
        Raises ValueError if the convention is not supported.
        """
        valid_conventions = ["30/360", "30e/360", "actual/360", "actual/365", "30/365"]
        if isinstance(following_coupons_day_count, DayCountBase):
            following_coupons_day_count_name = following_coupons_day_count.name
        else:
            following_coupons_day_count_name = following_coupons_day_count
            following_coupons_day_count = get_day_count_convention(
                following_coupons_day_count
            )
        if following_coupons_day_count_name not in valid_conventions:
            raise ValueError(
                f"Unsupported following coupons day count convention: {following_coupons_day_count}. "
                f"Supported conventions: {valid_conventions}"
            )
        return following_coupons_day_count

    def make_payment_flow(
        self,
    ) -> tuple[
        dict[pd.Timestamp, float], dict[pd.Timestamp, float], dict[pd.Timestamp, float]
    ]:
        """
        Generate the payment flow (cash flows) for the bond.
        Returns a tuple of dictionaries:

        * dict_payments: Payment dates as keys and cash flow amounts as values.
        * dict_spreads: Spread payment dates as keys and spread amounts as values.
        * dict_amortization: Amortization payment dates as keys and amortization amounts as values.

        Returns
        -------
        dict_payments : dict
            Dictionary with payment dates as keys and cash flow amounts as values.
        dict_spreads : dict
            Dictionary with spread payment dates as keys and spread amounts as values.
        dict_amortization : dict
            Dictionary with amortization payment dates as keys and amortization amounts as values.

        Raises
        ------
        ValueError
            If the bond is not properly initialized.

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', quoted_margin=0, cpn_freq=2, notional=1000)
        >>> bond.make_payment_flow() # doctest: +SKIP
        {Timestamp('2025-01-01 00:00:00'): 1050.0, Timestamp('2024-01-01 00:00:00'): 50.0, ...}
        """
        issue_dt, maturity, spread, cpn_freq, notional = (
            self.issue_dt,
            self.maturity,
            self.quoted_margin,
            self.cpn_freq,
            self.notional,
        )
        dict_payments = {}
        dict_spreads = {}
        dict_amortization = {}

        # Final payment: principal + last spread
        if cpn_freq == 0:
            last_spread = 0.0
        else:
            last_spread = (spread) / cpn_freq * notional

        dict_amortization[maturity] = notional
        dict_payments[maturity] = notional + last_spread

        dict_spreads[maturity] = last_spread
        if cpn_freq == 0:
            next_date_processed = maturity
        else:
            next_date_processed = maturity - relativedelta(months=12 // cpn_freq)

        for i in range(2, ((maturity - issue_dt) / 365).days * (cpn_freq) + 3):
            if (next_date_processed - issue_dt).days < (365 * 0.99) // (
                cpn_freq if cpn_freq > 0 else 1
            ):
                break
            coupon_spread = (spread) / (cpn_freq if cpn_freq > 0 else 1) * notional
            dict_payments[next_date_processed] = coupon_spread
            dict_spreads[next_date_processed] = coupon_spread
            dict_amortization[next_date_processed] = (
                0.0
                if next_date_processed not in dict_amortization
                else dict_amortization[next_date_processed]
            )
            next_date_processed = maturity - relativedelta(
                months=12 // (cpn_freq if cpn_freq > 0 else 1) * i
            )

        # Sort the payment dates
        dict_payments = dict(sorted(dict_payments.items()))
        dict_spreads = dict(sorted(dict_spreads.items()))
        dict_amortization = dict(sorted(dict_amortization.items()))
        return dict_payments, dict_spreads, dict_amortization

    def _calculate_time_to_payments(
        self,
        settlement_date,
        price,
        adjust_to_business_days,
        following_coupons_day_count,
        yield_calculation_convention,
        day_count_convention,
        payment_flow: Optional[dict[pd.Timestamp, float]] = None,
    ) -> dict[float, float]:
        """Calculate the time to each payment from the settlement date."""
        if payment_flow is None:
            payment_flow = self.payment_flow
        flows = self._filter_payment_flow(
            settlement_date,
            price,
            payment_flow=payment_flow,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        start = self.previous_coupon_date(
            settlement_date=settlement_date,
        )
        if start is None:
            start = self.issue_dt

        time_to_payments_keys = sorted(flows.keys())
        first_non_negative_key = next(
            (key for key in time_to_payments_keys if key > time_to_payments_keys[0]),
            None,
        )

        time_to_first_non_negative_key = day_count_convention.fraction_period_adjusted(
            start=start,
            current=settlement_date,
            end=first_non_negative_key,
            periods_per_year=self.cpn_freq,
        )

        times: defaultdict[float, float] = defaultdict(float)

        cpn_freq = max(1, self.cpn_freq)  # Avoid division by zero

        for key in time_to_payments_keys:
            if key <= settlement_date:
                times_key = 0.0
            else:
                times_key = (
                    following_coupons_day_count.fraction(
                        start=start,
                        current=key,
                    )
                    - time_to_first_non_negative_key / cpn_freq
                )
            times[times_key] += flows[key]

        return dict(times)

    def make_expected_cash_flow(
        self,
        price: Optional[float] = None,
        current_ref_rate: Optional[float] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        curve_delta: float = 0.0,
        #    adjust_to_business_days: Optional[bool] = None,
        #    day_count_convention: Optional[str | DayCountBase] = None,
        #    following_coupons_day_count: Optional[str | DayCountBase] = None,
        #    yield_calculation_convention: Optional[str] = None,
    ) -> dict[pd.Timestamp, float]:
        """
        Generate the expected cash flow for the bond from the settlement date onwards.
        Uses the reference rate curve to estimate future reference rates for cash flow calculations.

        Parameters
        ----------
        price : float, optional
            Price of the bond. If provided, includes bond price as a negative cash flow at settlement date.
        current_ref_rate : float, optional
            Current reference rate as a decimal. If not provided, will use self.current_ref_rate.
        ref_rate_curve : YieldCurveBase, optional
            Reference rate curve to use for estimating future rates. If not provided, will use self.ref_rate_curve.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        curve_delta : float, optional
            Adjustment to apply to the reference rate curve for sensitivity analysis. Defaults to 0.0.
            Does not modify the current reference rate if it is inferred from the curve.

        Returns
        -------
        expected_coupon_flow : dict
            Dictionary with coupon payment dates as keys and cash flow amounts as values.

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', ref_rate_curve, current_ref_rate=0.02, quoted_margin=50, cpn_freq=2)
        >>> bond.make_real_payment_flow(settlement_date='2022-01-01') # doctest: +SKIP
        {Timestamp('2022-07-01 00:00:00'): 1.25, Timestamp('2023-01-01 00:00:00'): 1.25, ...}
        """
        settlement_date = self._resolve_settlement_date(settlement_date)

        # One reference curve must be provided
        if ref_rate_curve is None:
            if self.ref_rate_curve is None:
                raise ValueError(
                    "Either ref_rate_curve or self.ref_rate_curve must be provided."
                )
            else:
                ref_rate_curve = self.ref_rate_curve

        # settlement date must be the same as the curve date
        if settlement_date != ref_rate_curve.curve_date:
            raise ValueError(
                "Settlement date must be the same as the curve date of the reference rate curve."
            )

        expected_cash_flow = self.spread_flow.copy()

        # filter only expected payments after settlement date
        expected_cash_flow = {
            date: spread
            for date, spread in expected_cash_flow.items()
            if date > settlement_date
        }

        if current_ref_rate is None:
            if self.cpn_freq == 0:
                current_ref_rate = 0.0
            elif self.current_ref_rate is None:
                # extract the current reference rate from the curve at the settlement date
                if (
                    self.issue_dt == settlement_date
                    or settlement_date in self.spread_flow
                ):
                    current_ref_rate = ref_rate_curve.forward_dates(
                        start_date=settlement_date,
                        end_date=next(iter(expected_cash_flow)),
                    )
                    current_ref_rate = rc.convert_yield(
                        current_ref_rate,
                        from_convention=ref_rate_curve.yield_calculation_convention,
                        to_convention="Annual",
                    )
                    current_ref_rate = rc.effective_to_nominal_periods(
                        current_ref_rate, periods_per_year=self.cpn_freq
                    )
                else:
                    raise ValueError(
                        "Either current_ref_rate or self.current_ref_rate must be provided if issue_dt is not equal to settlement_date."
                    )
            else:
                current_ref_rate = self.current_ref_rate

        last_date = settlement_date
        # Adjust expected cash flow using reference rate curve and current reference rate
        for i, (date, spread) in enumerate(expected_cash_flow.items()):
            if i == 0:
                expected_cash_flow[date] = (
                    spread + (current_ref_rate / self.cpn_freq * self.notional)
                    if self.cpn_freq > 0
                    else 0
                )
            else:
                # Adjust the spread using the forward rate and current reference rate
                new_current_ref_rate = ref_rate_curve.forward_dates(
                    last_date, date, spread_start=curve_delta, spread_end=curve_delta
                )
                new_current_ref_rate = rc.convert_yield(
                    new_current_ref_rate,
                    from_convention=ref_rate_curve.yield_calculation_convention,
                    to_convention=self.yield_calculation_convention,
                )
                expected_cash_flow[date] = (
                    spread + (new_current_ref_rate / self.cpn_freq * self.notional)
                    if self.cpn_freq > 0
                    else 0
                )
            last_date = date

        if price is not None:
            expected_cash_flow[
                settlement_date
            ] = -price  # Initial cash flow (negative for purchase)

        amortization_flow = {
            date: value
            for date, value in self.amortization_flow.items()
            if date > settlement_date and value != 0
        }
        for dt, amt in amortization_flow.items():
            if dt in expected_cash_flow:
                expected_cash_flow[dt] += amt
            else:
                expected_cash_flow[dt] = amt  # pragma: no cover

        expected_cash_flow = dict(sorted(expected_cash_flow.items()))

        return expected_cash_flow

    def value_with_curve(
        self,
        curve: YieldCurveBase,
        spread: float = 0,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        price: Optional[float] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
        current_ref_rate: Optional[float] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
    ) -> tuple[float, dict[float, float]]:
        """
        Value the bond using a discount curve.

        Calculates the present value of the bond's cash flows using the provided discount curve.

        Returns the total present value and a dictionary of present values for each payment.

        If a bond price is provided, it is included as a negative cash flow, and the
        present value would be equivalent to a Net Present Value (NPV) calculation, useful for
        comparing the bond's market price against its theoretical value based on the discount curve.

        The curve should have a method `discount_date(d)` that returns the discount factor for a given date `d`.

        The discount factor is typically calculated as:

        .. math::
            discount_date(d) = \\frac{1}{(1 + r(d))^t}

        where:

        - :math:`r(d)` is the discount rate at date :math:`d`.
        - :math:`t` is the time in years from the settlement date to date :math:`d`.

        The discount factor brings the future value back to the present. Using this discount factor, we can calculate the present value of future cash flows by discounting them back to the settlement date.

        For a set of cash flows :math:`C(t)` at times :math:`t`, the present value (PV) is calculated as:

        .. math::
            PV = \\sum_{i}^{N} C(d_i) * discount_date(d_i)

        for each (:math:`d_i`, :math:`C(d_i)`) cash flow, where :math:`i = 1, ..., N`

        where:

        - :math:`PV` is the present value of the cash flows
        - :math:`C(d)` is the cash flow at date :math:`d`
        - :math:`N` is the total number of cash flows
        - :math:`r(d)` is the discount rate at date :math:`d`.

        The discount rate for a cash flow at date :math:`d` is obtained from the discount curve using `curve.discount_date(d)`.

        This can be used to optimize the yield curve fitting process.

        Parameters
        ----------
        curve : object
            Discount curve object with a discount_date(d) method.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        price : float, optional
            If provided, includes bond price as a negative cash flow.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.
        current_ref_rate : float, optional
            Current reference rate. Defaults to value of self.current_ref_rate.
        ref_rate_curve : YieldCurveBase, optional
            Reference rate curve. Defaults to value of self.ref_rate_curve.

        Returns
        -------
        total_value : float
            Present value of the bond.
        pv : dict
            Dictionary of present values for each payment.

        Examples
        --------
        >>> from pyfian.yield_curves.flat_curve import FlatCurveBEY
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', quoted_margin=0, cpn_freq=2)
        >>> bond.value_with_curve(FlatCurveBEY(curve_date="2020-01-01", bey=0.05)) # doctest: +SKIP
        (value, {t1: pv1, t2: pv2, ...})
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        date_of_payments = self.make_expected_cash_flow(
            price=price,
            settlement_date=settlement_date,
            ref_rate_curve=ref_rate_curve,
            current_ref_rate=current_ref_rate,
        )

        # Calculate present value of each cash flow
        pv = {
            d: curve.discount_date(d, spread) * value
            for d, value in date_of_payments.items()
        }
        return sum(pv.values()), pv

    def required_margin(
        self,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
        current_ref_rate: Optional[float] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
        tol: Optional[float] = 1e-6,
        max_iter: Optional[int] = 100,
    ):
        """
        Estimate the spread over the reference rate curve using the xirr function from pyfian.time_value.irr.

        The spread is the difference between the yield of the bond and the yield of the reference rate curve at the same maturity.

        It is the additional yield that investors require to hold the bond instead of a risk-free reference bond.

        The spread is calculated by solving the equation:

        .. math::
            P = \\sum_{t=1}^{T} \\frac{C_t}{(1 + YTM + Spread)^{(t+1)}}

        where:

        - :math:`P` is the price of the bond
        - :math:`C_t` is the cash flow at time :math:`t`, where :math:`t` is the time in years from the settlement date
        - :math:`YTM` is the yield to maturity
        - :math:`T` is the total number of periods

        The times to payments are calculated from the settlement date to each payment date and need not be integer values.

        Parameters
        ----------
        price : float, optional
            Price of the bond. If not provided, will use self._price.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.
        current_ref_rate : float, optional
            Current reference rate as a decimal. If not provided, will use self.current_ref_rate.
        ref_rate_curve : YieldCurveBase, optional
            Reference rate curve to use for estimating future rates. If not provided, will use self.ref_rate_curve.
        tol : float, optional
            Tolerance for convergence (default is 1e-6).
        max_iter : int, optional
            Maximum number of iterations (default is 100).

        Returns
        -------
        discount_margin : float
            Estimated discount margin in basis points.

        Raises
        ------
        ValueError
            If bond price is not set or YTM calculation does not converge.

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.required_margin(price=95)
        np.float64(0.06100197251858131)
        """
        return self.discount_margin(
            price,
            settlement_date,
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
            current_ref_rate,
            ref_rate_curve,
            tol,
            max_iter,
        )

    def discount_margin(
        self,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
        current_ref_rate: Optional[float] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
        tol: Optional[float] = 1e-6,
        max_iter: Optional[int] = 100,
    ) -> float:
        """
        Estimate the spread over the reference rate curve using the xirr function from pyfian.time_value.irr.

        The spread is the difference between the yield of the bond and the yield of the reference rate curve at the same maturity.

        It is the additional yield that investors require to hold the bond instead of a risk-free reference bond.

        The spread is calculated by solving the equation:

        .. math::
            P = \\sum_{t=1}^{T} \\frac{C_t}{(1 + YTM + Spread)^{(t+1)}}

        where:

        - :math:`P` is the price of the bond
        - :math:`C_t` is the cash flow at time :math:`t`, where :math:`t` is the time in years from the settlement date
        - :math:`YTM` is the yield to maturity
        - :math:`T` is the total number of periods

        The times to payments are calculated from the settlement date to each payment date and need not be integer values.

        Parameters
        ----------
        price : float, optional
            Price of the bond. If not provided, will use self._price.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.
        current_ref_rate : float, optional
            Current reference rate as a decimal. If not provided, will use self.current_ref_rate.
        ref_rate_curve : YieldCurveBase, optional
            Reference rate curve to use for estimating future rates. If not provided, will use self.ref_rate_curve.
        tol : float, optional
            Tolerance for convergence (default is 1e-6).
        max_iter : int, optional
            Maximum number of iterations (default is 100).

        Returns
        -------
        discount_margin : float
            Estimated discount margin in basis points.

        Raises
        ------
        ValueError
            If bond price is not set or YTM calculation does not converge.

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.discount_margin(price=95)
        np.float64(0.06100197251858131)
        """
        if tol is None:
            tol = 1e-6
        if max_iter is None:
            max_iter = 100
        if price is None:
            if self._price is None:
                raise ValueError("Bond price must be set to calculate discount margin.")
            price = self._price
        # Prepare cash flows and dates
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )
        if ref_rate_curve is None:
            if self.ref_rate_curve is None:
                raise ValueError(
                    "Either ref_rate_curve or self.ref_rate_curve must be provided."
                )
            else:
                ref_rate_curve = self.ref_rate_curve

        return (
            self._get_spread_from_price(
                price=price,
                settlement_date=settlement_date,
                ref_rate_curve=ref_rate_curve,
                current_ref_rate=current_ref_rate,
            )
            * 10000
        )

    def _get_spread_from_price(
        self,
        price: float,
        settlement_date: pd.Timestamp,
        ref_rate_curve: YieldCurveBase,
        current_ref_rate: Optional[float] = None,
    ):
        dated_payment_flow = self.make_expected_cash_flow(
            price=price,
            settlement_date=settlement_date,
            ref_rate_curve=ref_rate_curve,
            current_ref_rate=current_ref_rate,
        )

        # Make objective function to calculate present value of each cash flow
        def _price_difference(z_spread):
            return sum(
                {
                    d: ref_rate_curve.discount_date(d, z_spread) * value
                    for d, value in dated_payment_flow.items()
                }.values()
            )

        # Multiply all times by the coupon frequency to convert to BEY
        initial_guess = self.quoted_margin if self.quoted_margin > 0 else 0.005
        # find zero of the objective function using root_scalar
        z_spread = optimize.root_scalar(
            _price_difference, x0=initial_guess, method="newton"
        ).root

        return z_spread

    def yield_to_maturity(
        self,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
        current_ref_rate: Optional[float] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
        tol: Optional[float] = 1e-6,
        max_iter: Optional[int] = 100,
        curve_delta: float = 0.0,
    ):
        # Calculate the yield to maturity as the sum of the required margin and market rate until the next coupon
        required_margin = self.required_margin(
            price,
            settlement_date,
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
            current_ref_rate,
            ref_rate_curve,
            tol,
            max_iter,
        )

        # get next coupon date
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        # get next coupon date
        next_coupon_date = self.next_coupon_date(settlement_date)

        if ref_rate_curve is None:
            ref_rate_curve = self.ref_rate_curve
            assert ref_rate_curve is not None

        rate_to_next_coupon = ref_rate_curve.date_rate(
            next_coupon_date,
            yield_calculation_convention=yield_calculation_convention,
            spread=curve_delta,
        )

        return rate_to_next_coupon + required_margin / 10000

    def expected_yield_to_maturity(
        self,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
        current_ref_rate: Optional[float] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
        tol: Optional[float] = 1e-6,
        max_iter: Optional[int] = 100,
    ) -> float:
        """
        Estimate the yield to maturity (YTM) using the xirr function from pyfian.time_value.irr.

        The YTM is the internal rate of return (IRR) of the bond's cash flows, assuming the bond is held to maturity.

        It is the discount rate that makes the present value of the bond's cash flows equal to its price for a given set of cash flows and settlement date.

        The YTM is calculated by solving the equation:

        .. math::
            P = \\sum_{t=1}^{T} \\frac{C_t}{(1 + YTM)^{(t+1)}}

        where:

        - :math:`P` is the price of the bond
        - :math:`C_t` is the cash flow at time :math:`t`, where :math:`t` is the time in years from the settlement date
        - :math:`YTM` is the yield to maturity
        - :math:`T` is the total number of periods

        The times to payments are calculated from the settlement date to each payment date and need not be integer values.

        Parameters
        ----------
        price : float, optional
            Price of the bond. If not provided, will use self._price.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.
        current_ref_rate : float, optional
            Current reference rate as a decimal. If not provided, will use self.current_ref_rate.
        ref_rate_curve : YieldCurveBase, optional
            Reference rate curve to use for estimating future rates. If not provided, will use self.ref_rate_curve.
        tol : float, optional
            Tolerance for convergence (default is 1e-6).
        max_iter : int, optional
            Maximum number of iterations (default is 100).

        Returns
        -------
        ytm : float
            Estimated yield to maturity as a decimal.

        Raises
        ------
        ValueError
            If bond price is not set or YTM calculation does not converge.

        Examples
        --------
        >>> from pyfian.yield_curves.flat_curve import FlatCurveBEY
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.expected_yield_to_maturity(price=95)
        np.float64(0.06100197251858131)
        """
        if tol is None:
            tol = 1e-6
        if max_iter is None:
            max_iter = 100
        if price is None:
            if self._price is None:
                raise ValueError(
                    "Bond price must be set to calculate expected yield to maturity."
                )
            price = self._price

        # Prepare cash flows and dates
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )
        dated_payment_flow = self.make_expected_cash_flow(
            price=price,
            settlement_date=settlement_date,
            ref_rate_curve=ref_rate_curve,
            current_ref_rate=current_ref_rate,
        )

        times_cashflows = self._calculate_time_to_payments(
            settlement_date=settlement_date,
            price=price,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
            payment_flow=dated_payment_flow,
        )
        times = list(times_cashflows.keys())
        payment_flow = list(times_cashflows.values())

        time_adjustment = get_time_adjustment(yield_calculation_convention)

        # Multiply all times by the coupon frequency to convert to BEY
        times = [t * time_adjustment for t in times]
        initial_guess = (
            self.quoted_margin / 100 / time_adjustment
            if self.quoted_margin > 0
            else 0.05
        )

        # Use xirr to calculate YTM
        result = xirr_base(
            cash_flows=payment_flow,
            times=times,
            guess=initial_guess,
            tol=tol,
            max_iter=max_iter,
        )

        result = result * time_adjustment
        if yield_calculation_convention == "Continuous":
            result = rc.convert_yield(
                result, from_convention="Annual", to_convention="Continuous"
            )

        return result

    def accrued_interest(
        self,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        current_ref_rate: Optional[float] = None,
    ) -> float:
        """
        Calculate accrued interest since last coupon payment.
        This is the interest that has accumulated on the bond since the last coupon payment date
        or issue date if no coupon payments have been made.

        The accrued interest is calculated on an actual/actual basis, which means it considers
        the actual number of days between the last coupon payment date and the settlement date.

        The formula is as follows:

        .. math::
            Accrued = C \\cdot \\frac{SettlementDate - CouponDate_{prev}}{CouponDate_{next} - CouponDate_{prev}}

        where:

        - :math:`C` is the coupon payment amount
        - :math:`SettlementDate` is the date for which to calculate accrued interest
        - :math:`CouponDate_{prev}` is the last coupon payment date before the settlement or issue date if no previous coupon
        - :math:`CouponDate_{next}` is the next coupon payment date after the settlement

        Parameters
        ----------
        settlement_date : str or datetime-like, optional
            Date for which to calculate accrued interest. Defaults to today.
        current_ref_rate : float, optional
            Current reference rate as a decimal. If not provided, will use self.current_ref_rate.

        Returns
        -------
        accrued : float
            Accrued interest amount.

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', quoted_margin=0, cpn_freq=2)
        >>> bond.accrued_interest('2024-07-02')
        2.5
        """
        settlement_date = self._resolve_settlement_date(settlement_date)

        if current_ref_rate is None:
            if self.current_ref_rate is None:
                raise ValueError(
                    "Either current_ref_rate or self.current_ref_rate must be provided."
                )
            current_ref_rate = self.current_ref_rate
        if self.cpn_freq == 0:
            return 0.0

        prev_coupon: pd.Timestamp = self.previous_coupon_date(settlement_date)
        next_coupon: pd.Timestamp = self.next_coupon_date(settlement_date)

        coupon = (current_ref_rate + self.quoted_margin) * self.notional / 100

        # If before first coupon, accrue from issue date
        if prev_coupon is None and next_coupon is not None:
            fraction_period_adjusted = (
                self.day_count_convention.fraction_period_adjusted(
                    start=self.issue_dt,
                    current=settlement_date,
                    periods_per_year=self.cpn_freq,
                    end=next_coupon,
                )
            )

        # If between coupons, accrue from previous coupon
        else:  # prev_coupon is not None and next_coupon is not None:
            fraction_period_adjusted = (
                self.day_count_convention.fraction_period_adjusted(
                    start=prev_coupon,
                    current=settlement_date,
                    periods_per_year=self.cpn_freq,
                    end=next_coupon,
                )
            )

        return coupon * fraction_period_adjusted

    def next_coupon_date(
        self, settlement_date: Optional[Union[str, pd.Timestamp]] = None
    ) -> Optional[pd.Timestamp]:
        """
        Get the next coupon payment date from a given date.

        This method finds the next coupon payment date after the specified settlement date.
        If no future coupon payments exist, it returns None.

        Parameters
        ----------
        settlement_date : str or datetime-like, optional
            Date from which to search. Defaults to today. Adjusts to settlement date.

        Returns
        -------
        next_date : pd.Timestamp or None
            Next coupon payment date, or None if none remain.

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', quoted_margin=0, cpn_freq=2)
        >>> bond.next_coupon_date('2023-06-01')
        Timestamp('2024-01-01 00:00:00')
        """
        settlement_date = self._resolve_settlement_date(settlement_date)

        future_dates = [
            d
            for d, coupon in self.coupon_flow.items()
            if d >= settlement_date + pd.offsets.BDay(self.record_date_t_minus)
        ]
        return min(future_dates) if future_dates else None

    def previous_coupon_date(
        self, settlement_date: Optional[Union[str, pd.Timestamp]] = None
    ) -> Optional[pd.Timestamp]:
        """
        Get the previous coupon payment date from a given date.

        This method finds the last coupon payment date before the specified settlement date.
        If no past coupon payments exist, it returns None.

        Parameters
        ----------
        settlement_date : str or datetime-like, optional
            Date from which to search. Defaults to today. Adjusts to settlement date.

        Returns
        -------
        prev_date : pd.Timestamp or None
            Previous coupon payment date, or None if none exist.

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', quoted_margin=0, cpn_freq=2)
        >>> bond.previous_coupon_date('2023-06-01')
        Timestamp('2023-01-01 00:00:00')
        """
        settlement_date = self._resolve_settlement_date(settlement_date)

        past_dates = [
            d
            for d in self.coupon_flow.keys()
            if d < settlement_date + pd.offsets.BDay(self.record_date_t_minus)
        ]

        return max(past_dates) if past_dates else None

    def __repr__(self) -> str:
        """
        Return string representation of the FloatingRateNote object.

        Returns
        -------
        str
            String representation of the bond.

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', 100, 2)
        >>> print(bond)
        FloatingRateNote(issue_dt=2020-01-01 00:00:00, maturity=2025-01-01 00:00:00, quoted_margin=100, cpn_freq=2)
        """
        return (
            f"FloatingRateNote(issue_dt={self.issue_dt}, maturity={self.maturity}, "
            f"quoted_margin={self.quoted_margin * 10000}, cpn_freq={self.cpn_freq})"
        )

    def modified_duration(
        self,
        discount_margin: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
        current_ref_rate: Optional[float] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
    ) -> float:
        """
        Calculate modified duration of the bond. Modified duration for a floating rate note is very low since the cash flows are reset periodically.
        The interest rate risk is minimal as the coupon payments adjust with market rates.
        However, there is risk in the spread, which is captured through the spread duration.

        The times to payments are calculated from the settlement date to each payment date and need not be integer values.

        Parameters
        ----------
        discount_margin : float, optional
            Discount margin in basis points. If not provided, will be calculated from price if given.
        price : float, optional
            Price of the bond. Used to estimate YTM if yield_to_maturity is not provided.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.
        current_ref_rate : float, optional
            Current reference rate as a decimal. If not provided, will use self.current_ref_rate.
        ref_rate_curve : YieldCurveBase, optional
            Reference rate curve. If not provided, will use self.ref_rate_curve.

        Returns
        -------
        duration : float
            Modified duration in years.

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', quoted_margin=0, cpn_freq=2, price=100, settlement_date="2020-01-01")
        >>> bond.modified_duration()
        4.3760319684
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        ytm, price_calc = self._resolve_ytm_and_price(
            discount_margin,
            price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
            ref_rate_curve=ref_rate_curve,
            current_ref_rate=current_ref_rate,
        )

        if ytm is None or price_calc is None:
            raise ValueError(
                "Unable to resolve yield to maturity. You must input settlement_date and either yield_to_maturity or price. Previous information was not available."
            )

        start = self.previous_coupon_date(
            settlement_date=settlement_date,
        )
        if start is None:
            start = self.issue_dt

        # get next coupon date
        next_coupon_date = self.next_coupon_date(settlement_date)

        t_passed = day_count_convention.fraction_period_adjusted(
            start=start,
            current=settlement_date,
            end=next_coupon_date,
            periods_per_year=self.cpn_freq,
        )

        time_adjustment = get_time_adjustment(yield_calculation_convention)

        # Calculate time to next coupon
        t = (
            following_coupons_day_count.fraction(
                start=start,
                current=next_coupon_date,
            )
            - t_passed / time_adjustment
        )

        # modified_duration = t * cf / (1 + ytm / m)^(t*m+1) / p / (1 + ytm / m)^(t*m) =
        # p = cf / (1 + ytm / m)^(t*m)
        # modified_duration = t * cf / (1 + ytm / m)^(t*m) / (cf / (1 + ytm / m)^(t*m)) / (1 + ytm / m) =
        # modified_duration = t / (1 + ytm / m)

        if yield_calculation_convention == "Continuous":
            duration = t
        else:
            duration = t / (1 + ytm / time_adjustment)
        return round(duration, 10)

    def spread_duration(
        self,
        discount_margin: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
        current_ref_rate: Optional[float] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
    ) -> float:
        """
        Calculate spread duration of the bond.
        While modified duration of a floating rate note is very low since the cash flows are reset periodically,
        the spread duration captures the risk in the spread. The interest rate risk is minimal as the coupon payments adjust with market rates.
        However, there is risk in the spread, which is captured through the spread duration.

        The times to payments are calculated from the settlement date to each payment date and need not be integer values.

        Parameters
        ----------
        discount_margin : float, optional
            Discount margin in basis points. If not provided, will be calculated from price if given.
        price : float, optional
            Price of the bond. Used to estimate YTM if yield_to_maturity is not provided.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.
        current_ref_rate : float, optional
            Current reference rate as a decimal. If not provided, will use self.current_ref_rate.
        ref_rate_curve : YieldCurveBase, optional
            Reference rate curve. If not provided, will use self.ref_rate_curve.

        Returns
        -------
        duration : float
            Modified duration in years.

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', quoted_margin=0, cpn_freq=2, price=100, settlement_date="2020-01-01")
        >>> bond.spread_duration()
        4.3760319684
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        discount_margin, price = self._resolve_discount_margin_and_price(
            discount_margin,
            price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
            ref_rate_curve=ref_rate_curve,
            current_ref_rate=current_ref_rate,
        )
        expected_ytm = self.expected_yield_to_maturity(
            price=price,
            settlement_date=settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
            ref_rate_curve=ref_rate_curve,
            current_ref_rate=current_ref_rate,
        )

        dated_payment_flow = self.make_expected_cash_flow(
            price=price,
            settlement_date=settlement_date,
            ref_rate_curve=ref_rate_curve,
            current_ref_rate=current_ref_rate,
        )
        times_cashflows = self._calculate_time_to_payments(
            settlement_date=settlement_date,
            price=price,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
            payment_flow=dated_payment_flow,
        )

        time_adjustment = get_time_adjustment(yield_calculation_convention)

        if yield_calculation_convention == "Continuous":
            duration = sum(
                [
                    t * cf * np.exp(-expected_ytm * t)
                    for t, cf in times_cashflows.items()
                ]
            )
        else:
            duration = sum(
                [
                    t
                    * cf
                    / (1 + expected_ytm / time_adjustment) ** (t * time_adjustment + 1)
                    for t, cf in times_cashflows.items()
                ]
            )
        return round(duration / price if price != 0 else 0.0, 10)

    def effective_duration(
        self,
        discount_margin: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
        current_ref_rate: Optional[float] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
    ) -> float:
        """
        Calculate effective duration of the bond.

        .. math::
            \\text{Effective Duration} = -\\frac{(P_{+} - P_{-})}{2 \\cdot \\epsilon \\cdot P}

        where:

        - :math:`P` is the price of the bond
        - :math:`P_{+}` is the price if yield increases by :math:`\\epsilon`
        - :math:`P_{-}` is the price if yield decreases by :math:`\\epsilon`
        - :math:`\\epsilon` is a small change in yield

        The times to payments are calculated from the settlement date to each payment date and need not be integer values.

        Parameters
        ----------
        discount_margin : float, optional
            Discount margin in basis points. If not provided, will be calculated from price if given.
        price : float, optional
            Price of the bond. Used to estimate discount_margin if not provided.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.
        current_ref_rate : float, optional
            Current reference rate as a decimal. If not provided, will use self.current_ref_rate.
        ref_rate_curve : YieldCurveBase, optional
            Reference rate curve. If not provided, will use self.ref_rate_curve.

        Returns
        -------
        duration : float
            Effective duration in years.

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', quoted_margin=0, cpn_freq=2, price=100, settlement_date="2020-01-01")
        >>> bond.effective_duration()
        4.3760319684
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        ytm, price_calc = self._resolve_ytm_and_price(
            discount_margin,
            price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
            ref_rate_curve=ref_rate_curve,
            current_ref_rate=current_ref_rate,
        )

        if ytm is None or price_calc is None:
            raise ValueError("Unable to determine yield to maturity.")

        # get next coupon date
        start = self.previous_coupon_date(
            settlement_date=settlement_date,
        )
        if start is None:
            start = self.issue_dt

        # get next coupon date
        next_coupon_date = self.next_coupon_date(settlement_date)

        t_passed = day_count_convention.fraction_period_adjusted(
            start=start,
            current=settlement_date,
            end=next_coupon_date,
            periods_per_year=self.cpn_freq,
        )

        time_adjustment = get_time_adjustment(yield_calculation_convention)

        # Calculate time to next coupon
        t = (
            following_coupons_day_count.fraction(
                start=start,
                current=next_coupon_date,
            )
            - t_passed / time_adjustment
        )
        # Calculate effective duration using a small epsilon
        epsilon = 0.0000001

        if yield_calculation_convention == "Continuous":
            price = np.exp(-ytm * t)
            price_plus_epsilon = np.exp(-(ytm + epsilon) * t)
            price_minus_epsilon = np.exp(-(ytm - epsilon) * t)
        else:
            price = 1 / (1 + ytm / time_adjustment) ** (t * time_adjustment)
            price_plus_epsilon = 1 / (1 + (ytm + epsilon) / time_adjustment) ** (
                t * time_adjustment
            )
            price_minus_epsilon = 1 / (1 + (ytm - epsilon) / time_adjustment) ** (
                t * time_adjustment
            )

        effective_duration = (
            -1 * (price_plus_epsilon - price_minus_epsilon) / (2 * epsilon * price)
        )
        return round(effective_duration, 10)

    def effective_spread_duration(
        self,
        discount_margin: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
        current_ref_rate: Optional[float] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
    ) -> float:
        """
        Calculate spread effective duration of the bond.

        .. math::
            \\text{Spread Effective Duration} = -\\frac{(P_{+} - P_{-})}{2 \\cdot \\epsilon \\cdot P}

        where:

        - :math:`P` is the price of the bond
        - :math:`P_{+}` is the price if spread increases by :math:`\\epsilon`
        - :math:`P_{-}` is the price if spread decreases by :math:`\\epsilon`
        - :math:`\\epsilon` is a small change in spread

        The times to payments are calculated from the settlement date to each payment date and need not be integer values.

        Parameters
        ----------
        discount_margin : float, optional
            Discount margin in basis points. If not provided, will be calculated from price if given.
        price : float, optional
            Price of the bond. Used to estimate discount_margin if not provided.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.
        current_ref_rate : float, optional
            Current reference rate as a decimal. If not provided, will use self.current_ref_rate.
        ref_rate_curve : YieldCurveBase, optional
            Reference rate curve. If not provided, will use self.ref_rate_curve.

        Returns
        -------
        duration : float
            Effective duration in years.

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', quoted_margin=0, cpn_freq=2, price=100, settlement_date="2020-01-01")
        >>> bond.effective_spread_duration()
        4.3760319684
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        # If calculate is False, raise ValueError since we cannot compute effective spread duration
        calculate, ref_rate_curve, current_ref_rate = self._should_calculate(
            settlement_date, ref_rate_curve, current_ref_rate
        )
        if not calculate:
            raise ValueError(
                "There is not enough information to calculate prices to calculate spread duration."
                "Please provide a reference rate curve and a current reference rate if the settlement date is not the curve date."
            )
        else:
            discount_margin, price = self._resolve_discount_margin_and_price(
                discount_margin,
                price,
                settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                day_count_convention=day_count_convention,
                ref_rate_curve=ref_rate_curve,
                current_ref_rate=current_ref_rate,
            )
            assert discount_margin is not None
            assert price is not None

            # Calculate effective duration using a small epsilon
            epsilon = 0.0001
            price_plus_epsilon = self._price_from_discount_margin_and_clean_parameters(
                discount_margin + epsilon,
                settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                day_count_convention=day_count_convention,
                ref_rate_curve=ref_rate_curve,
                current_ref_rate=current_ref_rate,
            )
            price_minus_epsilon = self._price_from_discount_margin_and_clean_parameters(
                discount_margin - epsilon,
                settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                day_count_convention=day_count_convention,
                ref_rate_curve=ref_rate_curve,
                current_ref_rate=current_ref_rate,
            )

            effective_spread_duration = (
                -1
                * (price_plus_epsilon - price_minus_epsilon)
                / (2 * epsilon / 10000 * price)
            )
            return round(effective_spread_duration, 10)

    def dv01(
        self,
        discount_margin: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
        current_ref_rate: Optional[float] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
    ) -> float:
        """
        Calculate the DV01 (Dollar Value of a 1 basis point) for the bond. The DV01 measures the change in the bond's price for a 1 basis point (0.0001) change in yield.
        Since floating rate notes have coupons that adjust with market rates, their DV01 is typically lower than that of fixed-rate bonds.

        Parameters
        ----------
        discount_margin : float, optional
            Discount margin in basis points (e.g., 50 for 0.50%).
        price : float, optional
            Price of the bond. Used to estimate YTM if discount_margin is not provided.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.
        current_ref_rate : float, optional
            Current reference rate as a decimal. If not provided, will use self.current_ref_rate.
        ref_rate_curve : YieldCurveBase, optional
            Reference rate curve. If not provided, will use self.ref_rate_curve.

        Returns
        -------
        dv01 : float
            The change in price for a 1 basis point (0.0001) change in yield.

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', quoted_margin=0, cpn_freq=2, price=100, settlement_date="2020-01-01")
        >>> bond.dv01()
        -0.0437603218
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )
        # Resolve yield to maturity and bond price
        ytm, price_calc = self._resolve_ytm_and_price(
            discount_margin,
            price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
            ref_rate_curve=ref_rate_curve,
            current_ref_rate=current_ref_rate,
        )

        if ytm is None:
            raise ValueError(
                "Unable to resolve yield to maturity. You must input settlement_date and either yield_to_maturity or price. Previous information was not available."
            )

        start = self.previous_coupon_date(
            settlement_date=settlement_date,
        )
        if start is None:
            start = self.issue_dt

        # get next coupon date
        next_coupon_date = self.next_coupon_date(settlement_date)

        t_passed = day_count_convention.fraction_period_adjusted(
            start=start,
            current=settlement_date,
            end=next_coupon_date,
            periods_per_year=self.cpn_freq,
        )

        time_adjustment = get_time_adjustment(yield_calculation_convention)

        # Calculate time to next coupon
        t = (
            following_coupons_day_count.fraction(
                start=start,
                current=next_coupon_date,
            )
            - t_passed / time_adjustment
        )

        if yield_calculation_convention == "Continuous":
            expected_price_reset = price_calc * np.exp(ytm * t)
        else:
            expected_price_reset = price_calc * (1 + ytm / time_adjustment) ** (
                t * time_adjustment
            )

        # Calculate price if yield increases by 1 basis point
        if yield_calculation_convention == "Continuous":
            price_up = expected_price_reset * np.exp(-(ytm + 0.0001) * t)
            price_down = expected_price_reset * np.exp(-(ytm - 0.0001) * t)
        else:
            price_up = expected_price_reset / (
                1 + (ytm + 0.0001) / time_adjustment
            ) ** (t * time_adjustment)
            price_down = expected_price_reset / (
                1 + (ytm - 0.0001) / time_adjustment
            ) ** (t * time_adjustment)

        return round(-(price_up - price_down) / 2, 10)

    def spread_dv01(
        self,
        discount_margin: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
        current_ref_rate: Optional[float] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
    ) -> float:
        """
        Calculate the spread DV01 (Dollar Value of a 1 basis point) for the bond. The DV01 measures the change in the bond's price for a 1 basis point (0.0001) change in discount margin.
        Since floating rate notes have coupons that adjust with market rates, their DV01 is typically lower than that of fixed-rate bonds.
        In contrast, the spread DV01 can be more sensitive to changes in the discount margin and reflect real risk.

        Parameters
        ----------
        discount_margin : float, optional
            Discount margin in basis points (e.g., 50 for 0.50%).
        price : float, optional
            Price of the bond. Used to estimate YTM if discount_margin is not provided.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.
        current_ref_rate : float, optional
            Current reference rate as a decimal. If not provided, will use self.current_ref_rate.
        ref_rate_curve : YieldCurveBase, optional
            Reference rate curve. If not provided, will use self.ref_rate_curve.

        Returns
        -------
        dv01 : float
            The change in price for a 1 basis point (0.0001) change in yield.

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', quoted_margin=0, cpn_freq=2, price=100, settlement_date="2020-01-01")
        >>> bond.dv01()
        -0.0437603218
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        calculate, ref_rate_curve, current_ref_rate = self._should_calculate(
            settlement_date, ref_rate_curve, current_ref_rate
        )

        if not calculate:
            raise ValueError(
                "There is not enough information to calculate prices to calculate spread duration."
                "Please provide a reference rate curve and a current reference rate if the settlement date is not the curve date."
            )
        else:
            discount_margin, price = self._resolve_discount_margin_and_price(
                discount_margin,
                price,
                settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                day_count_convention=day_count_convention,
                ref_rate_curve=ref_rate_curve,
                current_ref_rate=current_ref_rate,
            )
            assert discount_margin is not None
            assert price is not None

            # Calculate effect of a basis point change in discount margin on price
            epsilon = 1
            price_plus_epsilon = self._price_from_discount_margin_and_clean_parameters(
                discount_margin + epsilon,
                settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                day_count_convention=day_count_convention,
                ref_rate_curve=ref_rate_curve,
                current_ref_rate=current_ref_rate,
            )
            price_minus_epsilon = self._price_from_discount_margin_and_clean_parameters(
                discount_margin - epsilon,
                settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                day_count_convention=day_count_convention,
                ref_rate_curve=ref_rate_curve,
                current_ref_rate=current_ref_rate,
            )

            spread_dv01 = -(price_plus_epsilon - price_minus_epsilon) / 2
            return round(spread_dv01, 10)

    def _resolve_ytm_and_price(
        self,
        discount_margin: Optional[float],
        price: Optional[float],
        settlement_date: Optional[Union[str, pd.Timestamp]],
        adjust_to_business_days: bool,
        day_count_convention: DayCountBase,
        following_coupons_day_count: DayCountBase,
        yield_calculation_convention: str,
        ref_rate_curve: Optional[YieldCurveBase],
        current_ref_rate: Optional[float],
        curve_delta: float = 0.0,
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Helper to resolve yield_to_maturity and price from direct input, price, or default to notional.
        Returns a tuple (ytm, price_calc), both float or None.
        """
        # Case 1: price is provided, discount margin is None
        if price is not None and discount_margin is None:
            if price < 0:
                raise ValueError("Bond price cannot be negative.")
            ytm = self.yield_to_maturity(
                price=price,
                settlement_date=settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                day_count_convention=day_count_convention,
                ref_rate_curve=ref_rate_curve,
                current_ref_rate=current_ref_rate,
                curve_delta=curve_delta,
            )
            return ytm, price

        # Case 2: both price and discount margin are provided
        if price is not None and discount_margin is not None:
            if price < 0:
                raise ValueError("Bond price cannot be negative.")

            calculate, ref_rate_curve, current_ref_rate = self._should_calculate(
                settlement_date, ref_rate_curve, current_ref_rate
            )

            if calculate:
                price_calc = self._price_from_discount_margin_and_clean_parameters(
                    discount_margin=discount_margin,
                    settlement_date=settlement_date,
                    adjust_to_business_days=adjust_to_business_days,
                    following_coupons_day_count=following_coupons_day_count,
                    yield_calculation_convention=yield_calculation_convention,
                    day_count_convention=day_count_convention,
                    ref_rate_curve=ref_rate_curve,
                    current_ref_rate=current_ref_rate,
                    curve_delta=curve_delta,
                )
                if abs(price_calc - price) / price > 0.001 / 100:
                    raise ValueError(
                        "Bond price calculated by yield to maturity does not match the given bond price."
                        "Given bond price: {}, calculated bond price: {}".format(
                            price, price_calc
                        )
                    )
                yield_to_maturity = self.yield_to_maturity(
                    price=price,
                    settlement_date=settlement_date,
                    adjust_to_business_days=adjust_to_business_days,
                    following_coupons_day_count=following_coupons_day_count,
                    yield_calculation_convention=yield_calculation_convention,
                    day_count_convention=day_count_convention,
                    ref_rate_curve=ref_rate_curve,
                    current_ref_rate=current_ref_rate,
                    curve_delta=curve_delta,
                )

                return yield_to_maturity, price
            else:
                return None, price

        # Case 3: only discount margin is provided
        if discount_margin is not None:
            calculate, ref_rate_curve, current_ref_rate = self._should_calculate(
                settlement_date, ref_rate_curve, current_ref_rate
            )
            if calculate:
                price_calc = self._price_from_discount_margin_and_clean_parameters(
                    discount_margin=discount_margin,
                    settlement_date=settlement_date,
                    adjust_to_business_days=adjust_to_business_days,
                    following_coupons_day_count=following_coupons_day_count,
                    yield_calculation_convention=yield_calculation_convention,
                    day_count_convention=day_count_convention,
                    ref_rate_curve=ref_rate_curve,
                    current_ref_rate=current_ref_rate,
                    curve_delta=curve_delta,
                )

                yield_to_maturity = self.yield_to_maturity(
                    price=price_calc,
                    settlement_date=settlement_date,
                    adjust_to_business_days=adjust_to_business_days,
                    following_coupons_day_count=following_coupons_day_count,
                    yield_calculation_convention=yield_calculation_convention,
                    day_count_convention=day_count_convention,
                    ref_rate_curve=ref_rate_curve,
                    current_ref_rate=current_ref_rate,
                    curve_delta=curve_delta,
                )

                return yield_to_maturity, price_calc

        # Case 4: use stored values if available and settlement date matches
        if (
            self._yield_to_maturity is not None
            and self._settlement_date == settlement_date
        ):
            if (
                day_count_convention != self.day_count_convention
                or yield_calculation_convention != self.yield_calculation_convention
            ):
                ytm = self.yield_to_maturity(
                    price=price,
                    settlement_date=settlement_date,
                    adjust_to_business_days=adjust_to_business_days,
                    following_coupons_day_count=following_coupons_day_count,
                    yield_calculation_convention=yield_calculation_convention,
                    day_count_convention=day_count_convention,
                    curve_delta=curve_delta,
                )
            else:
                ytm = self._yield_to_maturity

            return ytm, self._price

        # Case 5: cannot determine, return None, None
        return None, None

    def _resolve_discount_margin_and_price(
        self,
        discount_margin: Optional[float],
        price: Optional[float],
        settlement_date: Optional[Union[str, pd.Timestamp]],
        adjust_to_business_days: bool,
        day_count_convention: DayCountBase,
        following_coupons_day_count: DayCountBase,
        yield_calculation_convention: str,
        ref_rate_curve: Optional[YieldCurveBase],
        current_ref_rate: Optional[float],
        curve_delta: float = 0.0,
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Helper to resolve yield_to_maturity and price from direct input, price, or default to notional.
        Returns a tuple (ytm, price_calc), both float or None.
        """
        # Case 1: price is provided, discount margin is None
        if price is not None and discount_margin is None:
            if price < 0:
                raise ValueError("Bond price cannot be negative.")
            discount_margin = self.discount_margin(
                price=price,
                settlement_date=settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                day_count_convention=day_count_convention,
                ref_rate_curve=ref_rate_curve,
                current_ref_rate=current_ref_rate,
            )
            return discount_margin, price

        # Case 2: both price and discount margin are provided
        if price is not None and discount_margin is not None:
            if price < 0:
                raise ValueError("Bond price cannot be negative.")

            calculate, ref_rate_curve, current_ref_rate = self._should_calculate(
                settlement_date, ref_rate_curve, current_ref_rate
            )

            if calculate:
                price_calc = self._price_from_discount_margin_and_clean_parameters(
                    discount_margin=discount_margin,
                    settlement_date=settlement_date,
                    adjust_to_business_days=adjust_to_business_days,
                    following_coupons_day_count=following_coupons_day_count,
                    yield_calculation_convention=yield_calculation_convention,
                    day_count_convention=day_count_convention,
                    ref_rate_curve=ref_rate_curve,
                    current_ref_rate=current_ref_rate,
                    curve_delta=curve_delta,
                )
                if abs(price_calc - price) / price > 0.001 / 100:
                    raise ValueError(
                        "Bond price calculated by discount margin does not match the given bond price."
                        "Given bond price: {}, calculated bond price: {}".format(
                            price, price_calc
                        )
                    )

                return discount_margin, price
            else:
                return None, price

        # Case 3: only discount margin is provided
        if discount_margin is not None:
            calculate, ref_rate_curve, current_ref_rate = self._should_calculate(
                settlement_date, ref_rate_curve, current_ref_rate
            )
            if calculate:
                price_calc = self._price_from_discount_margin_and_clean_parameters(
                    discount_margin=discount_margin,
                    settlement_date=settlement_date,
                    adjust_to_business_days=adjust_to_business_days,
                    following_coupons_day_count=following_coupons_day_count,
                    yield_calculation_convention=yield_calculation_convention,
                    day_count_convention=day_count_convention,
                    ref_rate_curve=ref_rate_curve,
                    current_ref_rate=current_ref_rate,
                    curve_delta=curve_delta,
                )
                return discount_margin, price_calc

        # Case 4: use stored values if available and settlement date matches
        if (
            self._discount_margin is not None
            and self._settlement_date == settlement_date
        ):
            if (
                day_count_convention != self.day_count_convention
                or yield_calculation_convention != self.yield_calculation_convention
            ):
                discount_margin = self.discount_margin(
                    price=price,
                    settlement_date=settlement_date,
                    adjust_to_business_days=adjust_to_business_days,
                    following_coupons_day_count=following_coupons_day_count,
                    yield_calculation_convention=yield_calculation_convention,
                    day_count_convention=day_count_convention,
                    current_ref_rate=current_ref_rate,
                    ref_rate_curve=ref_rate_curve,
                )
            else:
                discount_margin = self._discount_margin

            return discount_margin, self._price

        # Case 5: cannot determine, return None, None
        return None, None

    def macaulay_duration(
        self,
        discount_margin: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
        current_ref_rate: Optional[float] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
    ) -> float:
        """
        Calculate macaulay duration of the bond. Macaulay duration for a floating rate note is very low since the cash flows are reset periodically.
        The interest rate risk is minimal as the coupon payments adjust with market rates.
        However, there is risk in the spread, which is captured through the spread duration.

        The times to payments are calculated from the settlement date to each payment date and need not be integer values.

        Parameters
        ----------
        discount_margin : float, optional
            Discount margin in basis points. If not provided, will be calculated from price if given.
        price : float, optional
            Price of the bond. Used to estimate YTM if yield_to_maturity is not provided.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.
        current_ref_rate : float, optional
            Current reference rate as a decimal. If not provided, will use self.current_ref_rate.
        ref_rate_curve : YieldCurveBase, optional
            Reference rate curve. If not provided, will use self.ref_rate_curve.

        Returns
        -------
        duration : float
            Macaulay duration in years.

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', quoted_margin=0, cpn_freq=2, price=100, settlement_date="2020-01-01")
        >>> bond.macaulay_duration(yield_to_maturity=0.05, settlement_date='2020-01-01')
        4.3760319684
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        ytm, price_calc = self._resolve_ytm_and_price(
            discount_margin,
            price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
            ref_rate_curve=ref_rate_curve,
            current_ref_rate=current_ref_rate,
        )

        if ytm is None or price_calc is None:
            raise ValueError(
                "Unable to resolve yield to maturity. You must input settlement_date and either yield_to_maturity or price. Previous information was not available."
            )

        start = self.previous_coupon_date(
            settlement_date=settlement_date,
        )
        if start is None:
            start = self.issue_dt

        # get next coupon date
        next_coupon_date = self.next_coupon_date(settlement_date)

        t_passed = day_count_convention.fraction_period_adjusted(
            start=start,
            current=settlement_date,
            end=next_coupon_date,
            periods_per_year=self.cpn_freq,
        )

        time_adjustment = get_time_adjustment(yield_calculation_convention)

        # Calculate time to next coupon
        t = (
            following_coupons_day_count.fraction(
                start=start,
                current=next_coupon_date,
            )
            - t_passed / time_adjustment
        )
        # modified_duration = t * cf / (1 + ytm / m)^(t*m) / p / (1 + ytm / m)^(t*m) =
        # p = cf / (1 + ytm / m)^(t*m)
        # modified_duration = t * cf / (1 + ytm / m)^(t*m) / (cf / (1 + ytm / m)^(t*m)) / (1 + ytm / m) =
        # modified_duration = t / (1 + ytm / m)^(1)

        if yield_calculation_convention == "Continuous":
            duration = t
        else:
            duration = t
        return round(duration, 10)

    def convexity(
        self,
        discount_margin: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
        current_ref_rate: Optional[float] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
    ) -> float:
        """
        Calculate the convexity of the bond. The convexity for a floating rate note is generally low since the cash flows are reset periodically.

        .. math::
            Convexity = \\frac{1}{P} \\sum_{t=1}^{T} \\frac{C_t \\cdot t \\cdot (t + 1)}{(1 + YTM)^{(t + 2)}}
        where:

        - :math:`P` is the price of the bond
        - :math:`C_t` is the cash flow at time :math:`t`, where :math:`t` is the time in years from the settlement date
        - :math:`YTM` is the yield to maturity
        - :math:`T` is the total number of periods

        The times to payments are calculated from the settlement date to each payment date and need not be integer values.

        Parameters
        ----------
        yield_to_maturity : float, optional
            Yield to maturity as a decimal. If not provided, will be calculated from price if given.
        price : float, optional
            Price of the bond. Used to estimate YTM if yield_to_maturity is not provided.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.

        Returns
        -------
        convexity : float
            Bond convexity.

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', quoted_margin=0, cpn_freq=2, price=100, settlement_date="2020-01-01")
        >>> bond.convexity()
        22.6123221851
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        ytm, price_calc = self._resolve_ytm_and_price(
            discount_margin,
            price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
            ref_rate_curve=ref_rate_curve,
            current_ref_rate=current_ref_rate,
        )

        if ytm is None or price_calc is None:
            raise ValueError(
                "Unable to resolve yield to maturity. You must input settlement_date and either yield_to_maturity or price. Previous information was not available."
            )

        start = self.previous_coupon_date(
            settlement_date=settlement_date,
        )
        if start is None:
            start = self.issue_dt

        # get next coupon date
        next_coupon_date = self.next_coupon_date(settlement_date)

        t_passed = day_count_convention.fraction_period_adjusted(
            start=start,
            current=settlement_date,
            end=next_coupon_date,
            periods_per_year=self.cpn_freq,
        )

        time_adjustment = get_time_adjustment(yield_calculation_convention)

        # Calculate time to next coupon
        t = (
            following_coupons_day_count.fraction(
                start=start,
                current=next_coupon_date,
            )
            - t_passed / time_adjustment
        )

        # convexity = 1 / p * sum( cf * t * (t + 1) / (1 + ytm / m)^(t*m + 2) )

        if yield_calculation_convention == "Continuous":
            convexity = t**2 * np.exp(-ytm * t)
        else:
            convexity = (
                t
                * time_adjustment
                * (t * time_adjustment + 1)
                / (1 + ytm / time_adjustment) ** (t * time_adjustment + 2)
            )

        return round(convexity / time_adjustment**2, 10) if price_calc != 0 else 0.0

    def plot_cash_flows(
        self,
        discount_margin: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
        current_ref_rate: Optional[float] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
    ) -> None:
        """
        Visualize the cash flow schedule using matplotlib as stacked bars.

        Parameters
        ----------
        discount_margin : float, optional
            Discount margin in basis points. If not provided, will be calculated from price if given.
        price : float, optional
            If provided, includes bond price as a negative cash flow.
        settlement_date : str or datetime-like, optional
            Date from which to consider future payments. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.
        current_ref_rate : float, optional
            Current reference rate as a decimal. If not provided, will use self.current_ref_rate.
        ref_rate_curve : YieldCurveBase, optional
            Reference rate curve. If not provided, will use self.ref_rate_curve.

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', quoted_margin=0, cpn_freq=2, price=100)
        >>> bond.plot_cash_flows(settlement_date='2022-01-01') # doctest: +SKIP
        # Shows a plot
        """
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )
        df = self.to_dataframe(
            settlement_date=settlement_date,
            discount_margin=discount_margin,
            price=price,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
            ref_rate_curve=ref_rate_curve,
            current_ref_rate=current_ref_rate,
        )
        x_labels = df.index.strftime("%Y-%m-%d")
        cost = -df["Cost"]
        coupon = df["Expected Coupon"]
        amortization = df["Amortization"]

        fig = plt.figure(figsize=(10, 6))
        plt.bar(x_labels, cost, width=0.6, label="Cost")
        plt.bar(x_labels, coupon, width=0.6, bottom=cost, label="Expected Coupon")
        plt.bar(
            x_labels,
            amortization,
            width=0.6,
            bottom=cost + coupon,
            label="Amortization",
        )
        plt.xlabel("Date")
        plt.ylabel("Cash Flow")
        plt.title("Bond Cash Flow Schedule with Expected Cash Flows (Stacked)")
        plt.xticks(rotation=45)
        plt.legend()
        plt.tight_layout()
        plt.show()

        # return figure
        return fig

    def to_dataframe(
        self,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        discount_margin: Optional[float] = None,
        price: Optional[float] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
        current_ref_rate: Optional[float] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
    ) -> pd.DataFrame:
        """
        Export the bond's cash flow schedule as a pandas DataFrame.

        The DataFrame will contain the dates of cash flows and their corresponding amounts.

        The cash flows include:
        - Principal repayment at maturity
        - Coupon payments
        - Amortization payments (if applicable)
        - Bond price as a negative cash flow if provided

        The Dataframe will have the following columns:
        - 'date': The date of the cash flow.
        - 'Flows': The amount of the total cash flow.
        - 'Coupon': The coupon payment amount.
        - 'Amortization': The amortization payment amount.
        - 'Cost': The net cash flow after subtracting coupon and amortization payments.

        Parameters
        ----------
        settlement_date : str or datetime-like, optional
            Date from which to consider future payments. Defaults to issue date.
        discount_margin : float, optional
            Discount margin in basis points. If provided, it will be used to calculate the cash flows.
        price : float, optional
            If provided, includes bond price as a negative cash flow.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.
        current_ref_rate : float, optional
            Current reference rate as a decimal. If not provided, will use self.current_ref_rate.
        ref_rate_curve : YieldCurveBase, optional
            Reference rate curve. If not provided, will use self.ref_rate_curve.

        Returns
        -------
        df : pd.DataFrame
            DataFrame with columns ['date', 'cash_flow']

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', quoted_margin=0, cpn_freq=2, price=100)
        >>> bond.to_dataframe('2022-01-01') # doctest: +SKIP
        date        Flows  Coupon  Amortization  Cost
        2023-01-01  5.0    5.0          0.0           0.0
        2024-01-01  5.0    5.0          0.0           0.0
        2025-01-01  105.0  5.0        100.0           0.0
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        if ref_rate_curve is None:
            if self.ref_rate_curve is None:
                raise ValueError(
                    "Either ref_rate_curve or self.ref_rate_curve must be provided."
                )
            else:
                ref_rate_curve = self.ref_rate_curve

        # If neither discount_margin nor price is provided, make price calculation None
        if discount_margin is None and price is None:
            valid_price_calc = False
        else:
            valid_price_calc = True

        flows = self.filter_payment_flow(
            settlement_date,
            price if valid_price_calc else None,
            adjust_to_business_days=adjust_to_business_days,
            day_count_convention=day_count_convention,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
        )

        spread_flows = self.filter_payment_flow(
            settlement_date,
            None,
            self.spread_flow,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        amortization_flows = self.filter_payment_flow(
            settlement_date,
            None,
            self.amortization_flow,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        expected_cash_flows = self.make_expected_cash_flow(
            price=None,
            current_ref_rate=current_ref_rate,
            ref_rate_curve=ref_rate_curve,
            settlement_date=settlement_date,
        )
        expected_coupon_flows = (
            pd.Series(expected_cash_flows)
            - pd.Series(amortization_flows)
            - pd.Series(spread_flows)
        )

        # Concat coupon_flows and amortization_flows in a single dataframe
        df = (
            pd.concat(
                [
                    pd.Series(flows, name="Flows"),
                    pd.Series(expected_coupon_flows, name="Expected Coupon"),
                    pd.Series(spread_flows, name="Spread"),
                    pd.Series(amortization_flows, name="Amortization"),
                ],
                axis=1,
            )
            .astype(float)
            .fillna(0)
        )
        df["Cost"] = df["Expected Coupon"] + df["Amortization"] - df["Flows"]
        df.index = pd.DatetimeIndex(df.index)

        return df.sort_index()

    def z_spread(
        self,
        price: Optional[float] = None,
        discount_margin: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
        current_ref_rate: Optional[float] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
        tol: Optional[float] = 1e-6,
        max_iter: Optional[int] = 100,
    ) -> float:
        """
        Estimate the spread over the reference rate curve using the xirr function from pyfian.time_value.irr.

        The spread is the difference between the yield of the bond and the yield of the reference rate curve at the same maturity.

        It is the additional yield that investors require to hold the bond instead of a risk-free reference bond.

        The spread is calculated by solving the equation:

        .. math::
            P = \\sum_{t=1}^{T} \\frac{C_t}{(1 + YTM + Spread)^{(t+1)}}

        where:

        - :math:`P` is the price of the bond
        - :math:`C_t` is the cash flow at time :math:`t`, where :math:`t` is the time in years from the settlement date
        - :math:`YTM` is the yield to maturity
        - :math:`T` is the total number of periods

        The times to payments are calculated from the settlement date to each payment date and need not be integer values.

        Parameters
        ----------
        price : float, optional
            Price of the bond. If not provided, will use self._price.
        discount_margin : float, optional
            Discount margin in basis points. If provided, it will be used to calculate the price.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.
        current_ref_rate : float, optional
            Current reference rate as a decimal. If not provided, will use self.current_ref_rate.
        ref_rate_curve : YieldCurveBase, optional
            Reference rate curve to use for estimating future rates. If not provided, will use self.ref_rate_curve.
        tol : float, optional
            Tolerance for convergence (default is 1e-6).
        max_iter : int, optional
            Maximum number of iterations (default is 100).

        Returns
        -------
        z_spread : float
            Estimated z-spread as a decimal.

        Raises
        ------
        ValueError
            If bond price is not set or z-spread calculation does not converge.

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.z_spread(price=95)
        np.float64(0.06100197251858131)
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )
        if tol is None:
            tol = 1e-6
        if max_iter is None:
            max_iter = 100

        if ref_rate_curve is None:
            if self.ref_rate_curve is None:
                raise ValueError(
                    "Either ref_rate_curve or self.ref_rate_curve must be provided."
                )
            else:
                ref_rate_curve = self.ref_rate_curve

        discount_margin, price = self._resolve_discount_margin_and_price(
            discount_margin,
            price,
            settlement_date,
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
            ref_rate_curve=ref_rate_curve,
            current_ref_rate=current_ref_rate,
        )

        if price is None:
            if self._price is None:
                raise ValueError("Bond price must be set to calculate spread.")
            price = self._price
        # Prepare cash flows and dates
        settlement_date = self._resolve_settlement_date(settlement_date)

        return self._get_spread_from_price(
            price=price,
            settlement_date=settlement_date,
            ref_rate_curve=ref_rate_curve,
            current_ref_rate=current_ref_rate,
        )

    def i_spread(
        self,
        benchmark_curve: YieldCurveBase,
        discount_margin: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
        current_ref_rate: Optional[float] = None,
    ) -> float:
        """
        Calculate the I-spread of the bond relative to a benchmark yield curve.

        The I-spread is the difference between the bond's yield and the swap rate for the same maturity.

        The benchmark swap curve must be provided.

        I-spread = Bond YTM - Benchmark Swap Rate

        Parameters
        ----------
        benchmark_curve : YieldCurveBase, optional
            The benchmark yield curve to use for the I-spread calculation.
        discount_margin : float, optional
            Discount margin of the bond. Used to estimate if not set.
        price : float, optional
            Price of the bond. Used to estimate YTM if not set.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.
        ref_rate_curve : YieldCurveBase, optional
            Reference rate curve. If not provided, will use self.ref_rate_curve.
        current_ref_rate : float, optional
            Current reference rate. If not provided, will use self.current_ref_rate.

        Returns
        -------
        i_spread : float
            The I-spread in decimal (e.g., 0.0125 for 1.25%).

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', quoted_margin=0, cpn_freq=2, price=100, settlement_date="2020-01-01")
        >>> bond.i_spread(benchmark_curve=swap_curve) # doctest: +SKIP
        0.0185
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        benchmark_ytm = benchmark_curve.date_rate(
            date=self.maturity,
            yield_calculation_convention=yield_calculation_convention,
        )

        ytm = self.expected_yield_to_maturity(
            price=price,
            settlement_date=settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
            ref_rate_curve=ref_rate_curve,
            current_ref_rate=current_ref_rate,
        )

        return ytm - benchmark_ytm

    def g_spread(
        self,
        benchmark_ytm: Optional[float] = None,
        benchmark_curve: Optional[YieldCurveBase] = None,
        discount_margin: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
        current_ref_rate: Optional[float] = None,
    ) -> float:
        """
        Calculate the G-spread of the bond relative to a benchmark yield.

        The benchmark yield is the yield of a government bond that matches the maturity of the bond.

        If a benchmark curve is provided, the benchmark yield will be derived from the curve.

        G-spread = Bond YTM - Benchmark YTM

        Parameters
        ----------
        benchmark_ytm : float
            Yield to maturity of the government benchmark bond (in decimal, e.g., 0.03 for 3%).
        benchmark_curve : YieldCurveBase
            The benchmark yield curve to use for the G-spread calculation.
        discount_margin : float, optional
            Discount margin of the bond. Used to estimate YTM if not set.
        price : float, optional
            Price of the bond. Used to estimate YTM if not set.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.
        ref_rate_curve : YieldCurveBase, optional
            Reference rate curve. If not provided, will use self.ref_rate_curve.
        current_ref_rate : float, optional
            Current reference rate. If not provided, will use self.current_ref_rate.

        Returns
        -------
        g_spread : float
            The G-spread in decimal (e.g., 0.0125 for 1.25%).

        Examples
        --------
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', quoted_margin=0, cpn_freq=2, price=100, settlement_date="2020-01-01")
        >>> bond.g_spread(benchmark_ytm=0.03, price=100)
        np.float64(0.02)
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        if benchmark_ytm is None:
            if benchmark_curve is not None:
                benchmark_ytm = benchmark_curve.date_rate(
                    date=self.maturity,
                    yield_calculation_convention=yield_calculation_convention,
                )
            else:
                raise ValueError(
                    "Either benchmark_ytm or benchmark_curve must be provided."
                )

        ytm = self.expected_yield_to_maturity(
            price=price,
            settlement_date=settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
            ref_rate_curve=ref_rate_curve,
            current_ref_rate=current_ref_rate,
        )

        return round((ytm - benchmark_ytm), 10)


if __name__ == "__main__":  # pragma: no cover
    from pyfian.yield_curves.par_curve import ParCurve

    # Example usage
    # Par rates for different periods
    # 1-month	 4.49
    # 3-month	 4.32
    # 6-month	 4.14
    # 1-year	 3.95
    # 2-year	 3.79
    # 3-year	 3.75
    # 5-year	 3.86
    # 7-year	 4.07
    # 10-year	 4.33
    # 20-year	 4.89
    # 30-year	 4.92
    # Make dict of t and rates instances for each bond
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
    date = pd.Timestamp("2020-08-01")
    one_year_offset = date + pd.DateOffset(years=1)
    par_rates = {}

    for offset, cpn in list_maturities_rates:
        not_zero_coupon = date + offset > one_year_offset

        bond = {
            "cpn_freq": 2 if not_zero_coupon else 0,
            "cpn": cpn if not_zero_coupon else 0,
            "price": 100 if not_zero_coupon else None,
            "yield_to_maturity": None if not_zero_coupon else cpn / 100,
        }
        # self = bond
        par_rates[offset] = bond
    ref_rate_curve = ParCurve(curve_date="2020-08-01", par_rates=par_rates)

    floating_rate_note = FloatingRateNote(
        issue_dt="2020-01-01",
        maturity="2025-01-01",
        quoted_margin=100,
        cpn_freq=2,
        ref_rate_curve=ref_rate_curve,
        current_ref_rate=0.04,
    )
    floating_rate_note.yield_to_maturity(price=100, settlement_date="2020-08-01")
    floating_rate_note.required_margin(
        price=100, settlement_date="2020-08-01", ref_rate_curve=ref_rate_curve
    )

    ref_rate_curve = ParCurve(curve_date="2020-01-01", par_rates=par_rates)
    ref_rate_curve_BEY = ParCurve(
        curve_date="2020-01-01", par_rates=par_rates, yield_calculation_convention="BEY"
    )
    ref_rate_curve_flat_BEY = FlatCurveBEY(0.04, "2020-01-01")
    floating_rate_note.required_margin(
        price=100, settlement_date="2020-01-01", ref_rate_curve=ref_rate_curve_flat_BEY
    )

    floating_rate_note.required_margin(
        price=100, settlement_date="2020-01-01", ref_rate_curve=ref_rate_curve_BEY
    )

    ref_rate_curve_BEY = ParCurve(
        curve_date="2020-01-01",
        par_rates=par_rates,
        yield_calculation_convention="BEY",
        day_count_convention="30/360",
    )
    floating_rate_note = FloatingRateNote(
        issue_dt="2020-01-01",
        maturity="2025-01-01",
        quoted_margin=100,
        cpn_freq=2,
        ref_rate_curve=ref_rate_curve,
        current_ref_rate=0.0414,
    )
    floating_rate_note.required_margin(
        price=100, settlement_date="2020-01-01", ref_rate_curve=ref_rate_curve_BEY
    )

    # self = floating_rate_note
    # (settlement_date,
    # adjust_to_business_days,
    # day_count_convention,
    # following_coupons_day_count,
    # yield_calculation_convention,
    # current_ref_rate,
    # ref_rate_curve,
    # tol,
    # max_iter) = [None]*9
