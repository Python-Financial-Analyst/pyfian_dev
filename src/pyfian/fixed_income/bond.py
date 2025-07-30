"""
bond.py

Module for fixed income bond analytics, including BulletBond class for payment flows,
valuation, and yield calculations.
"""

from typing import Any, Optional, Union

import pandas as pd
from dateutil.relativedelta import relativedelta  # type: ignore

from pyfian.time_value.irr import xirr


class BulletBond:
    """
    BulletBond represents a bullet bond with fixed coupon payments and principal at maturity.

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

    Examples
    --------
    >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
    >>> bond.payment_flow
    {Timestamp('2025-01-01 00:00:00'): 105.0, Timestamp('2024-01-01 00:00:00'): 5.0, ...}
    """

    def __init__(
        self,
        issue_dt: Union[str, pd.Timestamp],
        maturity: Union[str, pd.Timestamp],
        cpn: float,
        cpn_freq: int,
    ) -> None:
        self.issue_dt: pd.Timestamp = pd.to_datetime(issue_dt)
        self.maturity: pd.Timestamp = pd.to_datetime(maturity)
        self.cpn: float = cpn
        self.cpn_freq: int = cpn_freq
        self.payment_flow: dict[pd.Timestamp, float] = self.make_payment_flow()

    def make_payment_flow(self) -> dict[pd.Timestamp, float]:
        """
        Generate the payment flow (cash flows) for the bond.

        Returns
        -------
        dict_payments : dict
            Dictionary with payment dates as keys and cash flow amounts as values.

        Examples
        --------
        >>> bond = BulletBond('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.make_payment_flow()
        {Timestamp('2025-01-01 00:00:00'): 105.0, Timestamp('2024-01-01 00:00:00'): 5.0, ...}
        """
        issue_dt, maturity, cpn, cpn_freq = (
            self.issue_dt,
            self.maturity,
            self.cpn,
            self.cpn_freq,
        )
        dict_payments = {}
        dict_payments[maturity] = 100 + cpn / cpn_freq
        next_date_processed = maturity - relativedelta(months=12 // cpn_freq)

        for i in range(2, ((maturity - issue_dt) / 365).days * cpn_freq + 3):
            if (next_date_processed - issue_dt).days < (365 * 0.9) // cpn_freq:
                break
            dict_payments[next_date_processed] = cpn / cpn_freq
            next_date_processed = maturity - relativedelta(months=12 // cpn_freq * i)
        return dict_payments

    def filter_payment_flow(
        self,
        valuation_date: Optional[Union[str, pd.Timestamp]] = None,
        bond_price: Optional[float] = None,
    ) -> dict[pd.Timestamp, float]:
        """
        Filter the payment flow to include only payments after the valuation date.

        Parameters
        ----------
        valuation_date : str or datetime-like, optional
            Date from which to consider future payments. Defaults to issue date.
        bond_price : float, optional
            If provided, adds the bond price as a negative cash flow at the valuation date.

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
        (
            issue_dt,
            maturity,
        ) = (
            self.issue_dt,
            self.maturity,
        )

        if valuation_date is not None:
            valuation_date = pd.to_datetime(valuation_date)
        else:
            valuation_date = issue_dt

        if valuation_date + pd.offsets.BDay(1) >= maturity - pd.offsets.BDay(
            1
        ) + pd.offsets.BDay(1):
            return {}
        cash_flows = {
            pd.to_datetime(key) - pd.offsets.BDay(1) + pd.offsets.BDay(1): value
            for key, value in self.payment_flow.items()
            if valuation_date <= pd.to_datetime(key) - pd.offsets.BDay(2)
            or (
                pd.to_datetime(key) == maturity
                and (valuation_date <= key - pd.offsets.BDay(1))
            )
        }
        if bond_price is not None:
            cash_flows[valuation_date + pd.offsets.BDay(1)] = -bond_price
        return cash_flows

    def calculate_time_to_payments(
        self,
        valuation_date: Optional[Union[str, pd.Timestamp]] = None,
        bond_price: Optional[float] = None,
    ) -> dict[float, float]:
        """
        Calculate the time to each payment from the valuation date.

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
        if valuation_date is not None:
            valuation_date = pd.to_datetime(valuation_date)
        else:
            valuation_date = self.issue_dt

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
