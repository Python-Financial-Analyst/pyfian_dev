"""
money_market_instruments.py

Module for money market instruments, including generic MoneyMarketInstrument and specific types such as Treasury Bill, Certificate of Deposit, Commercial Paper, and Banker's Acceptance.

Provides classes for short-term debt instruments, payment flow generation, and instrument-specific conventions.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, Union

import numpy as np
import pandas as pd
from pyfian.fixed_income.base_fixed_income import BaseFixedIncomeInstrument
from pyfian.utils.day_count import DayCountBase, get_day_count_convention
from pyfian.time_value import rate_conversions as rc


class MoneyMarketInstrument(BaseFixedIncomeInstrument):
    """
    MoneyMarketInstrument represents a generic short-term debt instrument, typically with maturities less than one year.
    Inherits from BaseFixedIncomeInstrument and provides payment flow logic specific to money market conventions.

    Parameters
    ----------
    issue_dt : str or datetime-like
            Issue date of the instrument.
    maturity : str or datetime-like
            Maturity date of the instrument.
    cpn : float
            Annual coupon rate (percentage).
    cpn_freq : int
            Number of coupon payments per year.
    notional : float, optional
            Face value (principal) of the instrument. Defaults to 100.
    day_count_convention : str, optional
            Day count convention for the instrument. Defaults to 'actual/360'.
    kwargs : dict, optional
            Additional keyword arguments for FixedRateBullet.

    Attributes
    ----------
    payment_flow : dict
            Dictionary of payment dates and amounts (principal + coupon).
    coupon_flow : dict
            Dictionary of coupon payment dates and amounts.
    amortization_flow : dict
            Dictionary of amortization payment dates and amounts.
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
        day_count_convention: str | DayCountBase = "actual/365",
        following_coupons_day_count: str | DayCountBase = "30/360",
        yield_calculation_convention: str = "Add-On",
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

    def make_payment_flow(self):
        """
        Generate the payment flow for a money market instrument.

        Returns
        -------
        tuple
                (dict_payments, dict_coupons, dict_amortization):
                - dict_payments: Dictionary of payment dates and total payments (principal + coupon).
                - dict_coupons: Dictionary of coupon payment dates and amounts.
                - dict_amortization: Dictionary of amortization payment dates and amounts.

        Notes
        -----
        For money market instruments, typically only a single payment at maturity (principal + last coupon, if any).
        Coupon is calculated using the day count convention and year fraction between issue and maturity.
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

        # Use day count convention to calculate year fraction
        year_fraction = self.day_count_convention.fraction(issue_dt, maturity)

        # Final payment: principal + last coupon
        last_coupon = (
            (cpn / cpn_freq) * year_fraction * notional / 100 if cpn > 0 else 0
        )
        dict_payments[maturity] = notional + last_coupon
        dict_amortization[maturity] = notional

        if cpn > 0:
            dict_coupons[maturity] = last_coupon

        # Sort the payment dates
        dict_payments = dict(sorted(dict_payments.items()))
        dict_coupons = dict(sorted(dict_coupons.items()))
        dict_amortization = dict(sorted(dict_amortization.items()))
        return dict_payments, dict_coupons, dict_amortization

    @classmethod
    def from_days(
        cls,
        days,
        notional=100,
        day_count_convention="actual/360",
        issue_dt=None,
        **kwargs,
    ):
        """
        Create a MoneyMarketInstrument with a specified number of days to maturity.

        Parameters
        ----------
        days : int
                Number of days until maturity.
        notional : float, optional
                Face value (principal). Defaults to 100.
        day_count_convention : str, optional
                Day count convention. Defaults to 'actual/360'.
        issue_dt : datetime, optional
                Issue date. Defaults to current date if None.
        kwargs : dict, optional
                Additional keyword arguments for FixedRateBullet.

        Returns
        -------
        MoneyMarketInstrument
                Instance with specified maturity.
        """
        if issue_dt is None:
            issue_dt = datetime.now()
        maturity = issue_dt + timedelta(days=days)
        return cls(
            issue_dt=issue_dt,
            maturity=maturity,
            notional=notional,
            day_count_convention=day_count_convention,
            **kwargs,
        )

    # Implement accrued_interest for Money Market Instruments
    def accrued_interest(
        self, settlement_date: Optional[Union[str, pd.Timestamp]] = None
    ) -> float:
        """
        Calculate the accrued interest for the money market instrument.

        Parameters
        ----------
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.

        Returns
        -------
        accrued_interest : float
            The accrued interest amount.
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        t = self.day_count_convention.fraction(self.issue_dt, settlement_date)
        accrued_interest = (self.cpn / self.cpn_freq) * t * self.notional / 100
        return accrued_interest

    def yield_to_maturity(
        self,
        bond_price: float,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
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
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.yield_to_maturity(bond_price=95)
        np.float64(0.06100197251858131)
        """
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
        flows = self._filter_payment_flow(
            settlement_date,
            bond_price,
            payment_flow=self.payment_flow,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        assert len(flows) == 2, (
            f"A Money Market instrument is supposed to have one payment and one price, got {flows}."
        )

        max_date = max(flows)
        min_date = min(flows)
        t = (max_date - min_date).days / 365
        effective_annual_rate = (flows[max_date] / -flows[min_date]) ** (1 / t) - 1

        if yield_calculation_convention == "Continuous":
            return rc.convert_effective_to_mmr(effective_annual_rate, "Continuous")
        elif yield_calculation_convention == "Annual":
            return effective_annual_rate
        elif yield_calculation_convention in ["Add-On", "Discount"]:
            return rc.convert_effective_to_mmr(
                effective_annual_rate,
                yield_calculation_convention=yield_calculation_convention,
                days=day_count_convention.numerator(
                    start=settlement_date, end=max_date, current=max_date
                ),
                base=day_count_convention.denominator(
                    start=settlement_date, end=max_date, current=max_date
                ),
            )
        elif yield_calculation_convention == "BEY":
            return rc.convert_effective_to_mmr(
                effective_annual_rate, "BEY", days=(max_date - min_date).days
            )
        else:
            raise ValueError(
                f"Unknown yield calculation convention: {yield_calculation_convention}"
            )

    def _validate_yield_calculation_convention(
        self, yield_calculation_convention: str
    ) -> str:
        """
        Validate the yield calculation convention.
        Raises ValueError if the convention is not supported.
        """
        valid_conventions_dict = {
            "discount": "Discount",
            "add-on": "Add-On",
            "annual": "Annual",
            "continuous": "Continuous",
            "bey": "BEY",
        }

        if yield_calculation_convention.lower() not in valid_conventions_dict:
            raise ValueError(
                f"Unsupported yield calculation convention: {yield_calculation_convention}. "
                f"Supported conventions: {valid_conventions_dict}"
            )
        return valid_conventions_dict[yield_calculation_convention.lower()]

    def _price_from_yield(
        self,
        time_to_payments: dict[tuple[float, float], float],
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
        assert len(time_to_payments) == 1, (
            f"A Money Market instrument is supposed to have one payment, got {time_to_payments}."
        )
        t, cf = next(iter(time_to_payments.items()))
        days = t[0]
        base = t[1]

        if yield_calculation_convention == "Discount":
            # Convert to yield_to_maturity add_on
            present_value = cf * (1 - days / base * yield_to_maturity)
            yield_to_maturity = (cf / present_value - 1) * base / days

        if yield_calculation_convention == "Continuous":
            price = cf * np.exp(-yield_to_maturity * days / 365)
        elif yield_calculation_convention == "Annual":
            price = cf / (1 + yield_to_maturity) ** (days / 365)
        elif yield_calculation_convention == "Add-On":
            price = cf / (1 + yield_to_maturity * days / base)
        elif yield_calculation_convention == "BEY":
            price = cf / (1 + yield_to_maturity * days / 365)
        elif yield_calculation_convention == "Discount":
            price = cf * (1 - days / base * yield_to_maturity)
        else:
            raise ValueError(
                f"Unknown yield calculation convention: {yield_calculation_convention}"
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

    # Should Return Days
    def _calculate_time_to_payments(
        self,
        settlement_date,
        bond_price,
        adjust_to_business_days,
        following_coupons_day_count,
        yield_calculation_convention,
        day_count_convention,
    ) -> dict[tuple[float, float], float]:
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

        time_to_payments_keys = sorted(flows.keys())

        times: defaultdict[tuple[float, float], float] = defaultdict(float)
        maturity = time_to_payments_keys[-1]
        base = day_count_convention.denominator(
            start=settlement_date, end=maturity, current=settlement_date
        )

        for key in time_to_payments_keys:
            days = day_count_convention.numerator(
                start=settlement_date, end=maturity, current=maturity
            )
            times[(days, base)] = times.get((days, base), 0) + flows[key]

        return dict(times)

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

        if ytm is None or price_calc is None:
            raise ValueError(
                "Unable to resolve yield to maturity. You must input settlement_date and either yield_to_maturity or bond_price. Previous information was not available."
            )

        assert len(time_to_payments) == 1, (
            f"A Money Market instrument is supposed to have one payment, got {time_to_payments}."
        )
        t, cf = next(iter(time_to_payments.items()))
        days = t[0]
        base = t[1]

        if yield_calculation_convention == "Continuous":
            duration = cf * np.exp(-ytm * days / 365) * days / 365
        elif yield_calculation_convention == "Annual":
            duration = cf / (1 + ytm) ** (days / 365 + 1) * days / 365
        elif yield_calculation_convention == "Add-On":
            # derivative of (1 / (1 + x * t)) is -(t / (1 + x * t)^2)
            duration = cf / (1 + ytm * days / base) ** 2 * (days / base)
        elif yield_calculation_convention == "BEY":
            duration = cf / (1 + ytm * days / 365) ** 2 * (days / 365)
        elif yield_calculation_convention == "Discount":
            # derivative of (1 - x) is -1
            duration = cf * days / base
        else:
            raise ValueError(
                f"Unknown yield calculation convention: {yield_calculation_convention}"
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
                Calculate Macaulay duration of the bond. It is the weighted average time to receive the bond's cash flows, where the weights are the present values of the cash flows.


        .. math::
            Macaulay Duration = \\frac{1}{P} \\sum_{t=1}^{T} \\frac{C_t}{(1 + YTM)^{(t+1)}} \\cdot t
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

        if ytm is None or price_calc is None:
            raise ValueError(
                "Unable to resolve yield to maturity. You must input settlement_date and either yield_to_maturity or bond_price. Previous information was not available."
            )

        assert len(time_to_payments) == 1, (
            f"A Money Market instrument is supposed to have one payment, got {time_to_payments}."
        )
        t, cf = next(iter(time_to_payments.items()))
        days = t[0]
        base = t[1]

        if yield_calculation_convention == "Continuous":
            duration = cf * np.exp(-ytm * days / 365) * days / 365
        elif yield_calculation_convention == "Annual":
            duration = cf / (1 + ytm) ** (days / 365) * days / 365
        elif yield_calculation_convention == "Add-On":
            # derivative of (1 / (1 + x * t)) is -(t / (1 + x * t)^2)
            duration = cf / (1 + ytm * days / base) * (days / base)
        elif yield_calculation_convention == "BEY":
            duration = cf / (1 + ytm * days / 365) * (days / 365)
        elif yield_calculation_convention == "Discount":
            # derivative of (1 - x) is -1
            duration = cf * days / base
        else:
            raise ValueError(
                f"Unknown yield calculation convention: {yield_calculation_convention}"
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

        if ytm is None or price_calc is None:
            raise ValueError(
                "Unable to resolve yield to maturity. You must input settlement_date and either yield_to_maturity or bond_price. Previous information was not available."
            )

        assert len(time_to_payments) == 1, (
            f"A Money Market instrument is supposed to have one payment, got {time_to_payments}."
        )

        t, cf = next(iter(time_to_payments.items()))
        days = t[0]
        base = t[1]

        if yield_calculation_convention == "Continuous":
            convexity = cf * np.exp(-ytm * days / 365) * (days / 365) ** 2
        elif yield_calculation_convention == "Annual":
            convexity = (
                cf / (1 + ytm) ** (days / 365 + 2) * (days / 365) * (days / 365 + 1)
            )
        elif yield_calculation_convention == "Add-On":
            # derivative of (1 / (1 + x * t)) is -(t / (1 + x * t)^2)
            convexity = cf / (1 + ytm * days / base) ** 3 * (days / base) ** 2
        elif yield_calculation_convention == "BEY":
            convexity = cf / (1 + ytm * days / 365) ** 3 * (days / 365) ** 2
        elif yield_calculation_convention == "Discount":
            # derivative of (1 - x) is -1
            convexity = 0.0
        else:
            raise ValueError(
                f"Unknown yield calculation convention: {yield_calculation_convention}"
            )

        return round(convexity / price_calc, 10) if price_calc != 0 else 0.0


class TreasuryBill(MoneyMarketInstrument):
    """
    TreasuryBill represents a short-term government security issued at a discount and maturing at par.
    Coupon is always zero and payment is made at maturity.

    Parameters
    ----------
    issue_dt : str or datetime-like
            Issue date of the T-Bill.
    maturity : str or datetime-like
            Maturity date of the T-Bill.
    notional : float, optional
            Face value (principal). Defaults to 100.
    day_count_convention : str, optional
            Day count convention. Defaults to 'actual/360'.
    yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to 'Discount'.
    kwargs : dict, optional
            Additional keyword arguments for MoneyMarketInstrument.
    """

    def __init__(
        self,
        issue_dt,
        maturity,
        notional=100,
        day_count_convention="actual/360",
        yield_calculation_convention="Discount",
        **kwargs,
    ):
        super().__init__(
            issue_dt=issue_dt,
            maturity=maturity,
            cpn=0.0,
            cpn_freq=1,
            notional=notional,
            day_count_convention=day_count_convention,
            yield_calculation_convention=yield_calculation_convention,
            **kwargs,
        )


class CertificateOfDeposit(MoneyMarketInstrument):
    """
    CertificateOfDeposit (CD) is a time deposit with a fixed interest rate and specified maturity.
    Pays interest at maturity or at specified frequency.

    Parameters
    ----------
    issue_dt : str or datetime-like
            Issue date of the CD.
    maturity : str or datetime-like
            Maturity date of the CD.
    cpn : float
            Annual coupon rate (percentage).
    cpn_freq : int, optional
            Number of coupon payments per year. Defaults to 1.
    notional : float, optional
            Face value (principal). Defaults to 100.
    day_count_convention : str, optional
            Day count convention. Defaults to 'actual/360'.
    yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to 'Add-On'.
    kwargs : dict, optional
            Additional keyword arguments for MoneyMarketInstrument.
    """

    def __init__(
        self,
        issue_dt,
        maturity,
        cpn,
        cpn_freq=1,
        notional=100,
        day_count_convention="actual/360",
        yield_calculation_convention="Add-On",
        **kwargs,
    ):
        super().__init__(
            issue_dt=issue_dt,
            maturity=maturity,
            cpn=cpn,
            cpn_freq=cpn_freq,
            notional=notional,
            day_count_convention=day_count_convention,
            yield_calculation_convention=yield_calculation_convention,
            **kwargs,
        )


class CommercialPaper(MoneyMarketInstrument):
    """
    CommercialPaper (CP) is a short-term unsecured promissory note issued by corporations.
    Issued at a discount, pays principal at maturity. Coupon is always zero.

    Parameters
    ----------
    issue_dt : str or datetime-like
            Issue date of the CP.
    maturity : str or datetime-like
            Maturity date of the CP.
    notional : float, optional
            Face value (principal). Defaults to 100.
    day_count_convention : str, optional
            Day count convention. Defaults to 'actual/360'.
    yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to 'Discount'.
    kwargs : dict, optional
            Additional keyword arguments for MoneyMarketInstrument.
    """

    def __init__(
        self,
        issue_dt,
        maturity,
        notional=100,
        day_count_convention="actual/360",
        yield_calculation_convention="Discount",
        **kwargs,
    ):
        super().__init__(
            issue_dt=issue_dt,
            maturity=maturity,
            cpn=0.0,
            cpn_freq=1,
            notional=notional,
            day_count_convention=day_count_convention,
            yield_calculation_convention=yield_calculation_convention,
            **kwargs,
        )


class BankersAcceptance(MoneyMarketInstrument):
    """
    BankersAcceptance (BA) is a short-term debt instrument guaranteed by a bank, commonly used in international trade.
    Issued at a discount, pays principal at maturity. Coupon is always zero.

    Parameters
    ----------
    issue_dt : str or datetime-like
            Issue date of the BA.
    maturity : str or datetime-like
            Maturity date of the BA.
    notional : float, optional
            Face value (principal). Defaults to 100.
    day_count_convention : str, optional
            Day count convention. Defaults to 'actual/360'.
    yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to 'Discount'.
    kwargs : dict, optional
            Additional keyword arguments for MoneyMarketInstrument.
    """

    def __init__(
        self,
        issue_dt,
        maturity,
        notional=100,
        day_count_convention="actual/360",
        yield_calculation_convention="Discount",
        **kwargs,
    ):
        super().__init__(
            issue_dt=issue_dt,
            maturity=maturity,
            cpn=0.0,
            cpn_freq=1,
            notional=notional,
            day_count_convention=day_count_convention,
            yield_calculation_convention=yield_calculation_convention,
            **kwargs,
        )
