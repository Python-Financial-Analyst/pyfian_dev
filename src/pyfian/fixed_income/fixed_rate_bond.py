"""
bond.py

Module for fixed income bond analytics, including FixedRateBullet class for payment flows,
valuation, and yield calculations.
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


class FixedRateBullet(BaseFixedIncomeInstrument):
    """
    FixedRateBullet represents a bullet bond with fixed coupon payments and principal at maturity.
    It allows for payment flow generation, valuation, yield calculations, and other bond analytics.

    Parameters
    ----------
    issue_dt : str or datetime-like
        Issue date of the bond.
    maturity : str or datetime-like
        Maturity date of the bond.
    cpn : float
        Annual coupon rate (percentage).
    cpn_freq : int
        Number of coupon payments per year.
    notional : float, optional
        Face value (principal) of the bond. Defaults to 100.
    settlement_convention_t_plus : int, optional
        Settlement convention. How many days after trade date the payment is made, e.g., T+1.
        Defaults to 1.
    record_date_t_minus : int, optional
        Record date convention. How many days before the coupon payment is made to receive it.
        If 1, you receive the payment if you had settled the trade 1 day before coupon payment.
        Defaults to 1.
    settlement_date : str or datetime-like, optional
        Settlement date for the bond. Defaults to None.
    yield_to_maturity : float, optional
        Yield to maturity of the bond. Set in decimal, e.g., 0.05 for 5%. Defaults to None.
    bond_price : float, optional
        Market price of the bond. Defaults to None.
    adjust_to_business_days : bool, optional
        Whether to adjust dates to business days. Defaults to False.
    day_count_convention : str, optional
        Day count convention for the bond. Defaults to 'actual/actual-Bond'.
        It is used to calculate the day count fraction for accrued interests and time to payments.
        Supported conventions: '30/360', '30e/360', 'actual/actual', 'actual/360', 'actual/365', '30/365', 'actual/actual-Bond'.
    following_coupons_day_count : str, optional
        Day count convention for the following coupons. Defaults to '30/360', to match the common convention for bonds.
        Convention "actual/365" might be the more relevant for Effective Annual Yield or Continuous Compounding.
    yield_calculation_convention : str, optional
        Yield convention for the bond yield calculation. By default, it is "BEY" (Bond Equivalent Yield).
        Other options are "Annual" or "Continuous".

    Raises
    ------
    ValueError
        If any of the input parameters are invalid.

    Attributes
    ----------
    issue_dt : pd.Timestamp
        Issue date of the bond.
    maturity : pd.Timestamp
        Maturity date of the bond.
    cpn : float
        Annual coupon rate (percentage).
    cpn_freq : int
        Number of coupon payments per year.
    notional : float
        Face value (principal) of the bond.
    settlement_convention_t_plus : int
        Settlement convention (T+).
    record_date_t_minus : int
        Record date convention (T-).
    settlement_date : pd.Timestamp
        Settlement date for the bond.
    yield_to_maturity : float
        Yield to maturity of the bond.
    bond_price : float
        Market price of the bond.
    payment_flow : dict[pd.Timestamp, float]
        Payment flow schedule for the bond.
    coupon_flow : dict[pd.Timestamp, float]
        Coupon payment schedule for the bond.
    amortization_flow : dict[pd.Timestamp, float]
        Amortization payment schedule for the bond.
    adjust_to_business_days : bool
        Whether to adjust dates to business days by default.
        If True, dates will be adjusted to the nearest business day.
    day_count_convention : DayCountBase
        Day count convention function for the bond.
    following_coupons_day_count : DayCountBase
        Day count convention for the following coupons. Defaults to '30/360', to match the common convention for bonds.
        Convention "actual/365" might be the more relevant for Effective Annual Yield or Continuous Compounding.
    yield_calculation_convention : str
        Yield convention for the bond yield calculation. By default, it is "BEY" (Bond Equivalent Yield).
        Other options are "Annual" or "Continuous".

    Examples
    --------
    >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 1, notional=1000)
    >>> bond.payment_flow # doctest: +SKIP
    {Timestamp('2025-01-01 00:00:00'): 1050.0, Timestamp('2024-01-01 00:00:00'): 50.0, ...}
    """

    def __init__(
        self,
        issue_dt: Union[str, pd.Timestamp],
        maturity: Union[str, pd.Timestamp],
        cpn: float,
        cpn_freq: int,
        notional: float = 100,
        settlement_convention_t_plus: int = 1,
        record_date_t_minus: int = 1,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        yield_to_maturity: Optional[float] = None,
        bond_price: Optional[float] = None,
        adjust_to_business_days: bool = False,
        day_count_convention: str | DayCountBase = "actual/actual-Bond",
        following_coupons_day_count: str | DayCountBase = "30/360",
        yield_calculation_convention: str = "BEY",
    ) -> None:
        # Input validation
        if cpn_freq < 0:
            raise ValueError("Coupon frequency must be greater or equal to zero.")
        # If coupon is positive, the coupon frequency must be greater than 0
        if cpn > 0 and cpn_freq <= 0:
            raise ValueError(
                "Coupon frequency must be greater than zero for positive coupons."
            )

        if notional < 0:
            raise ValueError("Notional (face value) cannot be negative.")
        if cpn < 0:
            raise ValueError("Coupon rate cannot be negative.")
        if settlement_convention_t_plus < 0:
            raise ValueError("Settlement convention (T+) cannot be negative.")
        if record_date_t_minus < 0:
            raise ValueError("Record date (T-) cannot be negative.")

        # Convert dates for validation
        _issue_dt = pd.to_datetime(issue_dt)
        _maturity = pd.to_datetime(maturity)
        if _maturity < _issue_dt:
            raise ValueError("Maturity date cannot be before issue date.")
        if settlement_date is not None:
            _settlement_date = pd.to_datetime(settlement_date)
            if _settlement_date < _issue_dt:
                raise ValueError("Settlement date cannot be before issue date.")

        self.issue_dt: pd.Timestamp = pd.to_datetime(issue_dt)
        self.maturity: pd.Timestamp = pd.to_datetime(maturity)
        self.cpn: float = cpn
        self.cpn_freq: int = cpn_freq
        self.notional: float = notional
        self.settlement_convention_t_plus: int = settlement_convention_t_plus
        self.record_date_t_minus: int = record_date_t_minus

        # Raise if day_count_convention is neither str nor DayCountBase
        if not isinstance(day_count_convention, (str, DayCountBase)):
            raise TypeError(
                "day_count_convention must be either a string or a DayCountBase instance."
            )

        # Initialize day count convention, defaulting to 'actual/actual-Bond'
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

        dict_payments, dict_coupons, dict_amortization = self.make_payment_flow()
        self.payment_flow: dict[pd.Timestamp, float] = dict_payments
        self.coupon_flow: dict[pd.Timestamp, float] = dict_coupons
        self.amortization_flow: dict[pd.Timestamp, float] = dict_amortization

        # Initialize settlement date, yield to maturity, and bond price
        self._settlement_date: Optional[pd.Timestamp] = None
        self._validate_bond_price(bond_price=bond_price)

        if settlement_date is not None:
            self.set_settlement_date(
                settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                day_count_convention=day_count_convention,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
            )

        if yield_to_maturity is not None:
            # Throw error if yield_to_maturity is not None and settlement_date is None
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

        if bond_price is not None:
            # Throw error if bond_price is not None and settlement_date is None
            if self._settlement_date is None:
                raise ValueError("Settlement date must be set if bond_price is set.")
            if yield_to_maturity is not None:
                # Check if self._bond_price is approximately equal to the bond_price, else raise ValueError
                if (
                    getattr(self, "_bond_price", None) is not None
                    and abs(self._bond_price - bond_price) / self._bond_price > 1e-5
                ):
                    raise ValueError(
                        "Bond price calculated by yield to maturity does not match the current bond price."
                        f" (calculated: {self._bond_price}, given: {bond_price})"
                    )
            self.set_bond_price(
                bond_price,
                settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
            )
        elif yield_to_maturity is None:
            # If neither yield_to_maturity nor bond_price is set, set bond price to None
            self._bond_price: Optional[float] = None

    def _validate_yield_calculation_convention(
        self, yield_calculation_convention: str
    ) -> str:
        """
        Validate the yield calculation convention.
        Raises ValueError if the convention is not supported.
        """
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
            following_coupons_day_count = following_coupons_day_count
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
        * dict_coupons: Coupon payment dates as keys and coupon amounts as values.
        * dict_amortization: Amortization payment dates as keys and amortization amounts as values.

        Returns
        -------
        dict_payments : dict
            Dictionary with payment dates as keys and cash flow amounts as values.
        dict_coupons : dict
            Dictionary with coupon payment dates as keys and coupon amounts as values.
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
        issue_dt, maturity, cpn, cpn_freq, notional = (
            self.issue_dt,
            self.maturity,
            self.cpn,
            self.cpn_freq,
            self.notional,
        )
        dict_payments = {}
        dict_coupons = {}
        dict_amortization = {}

        # Final payment: principal + last coupon
        last_coupon = (cpn / cpn_freq) * notional / 100 if cpn > 0 else 0
        dict_payments[maturity] = notional + last_coupon
        dict_amortization[maturity] = notional

        if cpn > 0:
            dict_coupons[maturity] = last_coupon
            next_date_processed = maturity - relativedelta(months=12 // cpn_freq)

            for i in range(2, ((maturity - issue_dt) / 365).days * cpn_freq + 3):
                if (next_date_processed - issue_dt).days < (365 * 0.99) // cpn_freq:
                    break
                coupon = (cpn / cpn_freq) * notional / 100
                dict_payments[next_date_processed] = coupon
                dict_coupons[next_date_processed] = coupon
                dict_amortization[next_date_processed] = 0.0
                next_date_processed = maturity - relativedelta(
                    months=12 // cpn_freq * i
                )

        # Sort the payment dates
        dict_payments = dict(sorted(dict_payments.items()))
        dict_coupons = dict(sorted(dict_coupons.items()))
        dict_amortization = dict(sorted(dict_amortization.items()))
        return dict_payments, dict_coupons, dict_amortization

    def _calculate_time_to_payments(
        self,
        settlement_date,
        bond_price,
        adjust_to_business_days,
        following_coupons_day_count,
        yield_calculation_convention,
        day_count_convention,
    ) -> dict[float, float]:
        """Calculate the time to each payment from the settlement date."""
        flows = self._filter_payment_flow(
            settlement_date,
            bond_price,
            payment_flow=self.payment_flow,
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
            (key for key in time_to_payments_keys if flows[key] > 0), None
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
            times_key = (
                following_coupons_day_count.fraction(
                    start=start,
                    current=key,
                )
                - time_to_first_non_negative_key / cpn_freq
            )
            times[times_key] += flows[key]

        return dict(times)

    def value_with_curve(
        self,
        curve: YieldCurveBase,
        spread: float = 0,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        bond_price: Optional[float] = None,
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
        bond_price : float, optional
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
            bond_price,
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
        bond_price: float,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
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
        bond_price : float
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
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.yield_to_maturity(bond_price=95)
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
        times_cashflows = self._calculate_time_to_payments(
            settlement_date,
            bond_price,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        times = list(times_cashflows.keys())
        payment_flow = list(times_cashflows.values())

        time_adjustment = get_time_adjustment(yield_calculation_convention)

        # Multiply all times by the coupon frequency to convert to BEY
        times = [t * time_adjustment for t in times]
        initial_guess = self.cpn / 100 / time_adjustment if self.cpn > 0 else 0.05

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
        bond_price: Optional[float] = None,
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
            Yield to maturity as a decimal. If not provided, will be calculated from bond_price if given.
        bond_price : float, optional
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

        ytm, price_calc = self._resolve_ytm_and_bond_price(
            yield_to_maturity,
            bond_price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        time_to_payments = self._calculate_time_to_payments(
            settlement_date,
            bond_price=None,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        time_adjustment = get_time_adjustment(yield_calculation_convention)

        if ytm is None or price_calc is None:
            raise ValueError(
                "Unable to resolve yield to maturity. You must input settlement_date and either yield_to_maturity or bond_price. Previous information was not available."
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
        bond_price: Optional[float] = None,
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
            Yield to maturity as a decimal. If not provided, will be calculated from bond_price if given.
        bond_price : float, optional
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

        ytm, price_calc = self._resolve_ytm_and_bond_price(
            yield_to_maturity,
            bond_price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        time_to_payments = self._calculate_time_to_payments(
            settlement_date,
            bond_price=None,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        time_adjustment = get_time_adjustment(yield_calculation_convention)

        if ytm is None or price_calc is None:
            raise ValueError(
                "Unable to resolve yield to maturity. You must input settlement_date and either yield_to_maturity or bond_price. Previous information was not available."
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
        bond_price: Optional[float] = None,
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
        bond_price : float, optional
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

        ytm, price_calc = self._resolve_ytm_and_bond_price(
            yield_to_maturity,
            bond_price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        time_to_payments = self._calculate_time_to_payments(
            settlement_date,
            bond_price=None,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        time_adjustment = get_time_adjustment(yield_calculation_convention)

        if ytm is None or price_calc is None:
            raise ValueError(
                "Unable to resolve yield to maturity. You must input settlement_date and either yield_to_maturity or bond_price. Previous information was not available."
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

        if self.cpn_freq == 0 or self.cpn == 0:
            return 0.0

        prev_coupon: pd.Timestamp = self.previous_coupon_date(settlement_date)
        next_coupon: pd.Timestamp = self.next_coupon_date(settlement_date)
        coupon = (self.cpn) * self.notional / 100

        # If before first coupon, accrue from issue date
        if prev_coupon is None and next_coupon is not None:
            # TODO: Handle day count convention for calculating accrued interest
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
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 1)
        >>> print(bond)
        FixedRateBullet(issue_dt=2020-01-01 00:00:00, maturity=2025-01-01 00:00:00, cpn=5, cpn_freq=1)
        """
        return (
            f"FixedRateBullet(issue_dt={self.issue_dt}, maturity={self.maturity}, "
            f"cpn={self.cpn}, cpn_freq={self.cpn_freq})"
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
            bond_price=None,
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
