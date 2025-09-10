"""
floating_rate_note.py

Module for fixed income floating rate note analytics, including FloatingRateNote class for payment flows,
valuation, and yield calculations. Adapted from FixedRateBullet.
"""

from collections import defaultdict
from typing import Optional, Union
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta  # type: ignore

from pyfian.fixed_income.base_fixed_income import BaseFixedIncomeInstrument
from pyfian.time_value import rate_conversions as rc
from pyfian.time_value.irr import xirr_base
from pyfian.time_value.rate_conversions import get_time_adjustment
from pyfian.utils.day_count import DayCountBase, get_day_count_convention
from pyfian.yield_curves.base_curve import YieldCurveBase


class FloatingRateNote(BaseFixedIncomeInstrument):
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
        yield_to_maturity: Optional[float] = None,
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
        if yield_to_maturity is not None:
            if self._settlement_date is None:
                raise ValueError(
                    "Settlement date must be set if yield to maturity is set."
                )
            self.set_yield_to_maturity(
                yield_to_maturity,
                settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                day_count_convention=day_count_convention,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
            )
        else:
            self._yield_to_maturity: Optional[float] = None
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
        elif yield_to_maturity is None:
            self._price: Optional[float] = None

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
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 1, notional=1000)
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
        last_spread = (spread) * notional

        dict_amortization[maturity] = notional
        dict_payments[maturity] = notional + last_spread

        dict_spreads[maturity] = last_spread
        next_date_processed = maturity - relativedelta(months=12 // cpn_freq)

        for i in range(2, ((maturity - issue_dt) / 365).days * cpn_freq + 3):
            if (next_date_processed - issue_dt).days < (365 * 0.99) // cpn_freq:
                break
            coupon_spread = (spread) * notional
            dict_payments[next_date_processed] = coupon_spread
            dict_spreads[next_date_processed] = coupon_spread
            dict_amortization[next_date_processed] = 0.0
            next_date_processed = maturity - relativedelta(months=12 // cpn_freq * i)

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

    def make_expected_coupon_flow(
        self,
        current_ref_rate: Optional[float] = None,
        ref_rate_curve: Optional[YieldCurveBase] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        #    adjust_to_business_days: Optional[bool] = None,
        #    day_count_convention: Optional[str | DayCountBase] = None,
        #    following_coupons_day_count: Optional[str | DayCountBase] = None,
        #    yield_calculation_convention: Optional[str] = None,
    ) -> dict[pd.Timestamp, float]:
        """
        Generate the expected coupon payment flow (cash flows) for the bond from the settlement date onwards.
        Uses the reference rate curve to estimate future reference rates for coupon calculations.

        Parameters
        ----------
        current_ref_rate : float, optional
            Current reference rate as a decimal. If not provided, will use self.current_ref_rate.
        ref_rate_curve : YieldCurveBase, optional
            Reference rate curve to use for estimating future rates. If not provided, will use self.ref_rate_curve.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.

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

        expected_coupon_flow = self.spread_flow.copy()

        # filter only expected payments after settlement date
        expected_coupon_flow = {
            date: spread
            for date, spread in expected_coupon_flow.items()
            if date > settlement_date
        }

        if current_ref_rate is None:
            if self.current_ref_rate is None:
                # extract the current reference rate from the curve at the settlement date
                if self.issue_dt == settlement_date:
                    current_ref_rate = ref_rate_curve.forward_dates(
                        start_date=settlement_date,
                        end_date=next(iter(expected_coupon_flow)),
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
        # Adjust expected coupon flow using reference rate curve and current reference rate
        for i, (date, spread) in enumerate(expected_coupon_flow.items()):
            if i == 0:
                expected_coupon_flow[date] = (
                    spread + (current_ref_rate / self.cpn_freq * self.notional)
                    if self.cpn_freq > 0
                    else 0
                )
            else:
                # Adjust the spread using the forward rate and current reference rate
                new_current_ref_rate = ref_rate_curve.forward_dates(last_date, date)
                new_current_ref_rate = rc.effective_to_nominal_periods(
                    new_current_ref_rate, periods_per_year=self.cpn_freq
                )
                expected_coupon_flow[date] = (
                    spread + (new_current_ref_rate / self.cpn_freq * self.notional)
                    if self.cpn_freq > 0
                    else 0
                )
            last_date = date

        return expected_coupon_flow

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

        Returns
        -------
        total_value : float
            Present value of the bond.
        pv : dict
            Dictionary of present values for each payment.

        Examples
        --------
        >>> from pyfian.yield_curves.flat_curve import FlatCurveBEY
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 1)
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

        date_of_payments = self._filter_payment_flow(
            settlement_date,
            price,
            payment_flow=self.payment_flow,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        pv = {
            d: curve.discount_date(d, spread) * value
            for d, value in date_of_payments.items()
        }
        return sum(pv.values()), pv

    def yield_to_maturity(
        self,
        price: float,
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
        price : float
            Price of the bond.
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
        >>> bond = FloatingRateNote('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.yield_to_maturity(price=95)
        np.float64(0.06100197251858131)
        """
        if tol is None:
            tol = 1e-6
        if max_iter is None:
            max_iter = 100
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
        # times_cashflows = self._calculate_time_to_payments(
        #     settlement_date,
        #     price,
        #     adjust_to_business_days=adjust_to_business_days,
        #     following_coupons_day_count=following_coupons_day_count,
        #     yield_calculation_convention=yield_calculation_convention,
        #     day_count_convention=day_count_convention,
        # )
        dated_payment_flow = self.make_expected_coupon_flow(
            settlement_date=settlement_date,
            ref_rate_curve=ref_rate_curve,
            current_ref_rate=current_ref_rate,
        )
        dated_payment_flow[
            settlement_date
        ] = -price  # Initial cash flow (negative for purchase)
        for dt, amt in self.amortization_flow.items():
            if dt in dated_payment_flow:
                dated_payment_flow[dt] += amt
            else:
                dated_payment_flow[dt] = amt

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

    def modified_duration(
        self,
        yield_to_maturity: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> float:
        """
        Calculate modified duration of the bond.

        .. math::
            Modified Duration = \\frac{1}{P} \\sum_{t=1}^{T} \\frac{C_t}{(1 + YTM)^{(t+1)}} \\cdot t
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
        duration : float
            Modified duration in years.

        Examples
        --------
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 2)
        >>> bond.effective_duration(yield_to_maturity=0.05, settlement_date='2020-01-01')
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
            yield_to_maturity,
            price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        time_to_payments = self._calculate_time_to_payments(
            settlement_date,
            price=None,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        time_adjustment = get_time_adjustment(yield_calculation_convention)

        if ytm is None or price_calc is None:
            raise ValueError(
                "Unable to resolve yield to maturity. You must input settlement_date and either yield_to_maturity or price. Previous information was not available."
            )

        if yield_calculation_convention == "Continuous":
            duration = sum(
                [t * cf * np.exp(-ytm * t) for t, cf in time_to_payments.items()]
            )
        else:
            duration = sum(
                [
                    t * cf / (1 + ytm / time_adjustment) ** (t * time_adjustment + 1)
                    for t, cf in time_to_payments.items()
                ]
            )
        return round(duration / price_calc if price_calc != 0 else 0.0, 10)

    def macaulay_duration(
        self,
        yield_to_maturity: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> float:
        """
        Calculate macaulay duration of the bond.


        .. math::
            Macaulay Duration = \\frac{1}{P} \\sum_{t=1}^{T} \\frac{C_t}{(1 + YTM)^{(t)}} \\cdot t
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
        duration : float
            Macaulay duration in years.

        Examples
        --------
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 2)
        >>> bond.macaulay_duration(yield_to_maturity=0.05)
        4.4854327646
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
            yield_to_maturity,
            price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        time_to_payments = self._calculate_time_to_payments(
            settlement_date,
            price=None,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        time_adjustment = get_time_adjustment(yield_calculation_convention)

        if ytm is None or price_calc is None:
            raise ValueError(
                "Unable to resolve yield to maturity. You must input settlement_date and either yield_to_maturity or price. Previous information was not available."
            )

        duration = sum(
            [
                t * cf / (1 + ytm / time_adjustment) ** (t * time_adjustment)
                for t, cf in time_to_payments.items()
            ]
        )
        return round(duration / price_calc if price_calc != 0 else 0.0, 10)

    def convexity(
        self,
        yield_to_maturity: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> float:
        """
        Calculate the convexity of the bond.



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
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 2)
        >>> bond.convexity(yield_to_maturity=0.05)
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
            yield_to_maturity,
            price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        time_to_payments = self._calculate_time_to_payments(
            settlement_date,
            price=None,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        time_adjustment = get_time_adjustment(yield_calculation_convention)

        if ytm is None or price_calc is None:
            raise ValueError(
                "Unable to resolve yield to maturity. You must input settlement_date and either yield_to_maturity or price. Previous information was not available."
            )

        if yield_calculation_convention == "Continuous":
            convexity = sum(
                [cf * t**2 * np.exp(-ytm * t) for t, cf in time_to_payments.items()]
            )
        else:
            convexity = sum(
                [
                    cf
                    * t
                    * time_adjustment
                    * (t * time_adjustment + 1)
                    / (1 + ytm / time_adjustment) ** (t * time_adjustment + 2)
                    for t, cf in time_to_payments.items()
                ]
            )
        return (
            round(convexity / price_calc / time_adjustment**2, 10)
            if price_calc != 0
            else 0.0
        )

    def accrued_interest(
        self, settlement_date: Optional[Union[str, pd.Timestamp]] = None
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

        Returns
        -------
        accrued : float
            Accrued interest amount.

        Examples
        --------
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.accrued_interest('2024-07-02')
        2.5
        """
        settlement_date = self._resolve_settlement_date(settlement_date)

        if self.cpn_freq == 0 or self.current_ref_rate is None:
            return 0.0
        if self.current_ref_rate is None:
            raise ValueError(
                "Current reference rate must be provided to calculate accrued interest."
            )

        prev_coupon: pd.Timestamp = self.previous_coupon_date(settlement_date)
        next_coupon: pd.Timestamp = self.next_coupon_date(settlement_date)

        self.current_ref_rate
        coupon = (self.current_ref_rate + self.quoted_margin) * self.notional / 100

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
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 1)
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
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 1)
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
        Return string representation of the FixedRateBullet object.

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
            f"quoted_margin={self.quoted_margin}, cpn_freq={self.cpn_freq})"
        )

    def _price_from_yield(
        self,
        time_to_payments: dict[float, float],
        yield_to_maturity: float,
        yield_calculation_convention: str,
    ) -> float:
        """
        Helper to calculate the price of the bond from yield to maturity and time to payments.
        Parameters
        ----------
        time_to_payments : dict
            Dictionary with time to payment (in years) as keys and cash flow values.
        yield_to_maturity : float
            Yield to maturity as a decimal (e.g., 0.05 for 5%).
        yield_calculation_convention : str
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.

        Returns
        -------
        float
            Price of the bond.
        """
        time_adjustment = get_time_adjustment(yield_calculation_convention)

        if yield_calculation_convention == "Continuous":
            price = sum(
                [
                    cf * np.exp(-yield_to_maturity * t)
                    for t, cf in time_to_payments.items()
                ]
            )
        else:
            price = sum(
                [
                    cf
                    / (1 + yield_to_maturity / time_adjustment) ** (t * time_adjustment)
                    for t, cf in time_to_payments.items()
                ]
            )
        return price

    def _price_from_yield_and_clean_parameters(
        self,
        yield_to_maturity: float,
        settlement_date: Optional[Union[str, pd.Timestamp]],
        adjust_to_business_days: bool,
        following_coupons_day_count: DayCountBase,
        yield_calculation_convention: str,
        day_count_convention: DayCountBase,
    ) -> float:
        time_to_payments = self._calculate_time_to_payments(
            settlement_date,
            price=None,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        return self._price_from_yield(
            time_to_payments,
            yield_to_maturity,
            yield_calculation_convention=yield_calculation_convention,
        )


if __name__ == "__main__":
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
