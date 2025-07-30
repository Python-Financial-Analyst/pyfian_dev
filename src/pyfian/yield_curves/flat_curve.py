"""
flat_curve.py

Module for flat yield curve models. Includes FlatCurveLog (log/continuous rates) and
FlatCurveAER (annual effective rates).
"""

from typing import Union

import numpy as np
import pandas as pd


class FlatCurveLog:
    """
    FlatCurveLog represents a flat curve with continuously compounded (log) rates.

    Parameters
    ----------
    log_rate : float
        Continuously compounded rate (as decimal, e.g. 0.05 for 5%).
    curve_date : str or datetime-like
        Date of the curve.
    """

    def __init__(self, log_rate: float, curve_date: Union[str, pd.Timestamp]) -> None:
        self.log_rate: float = log_rate
        self.curve_date: pd.Timestamp = pd.to_datetime(curve_date)

    def discount_t(self, t: float) -> float:
        """
        Discount a cash flow by time t (in years) using log rate.

        Parameters
        ----------
        t : float
            Time in years.
        Returns
        -------
        float
            Discount factor.
        """
        return np.exp(-self.log_rate * t)

    def discount_date(self, date: Union[str, pd.Timestamp]) -> float:
        """
        Discount a cash flow by a target date using log rate.

        Parameters
        ----------
        date : str or datetime-like
            Target date for discounting.
        Returns
        -------
        float
            Discount factor.
        """
        t = (pd.to_datetime(date) - self.curve_date).days / 365
        return self.discount_t(t)

    def __call__(self, t: float) -> float:
        """
        Return the log rate at time horizon t (in years).

        Parameters
        ----------
        t : float
            Time in years.
        Returns
        -------
        float
            Log rate (continuously compounded).
        """
        return self.log_rate

    def date_rate(self, date: Union[str, pd.Timestamp]) -> float:
        """
        Return the log rate at a specified date.

        Parameters
        ----------
        date : str or datetime-like
            Target date for rate.
        Returns
        -------
        float
            Log rate (continuously compounded).
        """
        return self.log_rate

    def __repr__(self) -> str:
        return (
            f"FlatCurveLog(log_rate={self.log_rate:.4f}, "
            f"curve_date={self.curve_date.strftime('%Y-%m-%d')})"
        )


class FlatCurveAER:
    """
    FlatCurveAER represents a flat curve with annual effective rates (AER).

    Parameters
    ----------
    aer : float
        Annual effective rate (as decimal, e.g. 0.05 for 5%).
    curve_date : str or datetime-like
        Date of the curve.
    """

    def __init__(self, aer: float, curve_date: Union[str, pd.Timestamp]) -> None:
        self.aer: float = aer
        self.curve_date: pd.Timestamp = pd.to_datetime(curve_date)

    def discount_t(self, t: float) -> float:
        """
        Discount a cash flow by time t (in years) using annual effective rate.

        Parameters
        ----------
        t : float
            Time in years.
        Returns
        -------
        float
            Discount factor.
        """
        return 1 / (1 + self.aer) ** t

    def discount_date(self, date: Union[str, pd.Timestamp]) -> float:
        """
        Discount a cash flow by a target date using annual effective rate.

        Parameters
        ----------
        date : str or datetime-like
            Target date for discounting.
        Returns
        -------
        float
            Discount factor.
        """
        t = (pd.to_datetime(date) - self.curve_date).days / 365
        return self.discount_t(t)

    def __call__(self, t: float) -> float:
        """
        Return the annual effective rate at time horizon t (in years).

        Parameters
        ----------
        t : float
            Time in years.
        Returns
        -------
        float
            Annual effective rate.
        """
        return self.aer

    def date_rate(self, date: Union[str, pd.Timestamp]) -> float:
        """
        Return the annual effective rate at a specified date.

        Parameters
        ----------
        date : str or datetime-like
            Target date for rate.
        Returns
        -------
        float
            Annual effective rate.
        """
        return self.aer

    def __repr__(self) -> str:
        return (
            f"FlatCurveAER(aer={self.aer:.4f}, "
            f"curve_date={self.curve_date.strftime('%Y-%m-%d')})"
        )
