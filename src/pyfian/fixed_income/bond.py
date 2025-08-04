"""
bond.py

Module for fixed income bond analytics, including BulletBond class for payment flows,
valuation, and yield calculations.
"""

from typing import Any, Optional, Union

import pandas as pd
import matplotlib.pyplot as plt
from dateutil.relativedelta import relativedelta  # type: ignore

from pyfian.time_value.irr import xirr


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
    valuation_date : str or datetime-like, optional
        Date for valuation. Defaults to None.
    yield_to_maturity : float, optional
        Yield to maturity of the bond. Set in decimal, e.g., 0.05 for 5%. Defaults to None.
    bond_price : float, optional
        Market price of the bond. Defaults to None.

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
        valuation_date: Optional[Union[str, pd.Timestamp]] = None,
        yield_to_maturity: Optional[float] = None,
        bond_price: Optional[float] = None,
    ) -> None:
        # If coupon is positive, the coupon frequency must be greater than 0
        if cpn > 0 and cpn_freq <= 0:
            raise ValueError(
                "Coupon frequency must be greater than zero for positive coupons."
            )

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

        # New attributes for defaults
        self._valuation_date: Optional[pd.Timestamp] = None

        if valuation_date is not None:
            self.set_valuation_date(valuation_date)

        if yield_to_maturity is not None:
            # Throw error if yield_to_maturity is not None and valuation_date is None
            if self._valuation_date is None:
                raise ValueError(
                    "Valuation date must be set if yield to maturity is set."
                )
            self.set_yield_to_maturity(yield_to_maturity, valuation_date)
        else:
            self._yield_to_maturity: Optional[float] = None

        if bond_price is not None:
            # Throw error if bond_price is not None and valuation_date is None
            if self._valuation_date is None:
                raise ValueError("Valuation date must be set if bond_price is set.")
            if yield_to_maturity is not None:
                # Check if self._bond_price is approximately equal to the bond_price, else raise ValueError
                if (
                    getattr(self, "_bond_price", None) is not None
                    and abs(self._bond_price - bond_price) / self._bond_price > 1e-5
                ):
                    raise ValueError(
                        "Bond price calculated by yield to maturity does not match the current bond price."
                    )
            self.set_bond_price(bond_price, valuation_date)
        elif yield_to_maturity is None:
            # If neither yield_to_maturity nor bond_price is set, set bond price to None
            self._bond_price: Optional[float] = None

    def set_valuation_date(
        self,
        valuation_date: Optional[Union[str, pd.Timestamp]],
        reset_yield_to_maturity: bool = True,
    ) -> Optional[pd.Timestamp]:
        """
        Set the default valuation date for the bond.
        If reset_yield_to_maturity is True, resets the yield to maturity and bond price.

        Parameters
        ----------
        valuation_date : Union[str, pd.Timestamp], optional
            The valuation date to set.
        reset_yield_to_maturity : bool, optional
            Whether to reset the yield to maturity and bond price.
        Returns
        -------
        Optional[pd.Timestamp]
            The updated valuation date.
        Raises
        ------
        ValueError
            If the valuation date is not set when the bond price is set.
        If the valuation date is changed, resets the bond price and yield to maturity if reset_yield_to_maturity is True.
        """
        old_valuation_date = self._valuation_date

        if valuation_date is not None:
            valuation_date = pd.to_datetime(valuation_date)
            if old_valuation_date is not None and valuation_date != old_valuation_date:
                # If the valuation date is changed, reset related attributes
                self._bond_price = None
                if reset_yield_to_maturity:
                    self._yield_to_maturity = None
                else:
                    # If not resetting YTM, ensure it is still valid
                    if self._yield_to_maturity is not None:
                        self._bond_price = self.price_from_yield(
                            self._yield_to_maturity, valuation_date
                        )

            self._valuation_date = pd.to_datetime(valuation_date)
        else:
            self._valuation_date = None
            # If no valuation date is set, reset bond price and YTM
            self._bond_price = None
            self._yield_to_maturity = None
        return self._valuation_date

    def set_yield_to_maturity(
        self,
        ytm: Optional[float],
        valuation_date: Optional[Union[str, pd.Timestamp, None]] = None,
    ) -> None:
        """
        Set the default yield to maturity for the bond. Updates bond price accordingly.
        Parameters
        ----------
        ytm : float, optional
            The yield to maturity to set.
        valuation_date : Union[str, pd.Timestamp], optional
            The valuation date to set.
        Raises
        ------
        ValueError
            If the valuation date is not set when the yield to maturity is set.

        If the yield to maturity is set, it will also update the bond price based on the yield.
        """
        self._yield_to_maturity = ytm

        if valuation_date is not None:
            valuation_date = self.set_valuation_date(valuation_date)
        # Since ytm is set, update bond price
        if ytm is not None:
            vdate = self._valuation_date
            if vdate is None:
                raise ValueError(
                    "Valuation date must be set since there is no default valuation_date for the bond."
                )
            self._bond_price = self.price_from_yield(ytm, vdate)
        else:
            # If no yield to maturity is set, reset bond price and yield to maturity
            self._bond_price = None
            self._yield_to_maturity = None

    def set_bond_price(
        self,
        price: Optional[float],
        valuation_date: Optional[Union[str, pd.Timestamp]] = None,
    ) -> None:
        """
        Set the default bond price for the bond. Updates yield to maturity accordingly.

        Parameters
        ----------
        price : float, optional
            The bond price to set.
        valuation_date : Union[str, pd.Timestamp], optional
            The valuation date to set.
        Raises
        ------
        ValueError
            If the valuation date is not set when the bond price is set.

        If the bond price is set, it will also update the yield to maturity based on the bond price.
        """
        self._bond_price = price
        if valuation_date is not None:
            valuation_date = self.set_valuation_date(valuation_date)
        # Since price is set, update yield to maturity
        if price is not None:
            vdate = self._valuation_date
            if vdate is None:
                raise ValueError(
                    "Valuation date must be set since there is no default valuation_date for the bond."
                )
            self._yield_to_maturity = self.yield_to_maturity(price, vdate)
        else:
            # If no bond price is set, reset yield to maturity and bond price
            self._bond_price = None
            self._yield_to_maturity = None

    def get_valuation_date(self) -> Optional[pd.Timestamp]:
        """
        Get the current valuation date for the bond.
        Returns
        -------
        Optional[pd.Timestamp]
            The current valuation date, or None if not set.
        """
        return self._valuation_date

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
        - dict_payments: Payment dates as keys and cash flow amounts as values.
        - dict_coupons: Coupon payment dates as keys and coupon amounts as values.
        - dict_amortization: Amortization payment dates as keys and amortization amounts as values.

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
                if (next_date_processed - issue_dt).days < (365 * 0.9) // cpn_freq:
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
        valuation_date: Optional[Union[str, pd.Timestamp]] = None,
        bond_price: Optional[float] = None,
        payment_flow: Optional[dict[pd.Timestamp, float]] = None,
    ) -> dict[pd.Timestamp, float]:
        """
        Filter the payment flow to include only payments after the valuation date.

        Parameters
        ----------
        valuation_date : str or datetime-like, optional
            Date from which to consider future payments. Defaults to issue date.
        bond_price : float, optional
            If provided, adds the bond price as a negative cash flow at the valuation date.
        payment_flow : dict, optional
            Dictionary of payment dates and cash flows. If not provided, uses the bond's payment flow.

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
        if payment_flow is None:
            payment_flow = self.payment_flow

        valuation_date = self._resolve_valuation_date(valuation_date)

        settlement_date = valuation_date + pd.offsets.BDay(
            self.settlement_convention_t_plus
        )

        # If settlement date would be after maturity, there are no cash flows
        if settlement_date > maturity - pd.offsets.BDay(1) + pd.offsets.BDay(1):
            return {}
        cash_flows = {}

        # If a bond_price is provided, add it as a negative cash flow
        if bond_price is not None:
            cash_flows[settlement_date] = -bond_price

        pd.offsets.BDay(self.record_date_t_minus)

        # Include all payments after the settlement date
        cash_flows.update(
            {
                pd.to_datetime(key) - pd.offsets.BDay(1) + pd.offsets.BDay(1): value
                for key, value in payment_flow.items()
                if (
                    settlement_date + pd.offsets.BDay(self.record_date_t_minus)
                    <= pd.to_datetime(key) - pd.offsets.BDay(1) + pd.offsets.BDay(1)
                )
                or (pd.to_datetime(key) == maturity and (settlement_date <= key))
            }
        )
        return cash_flows

    def calculate_time_to_payments(
        self,
        valuation_date: Optional[Union[str, pd.Timestamp]] = None,
        bond_price: Optional[float] = None,
    ) -> dict[float, float]:
        """
        Calculate the time to each payment from the valuation date.
        The time is expressed in years.

        Parameters
        ----------
        valuation_date : str or datetime-like, optional
            Date from which to calculate time to payments. Defaults to issue date.
        bond_price : float, optional
            If provided, includes bond price as a negative cash flow.

        Returns
        -------
        dict
            Dictionary with time to payment (in years) as keys and cash flow values.

        Examples
        --------
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.calculate_time_to_payments('2022-01-01')
        {1.0: 5.0, 2.0: 5.0, 3.0: 105.0}
        """
        valuation_date = self._resolve_valuation_date(valuation_date)

        flujos = self.filter_payment_flow(valuation_date, bond_price)
        return {
            (key - (valuation_date + pd.offsets.BDay(1))).days / 365: value
            for key, value in flujos.items()
        }

    def value_with_curve(
        self,
        curve: Any,
        valuation_date: Optional[Union[str, pd.Timestamp]] = None,
        bond_price: Optional[float] = None,
    ) -> tuple[float, dict[float, float]]:
        """
        Value the bond using a discount curve.

        Calculates the present value of the bond's cash flows using the provided discount curve.

        Returns the total present value and a dictionary of present values for each payment.

        If a bond price is provided, it is included as a negative cash flow, and the
        present value would be equivalent to a Net Present Value (NPV) calculation, useful for
        comparing the bond's market price against its theoretical value based on the discount curve.

        This can be used to optimize the yield curve fitting process.

        Parameters
        ----------
        curve : object
            Discount curve object with a discount_t(t) method.
        valuation_date : str or datetime-like, optional
            Valuation date. Defaults to issue date.
        bond_price : float, optional
            If provided, includes bond price as a negative cash flow.

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
        time_to_payments = self.calculate_time_to_payments(valuation_date, bond_price)
        pv = {t: curve.discount_t(t) * value for t, value in time_to_payments.items()}
        return sum(pv.values()), pv

    def yield_to_maturity(
        self,
        bond_price: float,
        valuation_date: Optional[Union[str, pd.Timestamp]] = None,
        tol: float = 1e-6,
        max_iter: int = 100,
    ) -> float:
        """
        Estimate the yield to maturity (YTM) using the xirr function from pyfian.time_value.irr.

        The YTM is the internal rate of return (IRR) of the bond's cash flows, assuming the bond is held to maturity.

        Parameters
        ----------
        bond_price : float
            Price of the bond.
        valuation_date : str or datetime-like, optional
            Valuation date. Defaults to issue date.
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
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.yield_to_maturity(price=95)
        0.06189544078
        """
        # Prepare cash flows and dates
        payment_flow = self.filter_payment_flow(valuation_date, bond_price=bond_price)
        # Use xirr to calculate YTM
        return xirr(payment_flow, tol=tol, max_iter=max_iter)

    def modified_duration(
        self,
        yield_to_maturity: Optional[float] = None,
        bond_price: Optional[float] = None,
        valuation_date: Optional[Union[str, pd.Timestamp]] = None,
    ) -> float:
        """
        Calculate modified duration of the bond.
        If neither yield_to_maturity nor price is provided, it is assumed that the clean price is equal to the notional.

        .. math::
            Modified Duration = \\frac{1}{P} \\sum_{t=1}^{T} \\frac{C_t}{(1 + YTM)^{(t+1)}} \\cdot t
        where:

        - :math:`P` is the price of the bond
        - :math:`C_t` is the cash flow at time t
        - :math:`YTM` is the yield to maturity
        - :math:`T` is the total number of periods

        Parameters
        ----------
        yield_to_maturity : float, optional
            Yield to maturity as a decimal. If not provided, will be calculated from bond_price if given.
        bond_price : float, optional
            Price of the bond. Used to estimate YTM if yield_to_maturity is not provided.
        valuation_date : str or datetime-like, optional
            Valuation date. Defaults to issue date.

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
        valuation_date = self._resolve_valuation_date(valuation_date)

        ytm, time_to_payments, price_calc = self._get_ytm_payments_price(
            yield_to_maturity, bond_price, valuation_date
        )
        duration = sum(
            [t * cf / (1 + ytm) ** (t + 1) for t, cf in time_to_payments.items()]
        )
        return duration / price_calc if price_calc != 0 else 0.0

    def convexity(
        self,
        yield_to_maturity: Optional[float] = None,
        bond_price: Optional[float] = None,
        valuation_date: Optional[Union[str, pd.Timestamp]] = None,
    ) -> float:
        """
        Calculate the convexity of the bond.

        If neither yield_to_maturity nor price is provided, it is assumed that the clean price is equal to the notional.

        .. math::
            Convexity = \\frac{1}{P} \\sum_{t=1}^{T} \\frac{C_t \\cdot t \\cdot (t + 1)}{(1 + YTM)^{(t + 2)}}
        where:

        - :math:`P` is the price of the bond
        - :math:`C_t` is the cash flow at time t
        - :math:`YTM` is the yield to maturity
        - :math:`T` is the total number of periods

        Parameters
        ----------
        yield_to_maturity : float, optional
            Yield to maturity as a decimal. If not provided, will be calculated from price if given.
        bond_price : float, optional
            Price of the bond. Used to estimate YTM if yield_to_maturity is not provided.
        valuation_date : str or datetime-like, optional
            Valuation date. Defaults to issue date.

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
        valuation_date = self._resolve_valuation_date(valuation_date)

        ytm, time_to_payments, price_calc = self._get_ytm_payments_price(
            yield_to_maturity, bond_price, valuation_date
        )
        convexity = sum(
            [
                cf * t * (t + 1) / (1 + ytm) ** (t + 2)
                for t, cf in time_to_payments.items()
            ]
        )
        return convexity / price_calc if price_calc != 0 else 0.0

    def accrued_interest(
        self, valuation_date: Optional[Union[str, pd.Timestamp]] = None
    ) -> float:
        """
        Calculate accrued interest since last coupon payment.
        This is the interest that has accumulated on the bond since the last coupon payment date

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
        >>> bond.accrued_interest('2023-06-01')
        2.5
        """
        valuation_date = self._resolve_valuation_date(valuation_date)

        settlement_date = valuation_date + pd.offsets.BDay(
            self.settlement_convention_t_plus
        )

        if self.cpn_freq == 0 or self.cpn == 0:
            return 0.0

        prev_coupon = self.previous_coupon_date(settlement_date)
        next_coupon = self.next_coupon_date(settlement_date)
        coupon = (self.cpn / self.cpn_freq) * self.notional / 100
        # If before first coupon, accrue from issue date
        if next_coupon is None:
            return 0.0
        if prev_coupon is None and next_coupon is not None:
            days_between = (next_coupon - self.issue_dt).days
            days_accrued = (settlement_date - self.issue_dt).days
            return coupon * days_accrued / days_between if days_between > 0 else 0.0

        days_between = (next_coupon - prev_coupon).days
        days_accrued = (settlement_date - prev_coupon).days
        return coupon * days_accrued / days_between if days_between > 0 else 0.0

    def clean_price(
        self,
        dirty_price: float,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
    ) -> float:
        """
        Convert dirty price to clean price.

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
        >>> bond.clean_price(102.5, '2023-06-01')
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
        >>> bond.dirty_price(100.0, '2023-06-01')
        102.5
        """
        return clean_price + self.accrued_interest(settlement_date)

    def price_from_yield(
        self,
        yield_to_maturity: float,
        valuation_date: Optional[Union[str, pd.Timestamp]] = None,
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
        valuation_date : str or datetime-like, optional
            Valuation date. Defaults to issue date.

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
        time_to_payments = self.calculate_time_to_payments(valuation_date)
        price = self._price_from_yield(time_to_payments, yield_to_maturity)
        return price

    def cash_flows(
        self, valuation_date: Optional[Union[str, pd.Timestamp]] = None
    ) -> list[float]:
        """
        Return a list of all future cash flows (coupons + principal at maturity).

        Parameters
        ----------
        valuation_date : str or datetime-like, optional
            Date from which to consider future payments. Defaults to issue date.

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
        flows = self.filter_payment_flow(valuation_date)
        return list(flows.values())

    def next_coupon_date(
        self, valuation_date: Optional[Union[str, pd.Timestamp]] = None
    ) -> Optional[pd.Timestamp]:
        """
        Get the next coupon payment date from a given date.

        Parameters
        ----------
        valuation_date : str or datetime-like, optional
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
        valuation_date = self._resolve_valuation_date(valuation_date)

        settlement_date = valuation_date + pd.offsets.BDay(
            self.settlement_convention_t_plus
        )
        future_dates = [d for d in self.coupon_flow.keys() if d > settlement_date]
        return min(future_dates) if future_dates else None

    def previous_coupon_date(
        self, valuation_date: Optional[Union[str, pd.Timestamp]] = None
    ) -> Optional[pd.Timestamp]:
        """
        Get the previous coupon payment date from a given date.

        Parameters
        ----------
        valuation_date : str or datetime-like, optional
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
        valuation_date = self._resolve_valuation_date(valuation_date)

        settlement_date = valuation_date + pd.offsets.BDay(
            self.settlement_convention_t_plus
        )

        past_dates = [d for d in self.coupon_flow.keys() if d <= settlement_date]

        return max(past_dates) if past_dates else None

    def to_dataframe(
        self,
        valuation_date: Optional[Union[str, pd.Timestamp]] = None,
        bond_price: Optional[float] = None,
    ) -> pd.DataFrame:
        """
        Export the bond’s cash flow schedule as a pandas DataFrame.

        Parameters
        ----------
        valuation_date : str or datetime-like, optional
            Date from which to consider future payments. Defaults to issue date.
        bond_price : float, optional
            If provided, includes bond price as a negative cash flow.

        Returns
        -------
        df : pd.DataFrame
            DataFrame with columns ['date', 'cash_flow']

        Examples
        --------
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.to_dataframe('2022-01-01')
        date        cash_flow
        0 2023-01-01    5.0
        1 2024-01-01    5.0
        2 2025-01-01    105.0
        """
        valuation_date = self._resolve_valuation_date(valuation_date)

        ytm, time_to_payments, price_calc = self._get_ytm_payments_price(
            None, bond_price, valuation_date
        )

        flows = self.filter_payment_flow(valuation_date, price_calc)
        coupon_flows = self.filter_payment_flow(valuation_date, None, self.coupon_flow)
        amortization_flows = self.filter_payment_flow(
            valuation_date, None, self.amortization_flow
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
        df["Cost"] = df["Flows"] - df["Coupon"] - df["Amortization"]

        return df.sort_index()

    def dv01(
        self,
        yield_to_maturity: Optional[float],
        bond_price: Optional[float] = None,
        valuation_date: Optional[Union[str, pd.Timestamp]] = None,
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
        valuation_date : str or datetime-like, optional
            Valuation date. Defaults to issue date.

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
        valuation_date = self._resolve_valuation_date(valuation_date)
        # Resolve yield to maturity and bond price
        ytm, time_to_payments, price_calc = self._get_ytm_payments_price(
            yield_to_maturity, bond_price, valuation_date
        )
        price_up = self.price_from_yield(ytm + 0.0001, valuation_date)
        return price_up - price_calc

    def plot_cash_flows(
        self,
        valuation_date: Optional[Union[str, pd.Timestamp]] = None,
        bond_price: Optional[float] = None,
    ) -> None:
        """
        Visualize the cash flow schedule using matplotlib as stacked bars.

        Parameters
        ----------
        valuation_date : str or datetime-like, optional
            Date from which to consider future payments. Defaults to issue date.
        bond_price : float, optional
            If provided, includes bond price as a negative cash flow.

        Examples
        --------
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.plot_cash_flows('2022-01-01')
        # Shows a plot
        """

        df = self.to_dataframe(valuation_date, bond_price)
        x_labels = df.index.strftime("%Y-%m-%d")
        cost = df["Cost"]
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
        self, time_to_payments: dict[float, float], yield_to_maturity: float
    ) -> float:
        """
        Helper to calculate the price of the bond from yield to maturity and time to payments.
        Parameters
        ----------
        time_to_payments : dict
            Dictionary with time to payment (in years) as keys and cash flow values.
        yield_to_maturity : float
            Yield to maturity as a decimal (e.g., 0.05 for 5%).
        Returns
        -------
        float
            Price of the bond.
        """
        price = sum(
            [cf / (1 + yield_to_maturity) ** t for t, cf in time_to_payments.items()]
        )
        return price

    def _resolve_ytm(
        self,
        yield_to_maturity: Optional[float],
        price: Optional[float],
        valuation_date: Optional[Union[str, pd.Timestamp]],
    ) -> float:
        """
        Helper to resolve yield_to_maturity from direct input, price, or default to notional.
        """
        if price is not None:
            return self.yield_to_maturity(
                bond_price=price, valuation_date=valuation_date
            )
        if yield_to_maturity is not None:
            return yield_to_maturity
        if (
            self._yield_to_maturity is not None
            and self._valuation_date == valuation_date
        ):
            return self._yield_to_maturity
        return self.yield_to_maturity(
            bond_price=self.dirty_price(self.notional, valuation_date),
            valuation_date=valuation_date,
        )

    def _get_ytm_payments_price(
        self,
        yield_to_maturity: Optional[float],
        price: Optional[float],
        valuation_date: Optional[Union[str, pd.Timestamp]],
    ) -> tuple[float, dict[float, float], float]:
        """
        Helper to resolve ytm, time_to_payments, and price_calc for DRY.
        Returns (ytm, time_to_payments, price_calc)
        """
        ytm = self._resolve_ytm(yield_to_maturity, price, valuation_date)
        time_to_payments = self.calculate_time_to_payments(valuation_date)
        price_calc = self._price_from_yield(time_to_payments, ytm)
        return ytm, time_to_payments, price_calc

    def _resolve_valuation_date(
        self, valuation_date: Optional[Union[str, pd.Timestamp]]
    ) -> pd.Timestamp:
        """
        Helper to resolve the valuation date for the bond.
        If valuation_date is provided, converts to pd.Timestamp.
        Otherwise, uses self._valuation_date or self.issue_dt.
        """
        if valuation_date is not None:
            return pd.to_datetime(valuation_date)
        if self._valuation_date is not None:
            return self._valuation_date
        return self.issue_dt


# class BulletBond:
#     """
#     Bullet Bond class representing a standard fixed-income security.

#     Parameters
#     ----------
#     face_value : float
#         The nominal value of the bond (par value).
#     coupon_rate : float
#         Annual coupon rate as a decimal (e.g., 0.05 for 5%).
#     maturity : int
#         Number of years until maturity.
#     price : float, optional
#         Current market price of the bond. Defaults to face value.
#     frequency : int, optional
#         Number of coupon payments per year. Defaults to 1.
#     """
#     def __init__(self, face_value: float, coupon_rate: float, maturity: int,
#                   price: float = None, frequency: int = 1):
#         self.face_value = face_value
#         self.coupon_rate = coupon_rate
#         self.maturity = maturity
#         self.price = price if price is not None else face_value
#         self.frequency = frequency

#     def coupon_payment(self) -> float:
#         """
#         Return the coupon payment per period.

#         Returns
#         -------
#         payment : float
#             Coupon payment per period.
#         """
#         return self.face_value * self.coupon_rate / self.frequency

#     def cash_flows(self) -> list:
#         """
#         Return a list of all cash flows (coupons + principal at maturity).

#         Returns
#         -------
#         flows : list of float
#             List of cash flows for each period.
#         """
#         flows = [self.coupon_payment()] * (self.maturity * self.frequency)
#         flows[-1] += self.face_value
#         return flows

#     def price_from_yield(self, yield_to_maturity: float) -> float:
#         """
#         Calculate the price of the bond given a yield to maturity (YTM).

#         Parameters
#         ----------
#         yield_to_maturity : float
#             Yield to maturity as a decimal (e.g., 0.05 for 5%).

#         Returns
#         -------
#         price : float
#             Price of the bond.
#         """
#         ytm = yield_to_maturity / self.frequency
#         n = self.maturity * self.frequency
#         c = self.coupon_payment()
#         price = sum([c / (1 + ytm) ** t for t in range(1, n + 1)])
#         price += self.face_value / (1 + ytm) ** n
#         return price

#     def yield_to_maturity(self) -> float:
#         """
#         Estimate the yield to maturity (YTM) using Newton-Raphson method.

#         Returns
#         -------
#         ytm : float
#             Estimated yield to maturity as a decimal.

#         Raises
#         ------
#         ValueError
#             If bond price is not set.
#         """
#         if self.price is None:
#             raise ValueError("Bond price must be set to calculate YTM.")
#         n = self.maturity * self.frequency
#         c = self.coupon_payment()
#         price = self.price
#         ytm = self.coupon_rate  # initial guess
#         for _ in range(100):
#             f = sum([c / (1 + ytm / self.frequency) ** t for t in range(1, n + 1)])
#             f += self.face_value / (1 + ytm / self.frequency) ** n
#             f -= price
#             # Derivative
#             df = sum([-t * c / self.frequency / (1 + ytm / self.frequency) ** (t + 1)
#                       for t in range(1, n + 1)])
#             df += -n * self.face_value / self.frequency / (1 + ytm / self.frequency) ** (n + 1)
#             if abs(df) < 1e-8:
#                 break
#             ytm -= f / df
#             if abs(f) < 1e-8:
#                 break
#         return ytm

#     def duration(self, yield_to_maturity: float = None) -> float:
#         """
#         Calculate Macaulay duration of the bond.

#         Parameters
#         ----------
#         yield_to_maturity : float, optional
#             Yield to maturity as a decimal. Defaults to coupon rate.

#         Returns
#         -------
#         duration : float
#             Macaulay duration in years.
#         """
#         if yield_to_maturity is None:
#             yield_to_maturity = self.coupon_rate
#         ytm = yield_to_maturity / self.frequency
#         n = self.maturity * self.frequency
#         c = self.coupon_payment()
#         price = self.price_from_yield(yield_to_maturity)
#         duration = sum([t * c / (1 + ytm) ** t for t in range(1, n + 1)])
#         duration += n * self.face_value / (1 + ytm) ** n
#         duration /= price
#         return duration / self.frequency

#     def __repr__(self):
#         """
#         Return string representation of the Bond object.

#         Returns
#         -------
#         repr : str
#             String representation.
#         """
#         return (f"Bond(face_value={self.face_value}, coupon_rate={self.coupon_rate}, "
#                 f"maturity={self.maturity}, price={self.price}, frequency={self.frequency})")
