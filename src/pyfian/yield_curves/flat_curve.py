"""
flat_curve.py

Module for flat yield curve models. Includes FlatCurveLog (log/continuous rates),
FlatCurveAER (annual effective rates), and FlatCurveBEY (bond equivalent yields).

Examples
--------
>>> from pyfian.yield_curves.flat_curve import FlatCurveLog, FlatCurveAER, FlatCurveBEY
>>> curve_log = FlatCurveLog(0.05, "2020-01-01")
>>> curve_log.discount_t(1)
0.951229424500714
>>> curve_log.discount_date("2021-01-01")
0.951229424500714
>>> curve_log(1)
0.05
>>> curve_log(1, yield_calculation_convention="Annual")
0.05127109637602412
>>> curve_log(1, yield_calculation_convention="BEY")
0.05128205128205128
>>> curve_log(1, yield_calculation_convention="Continuous")
0.05
>>> curve_log(1, yield_calculation_convention="Unknown")
Traceback (most recent call last):
    ...
ValueError: Unknown yield calculation convention: Unknown

>>> curve_aer = FlatCurveAER(0.05, "2020-01-01")
>>> curve_aer.discount_t(1)
0.9523809523809523
>>> curve_aer.discount_date("2021-01-01")
0.9523809523809523
>>> curve_aer(1)
0.05
>>> curve_aer(1, yield_calculation_convention="BEY")
0.04999999999999999
>>> curve_aer(1, yield_calculation_convention="Continuous")
0.04879016416943205
>>> curve_aer(1, yield_calculation_convention="Unknown")
Traceback (most recent call last):
    ...
ValueError: Unknown yield calculation convention: Unknown

>>> curve_bey = FlatCurveBEY(0.05, "2020-01-01")
>>> curve_bey.discount_t(1)
0.975609756097561
>>> curve_bey.discount_date("2021-01-01")
0.975609756097561
>>> curve_bey(1)
0.05061728395061728
>>> curve_bey(1, yield_calculation_convention="BEY")
0.05
>>> curve_bey(1, yield_calculation_convention="Continuous")
0.04939702358655452
>>> curve_bey(1, yield_calculation_convention="Unknown")
Traceback (most recent call last):
    ...
ValueError: Unknown yield calculation convention: Unknown
"""

from typing import Optional, Union
import numpy as np
import pandas as pd
from pyfian.visualization.mixins import YieldCurvePlotMixin
from pyfian.yield_curves.base_curve import YieldCurveBase
from pyfian.time_value import rate_conversions as rc


