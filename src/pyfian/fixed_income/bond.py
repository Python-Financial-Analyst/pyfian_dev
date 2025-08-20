"""
bond.py

Module for fixed income bond analytics, including BulletBond class for payment flows,
valuation, and yield calculations.
"""

from collections import defaultdict
from typing import Optional, Union

import pandas as pd
import matplotlib.pyplot as plt
from dateutil.relativedelta import relativedelta  # type: ignore
from scipy import optimize  # type: ignore

from pyfian.time_value.irr import xirr_base
from pyfian.utils.day_count import DayCountBase, get_day_count_convention
from pyfian.yield_curves.base_curve import YieldCurveBase


class BulletBond:
    """
    BulletBond represents a bullet bond with fixed coupon payments and principal at maturity.
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
        Other option is "Annual".

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
        Other option is "Annual".

    Examples
    --------
    >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1, notional=1000)
    >>> bond.payment_flow
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
        dict_payments, dict_coupons, dict_amortization = self.make_payment_flow()
        self.payment_flow: dict[pd.Timestamp, float] = dict_payments
        self.coupon_flow: dict[pd.Timestamp, float] = dict_coupons
        self.amortization_flow: dict[pd.Timestamp, float] = dict_amortization

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

        self.yield_calculation_convention: str = yield_calculation_convention

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

    def _resolve_valuation_parameters(
        self,
        adjust_to_business_days: Optional[bool],
        day_count_convention: Optional[str | DayCountBase],
        following_coupons_day_count: Optional[str | DayCountBase],
        yield_calculation_convention: Optional[str],
    ) -> tuple[bool, DayCountBase, DayCountBase, str]:
        if adjust_to_business_days is None:
            adjust_to_business_days = self.adjust_to_business_days
        if day_count_convention is None:
            day_count_convention = self.day_count_convention
        elif isinstance(day_count_convention, str):
            day_count_convention = get_day_count_convention(day_count_convention)
        if following_coupons_day_count is None:
            following_coupons_day_count = self.following_coupons_day_count
        else:
            following_coupons_day_count = self._validate_following_coupons_day_count(
                following_coupons_day_count
            )
        if yield_calculation_convention is None:
            yield_calculation_convention = self.yield_calculation_convention

        return (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

    def set_settlement_date(
        self,
        settlement_date: Optional[Union[str, pd.Timestamp]],
        reset_yield_to_maturity: bool = True,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> pd.Timestamp:
        """
        Set the default settlement date for the bond.
        If reset_yield_to_maturity is True, resets the yield to maturity and bond price.

        Parameters
        ----------
        settlement_date : Union[str, pd.Timestamp], optional
            The settlement date to set.
        reset_yield_to_maturity : bool, optional
            Whether to reset the yield to maturity and bond price.
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
                self._bond_price = None
                if reset_yield_to_maturity:
                    self._yield_to_maturity = None
                else:
                    # If not resetting YTM, ensure it is still valid
                    if self._yield_to_maturity is not None:
                        self._bond_price = self.price_from_yield(
                            self._yield_to_maturity,
                            settlement_date,
                            adjust_to_business_days=adjust_to_business_days,
                            day_count_convention=day_count_convention,
                            following_coupons_day_count=following_coupons_day_count,
                            yield_calculation_convention=yield_calculation_convention,
                        )

            self._settlement_date = pd.to_datetime(settlement_date)
        else:
            self._settlement_date = None
            # If no settlement date is set, reset bond price and YTM
            self._bond_price = None
            self._yield_to_maturity = None
        return self._settlement_date

    def set_yield_to_maturity(
        self,
        ytm: Optional[float],
        settlement_date: Optional[Union[str, pd.Timestamp, None]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> None:
        """
        Set the default yield to maturity for the bond. Updates bond price accordingly.

        Parameters
        ----------
        ytm : float, optional
            The yield to maturity to set.
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

        Raises
        ------
        ValueError
            If the settlement date is not set when the yield to maturity is set.

        If the yield to maturity is set, it will also update the bond price based on the yield.
        """
        self._yield_to_maturity = ytm
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
        # Since ytm is set, update bond price
        if ytm is not None:
            vdate = self._settlement_date
            if vdate is None:
                raise ValueError(
                    "Settlement date must be set since there is no default settlement_date for the bond."
                )
            self._bond_price = self.price_from_yield(
                ytm,
                vdate,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                day_count_convention=day_count_convention,
            )
        else:
            # If no yield to maturity is set, reset bond price and yield to maturity
            self._bond_price = None
            self._yield_to_maturity = None

    def _validate_bond_price(self, bond_price: Optional[float]) -> None:
        """
        Validate the bond price.
        Raises ValueError if the bond price is negative.
        """
        if bond_price is not None and bond_price < 0:
            raise ValueError("Bond price cannot be negative.")

    def set_bond_price(
        self,
        bond_price: Optional[float],
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> None:
        """
        Set the default bond price for the bond. Updates yield to maturity accordingly.

        Parameters
        ----------
        bond_price : float, optional
            The bond price to set.
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

        Raises
        ------
        ValueError
            If the settlement date is not set when the bond price is set.

        If the bond price is set, it will also update the yield to maturity based on the bond price.
        """
        self._validate_bond_price(bond_price=bond_price)
        self._bond_price = bond_price
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
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                day_count_convention=day_count_convention,
            )

        # Since bond price is set, update yield to maturity
        if bond_price is not None:
            vdate = self._settlement_date
            if vdate is None:
                raise ValueError(
                    "Settlement date must be set since there is no default settlement_date for the bond."
                )
            self._yield_to_maturity = self.yield_to_maturity(
                bond_price,
                vdate,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                day_count_convention=day_count_convention,
            )
        else:
            # If no bond price is set, reset yield to maturity and bond price
            self._bond_price = None
            self._yield_to_maturity = None

    def get_settlement_date(self) -> Optional[pd.Timestamp]:
        """
        Get the current settlement date for the bond.
        Returns
        -------
        Optional[pd.Timestamp]
            The current settlement date, or None if not set.
        """
        return self._settlement_date

    def get_yield_to_maturity(self) -> Optional[float]:
        """
        Get the current yield to maturity for the bond.
        Returns
        -------
        Optional[float]
            The current yield to maturity, or None if not set.
        """
        return self._yield_to_maturity

    def get_bond_price(self) -> Optional[float]:
        """
        Get the current bond price for the bond.
        Returns
        -------
        Optional[float]
            The current bond price, or None if not set.
        """
        return self._bond_price

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
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1, notional=1000)
        >>> bond.make_payment_flow()
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

    def filter_payment_flow(
        self,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        bond_price: Optional[float] = None,
        payment_flow: Optional[dict[pd.Timestamp, float]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> dict[pd.Timestamp, float]:
        """
        Filter the payment flow to include only payments after the settlement date.

        If a bond price is provided, it is added as a negative cash flow at the settlement date.

        The settlement date is resolved to a pd.Timestamp, and if it is not provided, it defaults to the issue date.

        The function returns a dictionary of payment dates and cash flows that occur after the settlement date.
        If `adjust_to_business_days` is True (default: value of self.adjust_to_business_days), payment dates are adjusted to business days.

        Parameters
        ----------
        settlement_date : str or datetime-like, optional
            Date from which to consider future payments. Defaults to issue date.
        bond_price : float, optional
            If provided, adds the bond price as a negative cash flow at the settlement date.
        payment_flow : dict, optional
            Dictionary of payment dates and cash flows. If not provided, uses the bond's payment flow.
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
        cash_flows : dict
            Dictionary of filtered payment dates and cash flows.

        Examples
        --------
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.filter_payment_flow('2022-01-01')
        {Timestamp('2023-01-01 00:00:00'): 5.0, Timestamp('2024-01-01 00:00:00'): 5.0,
        Timestamp('2025-01-01 00:00:00'): 105.0}
        """
        maturity = self.maturity
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

        if payment_flow is None:
            payment_flow = self.payment_flow

        settlement_date = self._resolve_settlement_date(settlement_date)

        self._validate_bond_price(bond_price)

        if adjust_to_business_days:

            def business_days_adjustment(x):
                return x - pd.offsets.BDay(1) + pd.offsets.BDay(1)
        else:

            def business_days_adjustment(x):
                return x

        # If settlement date would be after maturity, there are no cash flows
        if settlement_date > business_days_adjustment(maturity):
            return {}
        cash_flows = {}

        # If a bond_price is provided, add it as a negative cash flow
        if bond_price is not None:
            cash_flows[settlement_date] = -bond_price

        # Include all payments after the settlement date
        cash_flows.update(
            {
                business_days_adjustment(pd.to_datetime(key)): value
                for key, value in payment_flow.items()
                if (
                    settlement_date + pd.offsets.BDay(self.record_date_t_minus)
                    <= business_days_adjustment(pd.to_datetime(key))
                )
                or (pd.to_datetime(key) == maturity and (settlement_date <= key))
            }
        )
        return cash_flows

    def calculate_time_to_payments(
        self,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        bond_price: Optional[float] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> dict[float, float]:
        """
        Calculate the time to each payment from the settlement date.
        The time is expressed in years.

        .. math::
            T = \\frac{D - S}{365}

        for each payment :math:`D` and settlement date :math:`S`

        where:

        - :math:`T` is the time to payment (in years)
        - :math:`D` is the payment date
        - :math:`S` is the settlement date

        Parameters
        ----------
        settlement_date : str or datetime-like, optional
            Date from which to calculate time to payments. Defaults to issue date.
        bond_price : float, optional
            If provided, adds bond price as a negative cash flow.
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
        dict
            Dictionary with time to payment (in years) as keys and cash flow values.

        Examples
        --------
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 2)
        >>> bond.calculate_time_to_payments('2022-01-01')
        {1.0: 5.0, 2.0: 5.0, 3.0: 105.0}
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

        flujos = self.filter_payment_flow(
            settlement_date,
            bond_price,
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

        time_to_payments_keys = sorted(flujos.keys())
        first_non_negative_key = next(
            (key for key in time_to_payments_keys if flujos[key] > 0), None
        )

        time_to_first_non_negative_key = day_count_convention.fraction_period_adjusted(
            start=start,
            current=settlement_date,
            end=first_non_negative_key,
            periods_per_year=self.cpn_freq,
        )

        times: defaultdict[float, float] = defaultdict(float)

        for key in time_to_payments_keys:
            times_key = (
                following_coupons_day_count.fraction(
                    start=start,
                    current=key,
                )
                - time_to_first_non_negative_key / self.cpn_freq
            )
            times[times_key] += flujos[key]

        return dict(times)

    def value_with_curve(
        self,
        curve: YieldCurveBase,
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

        The curve should have a method `discount_t(t)` that returns the discount factor for a given time `t` expressed in years from the settlement date.

        The discount factor is typically calculated as:

        .. math::
            discount_t(t) = \\frac{1}{(1 + r(t))^t}

        where:

        - :math:`r(t)` is the discount rate at time :math:`t`.

        The discount factor brings the future value back to the present. Using this discount factor, we can calculate the present value of future cash flows by discounting them back to the settlement date.

        For a set of cash flows :math:`C(t)` at times :math:`t`, the present value (PV) is calculated as:

        .. math::
            PV = \\sum_{i}^{N} C(t_i) * discount_t(t_i)

        for each (:math:`t_i`, :math:`C(t_i)`) cash flow, where :math:`i = 1, ..., N`

        where:

        - :math:`PV` is the present value of the cash flows
        - :math:`C(t)` is the cash flow at time :math:`t`
        - :math:`N` is the total number of cash flows
        - :math:`r(t)` is the discount rate at time :math:`t`.

        The discount rate for a cash flow at time :math:`t` is obtained from the discount curve using `curve.discount_t(t)`.

        This can be used to optimize the yield curve fitting process.

        Parameters
        ----------
        curve : object
            Discount curve object with a discount_t(t) method.
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
        >>> class DummyCurve:
        ...     def discount_t(self, t):
        ...         return 1 / (1 + 0.05 * t)
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.value_with_curve(DummyCurve())
        (value, {t1: pv1, t2: pv2, ...})
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

        time_to_payments = self.calculate_time_to_payments(
            settlement_date,
            bond_price,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        pv = {t: curve.discount_t(t) * value for t, value in time_to_payments.items()}
        return sum(pv.values()), pv

    def g_spread(
        self,
        benchmark_ytm: Optional[float] = None,
        benchmark_curve: Optional[YieldCurveBase] = None,
        yield_to_maturity: Optional[float] = None,
        bond_price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
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
        yield_to_maturity : float, optional
            Yield to maturity of the bond. Used to estimate YTM if not set.
        bond_price : float, optional
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

        Returns
        -------
        g_spread : float
            The G-spread in decimal (e.g., 0.0125 for 1.25%).

        Examples
        --------
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.g_spread(benchmark_ytm=0.03, bond_price=102)
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

        ytm = self._resolve_ytm(
            yield_to_maturity,
            bond_price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        return ytm - benchmark_ytm

    def i_spread(
        self,
        benchmark_curve: YieldCurveBase,
        yield_to_maturity: Optional[float] = None,
        bond_price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
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
        yield_to_maturity : float, optional
            Yield to maturity of the bond. Used to estimate YTM if not set.
        bond_price : float, optional
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

        Returns
        -------
        i_spread : float
            The I-spread in decimal (e.g., 0.0125 for 1.25%).

        Examples
        --------
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.i_spread(benchmark_curve=swap_curve)
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

        ytm = self._resolve_ytm(
            yield_to_maturity,
            bond_price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        return ytm - benchmark_ytm

    def z_spread(
        self,
        benchmark_curve: YieldCurveBase,
        yield_to_maturity: Optional[float] = None,
        bond_price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> float:
        """
        Calculate the Z-spread of the bond relative to a benchmark yield curve.

        The Z-spread is the constant spread that, when added to the benchmark yield curve, makes the present value of the bond's cash flows equal to its market price.

        The benchmark curve must be provided.

        The Z-spread is calculated by solving the equation:

        .. math::
            P = \\sum_{t=1}^{T} \\frac{C_t}{(1 + YTM + Z)^{(t+1)}}

        where:

        - :math:`P` is the price of the bond
        - :math:`C_t` is the cash flow at time :math:`t`, where :math:`t` is the time in years from the settlement date
        - :math:`YTM` is the yield to maturity
        - :math:`T` is the total number of periods
        - :math:`Z` is the Z-spread

        The times to payments are calculated from the settlement date to each payment date and need not be integer values.

        Parameters
        ----------
        benchmark_curve : YieldCurveBase, optional
            The benchmark yield curve to use for the Z-spread calculation.
        yield_to_maturity : float, optional
            Yield to maturity of the bond. Used to estimate YTM if not set.
        bond_price : float, optional
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

        Returns
        -------
        z_spread : float
            The Z-spread in decimal (e.g., 0.0125 for 1.25%).

        Examples
        --------
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 2)
        >>> bond.z_spread(benchmark_curve=FlatCurveBEY(0.05, '2020-01-01'))
        0.0
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

        # benchmark_ytm = benchmark_curve.date_rate(date=self.maturity, yield_calculation_convention=yield_calculation_convention)
        ytm, time_to_payments, price_calc = self._get_ytm_payments_price(
            yield_to_maturity,
            bond_price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        def _price_difference(z_spread):
            return (
                sum(
                    benchmark_curve.discount_t(t, z_spread) * value
                    for t, value in time_to_payments.items()
                )
                - price_calc
            )

        # use scipy to target _price_difference equal to 0
        z_spread = optimize.root_scalar(_price_difference, x0=0, method="newton").root

        return z_spread.root

    def yield_to_maturity(
        self,
        bond_price: float,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        tol: float = 1e-6,
        max_iter: int = 100,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
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
        tol : float, optional
            Tolerance for convergence (default is 1e-6).
        max_iter : int, optional
            Maximum number of iterations (default is 100).
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
        ytm : float
            Estimated yield to maturity as a decimal.

        Raises
        ------
        ValueError
            If bond price is not set or YTM calculation does not converge.

        Examples
        --------
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.yield_to_maturity(bond_price=95)
        0.06189544078
        """
        # Prepare cash flows and dates
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
        times_cashflows = self.calculate_time_to_payments(
            settlement_date,
            bond_price,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        times = list(times_cashflows.keys())
        payment_flow = list(times_cashflows.values())

        if yield_calculation_convention == "BEY":
            # Multiply all times by the coupon frequency to convert to BEY
            times = [t * 2 for t in times]
            initial_guess = self.cpn / 100 / 2 if self.cpn > 0 else 0.05
        else:
            initial_guess = (
                self.cpn / 100 if self.cpn > 0 else 0.05
            )  # Default guess for YTM

        # Use xirr to calculate YTM
        result = xirr_base(
            cash_flows=payment_flow,
            times=times,
            guess=initial_guess,
            tol=tol,
            max_iter=max_iter,
        )

        if yield_calculation_convention == "BEY":
            result = result * 2

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
        If neither yield_to_maturity nor price is provided, it is assumed that the clean price is equal to the notional.

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
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.modified_duration(yield_to_maturity=0.05)
        4.2
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

        ytm, time_to_payments, price_calc = self._get_ytm_payments_price(
            yield_to_maturity,
            bond_price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        if yield_calculation_convention == "BEY":
            time_adjustment = 2
        else:
            time_adjustment = 1

        duration = sum(
            [
                t * cf / (1 + ytm / time_adjustment) ** (t * time_adjustment + 1)
                for t, cf in time_to_payments.items()
            ]
        )
        return duration / price_calc if price_calc != 0 else 0.0

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

        If neither yield_to_maturity nor price is provided, it is assumed that the clean price is equal to the notional.

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
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.convexity(yield_to_maturity=0.05)
        18.7
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
        ytm, time_to_payments, price_calc = self._get_ytm_payments_price(
            yield_to_maturity,
            bond_price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        if yield_calculation_convention == "BEY":
            time_adjustment = 2
        else:
            time_adjustment = 1

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
        return convexity / price_calc / time_adjustment**2 if price_calc != 0 else 0.0

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
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.accrued_interest('2024-07-02')
        2.5
        """
        settlement_date = self._resolve_settlement_date(settlement_date)

        if self.cpn_freq == 0 or self.cpn == 0:
            return 0.0

        prev_coupon: pd.Timestamp = self.previous_coupon_date(settlement_date)
        next_coupon: pd.Timestamp = self.next_coupon_date(settlement_date)
        coupon = (self.cpn) * self.notional / 100
        # coupon_per_period = coupon / self.cpn_freq

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

        # days_between = (next_coupon - prev_coupon).days
        # days_accrued = (settlement_date - prev_coupon).days
        # return coupon * days_accrued / days_between if days_between > 0 else 0.0

    def clean_price(
        self,
        dirty_price: float,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
    ) -> float:
        """
        Convert dirty price to clean price.

        The clean price is the price of the bond excluding any accrued interest.

        The formula is as follows:

        .. math::
            CleanPrice = DirtyPrice - AccruedInterest

        Parameters
        ----------
        dirty_price : float
            Dirty price of the bond.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to today.

        Returns
        -------
        clean_price : float
            Clean price of the bond.

        Examples
        --------
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.clean_price(102.5, '2024-07-02')
        100.0
        """
        return dirty_price - self.accrued_interest(settlement_date)

    def dirty_price(
        self,
        clean_price: float,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
    ) -> float:
        """
        Convert clean price to dirty price.

        The dirty price is the price of the bond including accrued interest.

        The formula is as follows:

        .. math::
            DirtyPrice = CleanPrice + AccruedInterest

        Parameters
        ----------
        clean_price : float
            Clean price of the bond.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to today.

        Returns
        -------
        dirty_price : float
            Dirty price of the bond.

        Examples
        --------
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.dirty_price(100.0, '2024-07-02')
        102.5
        """
        return clean_price + self.accrued_interest(settlement_date)

    def price_from_yield(
        self,
        yield_to_maturity: float,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> float:
        """
        Calculate the price of the bond given a yield to maturity (YTM).

        .. math::
            Price = \\sum_{t=1}^{T} \\frac{C_t}{(1 + YTM)^{t}}

        where:
            - :math:`C_t` is the cash flow at time `t`
            - :math:`YTM` is the yield to maturity
            - :math:`T` is the total number of periods

        Parameters
        ----------
        yield_to_maturity : float
            Yield to maturity as a decimal.
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
        price : float
            Price of the bond.

        Examples
        --------
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.price_from_yield(0.05)
        100.0
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

        time_to_payments = self.calculate_time_to_payments(
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        price = self._price_from_yield(
            time_to_payments,
            yield_to_maturity,
            yield_calculation_convention=yield_calculation_convention,
        )

        return price

    def cash_flows(
        self,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> list[float]:
        """
        Return a list of all future cash flows (coupons + principal at maturity).

        Parameters
        ----------
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

        Returns
        -------
        flows : list of float
            List of cash flows for each period.

        Examples
        --------
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.cash_flows('2022-01-01')
        [5.0, 5.0, 105.0]
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

        flows = self.filter_payment_flow(
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        return list(flows.values())

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
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
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
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
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

    def to_dataframe(
        self,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        yield_to_maturity: Optional[float] = None,
        bond_price: Optional[float] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Export the bond’s cash flow schedule as a pandas DataFrame.

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
        yield_to_maturity : float, optional
            Yield to maturity as a decimal. If provided, it will be used to calculate the cash flows.
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
        df : pd.DataFrame
            DataFrame with columns ['date', 'cash_flow']

        Examples
        --------
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.to_dataframe('2022-01-01')
        date        Flows  Coupon  Amortization  Cost
        2022-01-03  5.0    5.0          0.0           0.0
        2023-01-02  5.0    5.0          0.0           0.0
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

        ytm, time_to_payments, price_calc = self._get_ytm_payments_price(
            yield_to_maturity,
            bond_price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        # If neither yield_to_maturity nor bond_price is provided, make price calculation None
        if yield_to_maturity is None and bond_price is None:
            valid_price_calc = False
        else:
            valid_price_calc = True

        flows = self.filter_payment_flow(
            settlement_date,
            price_calc if valid_price_calc else None,
            adjust_to_business_days=adjust_to_business_days,
            day_count_convention=day_count_convention,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
        )

        coupon_flows = self.filter_payment_flow(
            settlement_date,
            None,
            self.coupon_flow,
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
        # Concat coupon_flows and amortization_flows in a single dataframe
        df = pd.concat(
            [
                pd.Series(flows, name="Flows"),
                pd.Series(coupon_flows, name="Coupon"),
                pd.Series(amortization_flows, name="Amortization"),
            ],
            axis=1,
        ).fillna(0)
        df["Cost"] = df["Coupon"] + df["Amortization"] - df["Flows"]

        return df.sort_index()

    def dv01(
        self,
        yield_to_maturity: Optional[float],
        bond_price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> float:
        """
        Calculate the DV01 (Dollar Value of a 1 basis point) for the bond.
        If neither yield_to_maturity nor bond_price is provided, it is assumed that the clean price is equal to the notional.

        Parameters
        ----------
        yield_to_maturity : float
            Yield to maturity as a decimal (e.g., 0.05 for 5%).
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
        dv01 : float
            The change in price for a 1 basis point (0.0001) change in yield.

        Examples
        --------
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.dv01(0.05)
        -0.42
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
        ytm, time_to_payments, price_calc = self._get_ytm_payments_price(
            yield_to_maturity,
            bond_price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        price_up = self.price_from_yield(
            ytm + 0.0001,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        price_down = self.price_from_yield(
            ytm - 0.0001,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        return (price_up - price_down) / 2

    def plot_cash_flows(
        self,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        bond_price: Optional[float] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> None:
        """
        Visualize the cash flow schedule using matplotlib as stacked bars.

        Parameters
        ----------
        settlement_date : str or datetime-like, optional
            Date from which to consider future payments. Defaults to issue date.
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

        Examples
        --------
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.plot_cash_flows('2022-01-01')
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
            settlement_date,
            bond_price=bond_price,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        x_labels = df.index.strftime("%Y-%m-%d")
        cost = -df["Cost"]
        coupon = df["Coupon"]
        amortization = df["Amortization"]

        plt.figure(figsize=(10, 6))
        plt.bar(x_labels, cost, width=0.6, label="Cost")
        plt.bar(x_labels, coupon, width=0.6, bottom=cost, label="Coupon")
        plt.bar(
            x_labels,
            amortization,
            width=0.6,
            bottom=cost + coupon,
            label="Amortization",
        )
        plt.xlabel("Date")
        plt.ylabel("Cash Flow")
        plt.title("Bond Cash Flow Schedule (Stacked)")
        plt.xticks(rotation=45)
        plt.legend()
        plt.tight_layout()
        plt.show()

    def __repr__(self) -> str:
        """
        Return string representation of the BulletBond object.

        Returns
        -------
        str
            String representation of the bond.

        Examples
        --------
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> print(bond)
        BulletBond(issue_dt=2020-01-01 00:00:00, maturity=2025-01-01 00:00:00, cpn=5, cpn_freq=1)
        """
        return (
            f"BulletBond(issue_dt={self.issue_dt}, maturity={self.maturity}, "
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
        if yield_calculation_convention == "BEY":
            time_adjustment = 2
        else:
            time_adjustment = 1

        price = sum(
            [
                cf / (1 + yield_to_maturity / time_adjustment) ** (t * time_adjustment)
                for t, cf in time_to_payments.items()
            ]
        )
        return price

    def _resolve_settlement_date(
        self, settlement_date: Optional[Union[str, pd.Timestamp]]
    ) -> pd.Timestamp:
        """
        Helper to resolve the settlement date for the bond.
        If settlement_date is provided, converts to pd.Timestamp.
        Otherwise, uses self._settlement_date or self.issue_dt.
        """
        if settlement_date is not None:
            dt = pd.to_datetime(settlement_date)
            if dt < self.issue_dt:
                raise ValueError("Settlement date cannot be before issue date.")
            return dt
        if self._settlement_date is not None:
            return self._settlement_date
        return self.issue_dt

    def _resolve_ytm(
        self,
        yield_to_maturity: Optional[float],
        bond_price: Optional[float],
        settlement_date: Optional[Union[str, pd.Timestamp]],
        adjust_to_business_days: bool,
        day_count_convention: DayCountBase,
        following_coupons_day_count: DayCountBase,
        yield_calculation_convention: str,
    ) -> float:
        """
        Helper to resolve yield_to_maturity from direct input, price, or default to notional.
        """
        if bond_price is not None and yield_to_maturity is None:
            if bond_price < 0:
                raise ValueError("Bond price cannot be negative.")
            return self.yield_to_maturity(
                bond_price=bond_price,
                settlement_date=settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                day_count_convention=day_count_convention,
            )

        if bond_price is not None and yield_to_maturity is not None:
            # If bond price provided is very different as a percent from calculated bond price, raise exception
            price_calc = self.price_from_yield(
                yield_to_maturity,
                settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                day_count_convention=day_count_convention,
            )
            if abs(price_calc - bond_price) / bond_price > 0.001 / 100:
                raise ValueError(
                    "Bond price calculated by yield to maturity does not match the given bond price."
                    "Given bond price: {}, calculated bond price: {}".format(
                        bond_price, price_calc
                    )
                )
            price_calc = bond_price

        if yield_to_maturity is not None:
            return yield_to_maturity
        if (
            self._yield_to_maturity is not None
            and self._settlement_date == settlement_date
        ):
            return self._yield_to_maturity

        return self.yield_to_maturity(
            bond_price=self.dirty_price(self.notional, settlement_date),
            settlement_date=settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

    def _get_ytm_payments_price(
        self,
        yield_to_maturity: Optional[float],
        bond_price: Optional[float],
        settlement_date: Optional[Union[str, pd.Timestamp]],
        adjust_to_business_days: bool,
        day_count_convention: DayCountBase,
        following_coupons_day_count: DayCountBase,
        yield_calculation_convention: str,
    ) -> tuple[float, dict[float, float], float]:
        """
        Helper to resolve ytm, time_to_payments, and price_calc for DRY.
        Returns (ytm, time_to_payments, price_calc)
        """

        ytm = self._resolve_ytm(
            yield_to_maturity,
            bond_price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        time_to_payments = self.calculate_time_to_payments(
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        if bond_price is None:
            price_calc = self.price_from_yield(
                ytm,
                settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                day_count_convention=day_count_convention,
            )
        else:
            price_calc = bond_price
        return ytm, time_to_payments, price_calc