class FlatCurveLog(YieldCurvePlotMixin, YieldCurveBase):
    """
    FlatCurveLog represents a flat curve with continuously compounded (log) rates.

    Parameters
    ----------
    log_rate : float
        Continuously compounded rate (as decimal, e.g. 0.05 for 5%).
    curve_date : str or datetime-like
        Date of the curve.
    """

    def __init__(
        self,
        log_rate: float,
        curve_date: Union[str, pd.Timestamp],
        yield_calculation_convention: str = "Continuous",
    ) -> None:
        self.log_rate: float = log_rate
        self.curve_date: pd.Timestamp = pd.to_datetime(curve_date)
        self.yield_calculation_convention: str = yield_calculation_convention

    def discount_t(self, t: float, spread: float = 0) -> float:
        """
        Discount a cash flow by time t (in years) using log rate.

        The spread is added to the yield in the original curve.

        Parameters
        ----------
        t : float
            Time in years.
        spread : float, optional
            Spread to add to the discount rate. Defaults to 0.

        Returns
        -------
        float
            Discount factor.

        Examples
        --------
        >>> curve = FlatCurveLog(0.05, "2020-01-01")
        >>> curve.discount_t(1)
        0.951229424500714
        >>> # Equivalent to: assert curve.discount_t(1) == pytest.approx(np.exp(-0.05))
        """
        return np.exp(-(self.log_rate + spread) * t)

    def discount_date(self, date: Union[str, pd.Timestamp], spread: float = 0) -> float:
        """
        Discount a cash flow by a target date using log rate.

        The spread is added to the yield in the original curve.

        Parameters
        ----------
        date : str or datetime-like
            Target date for discounting.
        spread : float, optional
            Spread to add to the discount rate. Defaults to 0.

        Returns
        -------
        float
            Discount factor.

        Examples
        --------
        >>> curve = FlatCurveLog(0.05, "2020-01-01")
        >>> curve.discount_date("2021-01-01")
        0.951229424500714
        """
        t = (pd.to_datetime(date) - self.curve_date).days / 365
        return self.discount_t(t, spread)

    def __call__(
        self,
        t: float,
        yield_calculation_convention: Optional[str] = None,
        spread: float = 0,
    ) -> float:
        """
        Return the log rate at time horizon t (in years).

        The spread is added to the yield in the original curve.

        yield_calculation_convention can be used to transform the yield to different conventions.

        Parameters
        ----------
        t : float
            Time in years.
        yield_calculation_convention : str, optional
            Yield calculation convention to use. Must be one of "Annual", "BEY", "Continuous".
        spread : float, optional
            Spread to add to the yield. Defaults to 0.

        Returns
        -------
        float
            Log rate (continuously compounded).

        Examples
        --------
        >>> curve = FlatCurveLog(0.05, "2020-01-01")
        >>> curve(1)
        0.05
        >>> curve(1, yield_calculation_convention="Annual")
        np.expm1(0.05)
        >>> curve(1, yield_calculation_convention="BEY")
        2 * ((1 + np.expm1(0.05)) ** 0.5 - 1)
        >>> curve(1, yield_calculation_convention="Continuous")
        0.05
        >>> curve(1, yield_calculation_convention="Unknown")
        Traceback (most recent call last):
            ...
        ValueError: Unknown yield calculation convention: Unknown
        """
        if yield_calculation_convention is None:
            yield_calculation_convention = self.yield_calculation_convention

        # Use the appropriate yield calculation convention
        if yield_calculation_convention == "Annual":
            return rc.continuous_to_effective(self.log_rate + spread)
        elif yield_calculation_convention == "BEY":
            return rc.effective_annual_to_bey(
                rc.continuous_to_effective(self.log_rate + spread)
            )
        elif yield_calculation_convention == "Continuous":
            return self.log_rate + spread
        else:
            raise ValueError(
                f"Unknown yield calculation convention: {yield_calculation_convention}"
            )

    def date_rate(
        self,
        date: Union[str, pd.Timestamp],
        yield_calculation_convention: Optional[str] = None,
        spread: float = 0,
    ) -> float:
        """
        Return the log rate at a specified date.

        The spread is added to the yield in the original curve.

        yield_calculation_convention can be used to transform the yield to different conventions.

        Parameters
        ----------
        date : str or datetime-like
            Target date for rate.
        yield_calculation_convention : str, optional
            Yield calculation convention to use. Must be one of "Annual", "BEY", "Continuous".
        spread : float, optional
            Spread to add to the yield. Defaults to 0.

        Returns
        -------
        float
            Log rate (continuously compounded).

        Examples
        --------
        >>> curve = FlatCurveLog(0.05, "2020-01-01")
        >>> curve.date_rate("2022-01-01")
        0.05
        >>> curve.date_rate("2022-01-01", yield_calculation_convention="Annual")
        np.expm1(0.05)
        >>> curve.date_rate("2022-01-01", yield_calculation_convention="BEY")
        2 * ((1 + np.expm1(0.05)) ** 0.5 - 1)
        >>> curve.date_rate("2022-01-01", yield_calculation_convention="Continuous")
        0.05
        >>> curve.date_rate("2022-01-01", yield_calculation_convention="Unknown")
        Traceback (most recent call last):
            ...
        ValueError: Unknown yield calculation convention: Unknown
        """
        if yield_calculation_convention is None:
            yield_calculation_convention = self.yield_calculation_convention

        if yield_calculation_convention == "Annual":
            return rc.continuous_to_effective(self.log_rate + spread)
        elif yield_calculation_convention == "BEY":
            return rc.effective_annual_to_bey(
                rc.continuous_to_effective(self.log_rate + spread)
            )
        elif yield_calculation_convention == "Continuous":
            return self.log_rate + spread
        else:
            raise ValueError(
                f"Unknown yield calculation convention: {yield_calculation_convention}"
            )

    def __repr__(self) -> str:
        return (
            f"FlatCurveLog(log_rate={self.log_rate:.4f}, "
            f"curve_date={self.curve_date.strftime('%Y-%m-%d')})"
        )


class FlatCurveAER(YieldCurvePlotMixin, YieldCurveBase):
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
        self.yield_calculation_convention: str = "Annual"

    def discount_t(self, t: float, spread: float = 0) -> float:
        """
        Discount a cash flow by time t (in years) using annual effective rate.

        The spread is added to the yield in the original curve.

        Parameters
        ----------
        t : float
            Time in years.
        spread : float, optional
            Spread to add to the yield. Defaults to 0.

        Returns
        -------
        float
            Discount factor.

        Examples
        --------
        >>> curve = FlatCurveAER(0.05, "2020-01-01")
        >>> curve.discount_t(1)
        0.9523809523809523
        """
        return 1 / (1 + self.aer + spread) ** t

    def discount_date(self, date: Union[str, pd.Timestamp], spread: float = 0) -> float:
        """
        Discount a cash flow by a target date using annual effective rate.

        The spread is added to the yield in the original curve.

        Parameters
        ----------
        date : str or datetime-like
            Target date for discounting.
        spread : float, optional
            Spread to add to the discount rate. Defaults to 0.

        Returns
        -------
        float
            Discount factor.

        Examples
        --------
        >>> curve = FlatCurveAER(0.05, "2020-01-01")
        >>> curve.discount_date("2021-01-01")
        0.9523809523809523
        """
        t = (pd.to_datetime(date) - self.curve_date).days / 365
        return self.discount_t(t, spread)

    def __call__(
        self,
        t: float,
        yield_calculation_convention: Optional[str] = None,
        spread: float = 0,
    ) -> float:
        """
        Return the annual effective rate at time horizon t (in years).

        The spread is added to the yield in the original curve.

        yield_calculation_convention can be used to transform the yield to different conventions.

        Parameters
        ----------
        t : float
            Time in years.
        yield_calculation_convention : str, optional
            Yield calculation convention to use. Must be one of "Annual", "BEY", "Continuous".
        spread : float, optional
            Spread to add to the yield. Defaults to 0.

        Returns
        -------
        float
            Annual effective rate.

        Examples
        --------
        >>> curve = FlatCurveAER(0.05, "2020-01-01")
        >>> curve(1)
        0.05
        >>> curve(1, yield_calculation_convention="BEY")
        2 * ((1 + 0.05) ** 0.5 - 1)
        >>> curve(1, yield_calculation_convention="Continuous")
        np.log(1 + 0.05)
        >>> curve(1, yield_calculation_convention="Unknown")
        Traceback (most recent call last):
            ...
        ValueError: Unknown yield calculation convention: Unknown
        """
        if yield_calculation_convention is None:
            yield_calculation_convention = self.yield_calculation_convention

        if yield_calculation_convention == "Annual":
            return self.aer + spread
        elif yield_calculation_convention == "BEY":
            return rc.effective_annual_to_bey(self.aer + spread)
        elif yield_calculation_convention == "Continuous":
            return rc.effective_to_continuous(self.aer + spread)
        else:
            raise ValueError(
                f"Unknown yield calculation convention: {yield_calculation_convention}"
            )

    def date_rate(
        self,
        date: Union[str, pd.Timestamp],
        yield_calculation_convention: Optional[str] = None,
        spread: float = 0,
    ) -> float:
        """
        Return the annual effective rate at a specified date.

        The spread is added to the yield in the original curve.

        yield_calculation_convention can be used to transform the yield to different conventions.

        Parameters
        ----------
        date : str or datetime-like
            Target date for rate.
        yield_calculation_convention : str, optional
            Yield calculation convention to use. Must be one of "Annual", "BEY", "Continuous".
        spread : float, optional
            Spread to add to the yield. Defaults to 0.

        Returns
        -------
        float
            Annual effective rate.

        Examples
        --------
        >>> curve = FlatCurveAER(0.05, "2020-01-01")
        >>> curve.date_rate("2022-01-01")
        0.05
        >>> curve.date_rate("2022-01-01", yield_calculation_convention="BEY")
        2 * ((1 + 0.05) ** 0.5 - 1)
        >>> curve.date_rate("2022-01-01", yield_calculation_convention="Continuous")
        np.log(1 + 0.05)
        >>> curve.date_rate("2022-01-01", yield_calculation_convention="Unknown")
        Traceback (most recent call last):
            ...
        ValueError: Unknown yield calculation convention: Unknown
        """
        if yield_calculation_convention is None:
            yield_calculation_convention = self.yield_calculation_convention

        if yield_calculation_convention == "Annual":
            return self.aer + spread
        elif yield_calculation_convention == "BEY":
            return rc.effective_annual_to_bey(self.aer + spread)
        elif yield_calculation_convention == "Continuous":
            return rc.effective_to_continuous(self.aer + spread)
        else:
            raise ValueError(
                f"Unknown yield calculation convention: {yield_calculation_convention}"
            )

    def __repr__(self) -> str:
        return (
            f"FlatCurveAER(aer={self.aer:.4f}, "
            f"curve_date={self.curve_date.strftime('%Y-%m-%d')})"
        )


class FlatCurveBEY(YieldCurvePlotMixin, YieldCurveBase):
    """
    FlatCurveBEY represents a flat curve with bond equivalent yields (BEY).

    Parameters
    ----------
    bey : float
        Bond equivalent yield (as decimal, e.g. 0.05 for 5%).
    curve_date : str or datetime-like
        Date of the curve.
    """

    def __init__(self, bey: float, curve_date: Union[str, pd.Timestamp]) -> None:
        self.bey: float = bey
        self.curve_date: pd.Timestamp = pd.to_datetime(curve_date)
        self.yield_calculation_convention: str = "Annual"

    def discount_t(self, t: float, spread: float = 0) -> float:
        """
        Discount a cash flow by time t (in years) using annual effective rate.

        The spread is added to the yield in the original curve.

        Parameters
        ----------
        t : float
            Time in years.
        spread : float, optional
            Spread to add to the discount rate. Defaults to 0.

        Returns
        -------
        float
            Discount factor.

        Examples
        --------
        >>> curve = FlatCurveBEY(0.05, "2020-01-01")
        >>> curve.discount_t(1)
        0.975609756097561
        """
        return 1 / (1 + (self.bey + spread) / 2) ** (t * 2)

    def discount_date(self, date: Union[str, pd.Timestamp], spread: float = 0) -> float:
        """
        Discount a cash flow by a target date using annual effective rate.

        The spread is added to the yield in the original curve.

        Parameters
        ----------
        date : str or datetime-like
            Target date for discounting.
        spread : float, optional
            Spread to add to the discount rate. Defaults to 0.

        Returns
        -------
        float
            Discount factor.

        Examples
        --------
        >>> curve = FlatCurveBEY(0.05, "2020-01-01")
        >>> curve.discount_date("2021-01-01")
        0.975609756097561
        """
        t = (pd.to_datetime(date) - self.curve_date).days / 365
        return self.discount_t(t, spread=spread)

    def __call__(
        self,
        t: float,
        yield_calculation_convention: Optional[str] = None,
        spread: float = 0,
    ) -> float:
        """
        Return the annual effective rate at time horizon t (in years).

        The spread is added to the yield in the original curve.

        yield_calculation_convention can be used to transform the yield to different conventions.

        Parameters
        ----------
        t : float
            Time in years.
        yield_calculation_convention : str, optional
            Yield calculation convention to use. Must be one of "Annual", "BEY", "Continuous".
        spread : float, optional
            Spread to add to the yield. Defaults to 0.

        Returns
        -------
        float
            Annual effective rate.

        Examples
        --------
        >>> curve = FlatCurveBEY(0.05, "2020-01-01")
        >>> curve(1)
        (1 + 0.05 / 2) ** 2 - 1
        >>> curve(1, yield_calculation_convention="Annual")
        (1 + 0.05 / 2) ** 2 - 1
        >>> curve(1, yield_calculation_convention="BEY")
        0.05
        >>> curve(1, yield_calculation_convention="Continuous")
        np.log(1 + ((1 + 0.05 / 2) ** 2 - 1))
        >>> curve(1, yield_calculation_convention="Unknown")
        Traceback (most recent call last):
            ...
        ValueError: Unknown yield calculation convention: Unknown
        """
        if yield_calculation_convention is None:
            yield_calculation_convention = self.yield_calculation_convention

        if yield_calculation_convention == "Annual":
            return rc.bey_to_effective_annual(self.bey + spread)
        elif yield_calculation_convention == "BEY":
            return self.bey + spread
        elif yield_calculation_convention == "Continuous":
            return rc.effective_to_continuous(
                rc.bey_to_effective_annual(self.bey + spread)
            )
        else:
            raise ValueError(
                f"Unknown yield calculation convention: {yield_calculation_convention}"
            )

    def date_rate(
        self,
        date: Union[str, pd.Timestamp],
        yield_calculation_convention: Optional[str] = None,
        spread: float = 0,
    ) -> float:
        """
        Return the annual effective rate at a specified date.

        The spread is added to the yield in the original curve.

        yield_calculation_convention can be used to transform the yield to different conventions.

        Parameters
        ----------
        date : str or datetime-like
            Target date for rate.
        yield_calculation_convention : str, optional
            Yield calculation convention to use. Must be one of "Annual", "BEY", "Continuous".

        Returns
        -------
        float
            Annual effective rate.

        Examples
        --------
        >>> curve = FlatCurveBEY(0.05, "2020-01-01")
        >>> curve.date_rate("2022-01-01")
        (1 + 0.05 / 2) ** 2 - 1
        >>> curve.date_rate("2022-01-01", yield_calculation_convention="Annual")
        (1 + 0.05 / 2) ** 2 - 1
        >>> curve.date_rate("2022-01-01", yield_calculation_convention="BEY")
        0.05
        >>> curve.date_rate("2022-01-01", yield_calculation_convention="Continuous")
        np.log(1 + ((1 + 0.05 / 2) ** 2 - 1))
        >>> curve.date_rate("2022-01-01", yield_calculation_convention="Unknown")
        Traceback (most recent call last):
            ...
        ValueError: Unknown yield calculation convention: Unknown
        """
        if yield_calculation_convention is None:
            yield_calculation_convention = self.yield_calculation_convention

        if yield_calculation_convention == "Annual":
            return rc.bey_to_effective_annual(self.bey + spread)
        elif yield_calculation_convention == "BEY":
            return self.bey + spread
        elif yield_calculation_convention == "Continuous":
            return rc.effective_to_continuous(
                rc.bey_to_effective_annual(self.bey + spread)
            )
        else:
            raise ValueError(
                f"Unknown yield calculation convention: {yield_calculation_convention}"
            )

    def __repr__(self) -> str:
        return (
            f"FlatCurveBEY(bey={self.bey:.4f}, "
            f"curve_date={self.curve_date.strftime('%Y-%m-%d')})"
        )
