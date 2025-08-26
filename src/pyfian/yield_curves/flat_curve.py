"""
flat_curve.py

Module for flat yield curve models. Implements:

- FlatCurveLog: Flat curve with continuously compounded (log) rates.
- FlatCurveAER: Flat curve with annual effective rates (AER).
- FlatCurveBEY: Flat curve with bond equivalent yields (BEY).

Each class provides a different convention for representing flat yield curves, useful for pricing, discounting, and rate conversions in fixed income analytics.

Examples
--------
>>> from pyfian.yield_curves.flat_curve import FlatCurveLog, FlatCurveAER, FlatCurveBEY
>>> curve_log = FlatCurveLog(0.05, "2020-01-01")
>>> curve_log.discount_t(1)
0.951229424500714
>>> curve_log.discount_date("2021-01-01")
0.951229424500714
>>> curve_log.get_rate(1)
0.05
>>> curve_log.get_rate(1, yield_calculation_convention="Annual")
0.05127109637602412
>>> curve_log.get_rate(1, yield_calculation_convention="BEY")
0.05128205128205128
>>> curve_log.get_rate(1, yield_calculation_convention="Continuous")
0.05
>>> curve_log.get_rate(1, yield_calculation_convention="Unknown")
Traceback (most recent call last):
    ...
ValueError: Unknown yield calculation convention: Unknown

>>> curve_aer = FlatCurveAER(0.05, "2020-01-01")
>>> curve_aer.discount_t(1)
0.9523809523809523
>>> curve_aer.discount_date("2021-01-01")
0.9523809523809523
>>> curve_aer.get_rate(1)
0.05
>>> curve_aer.get_rate(1, yield_calculation_convention="BEY")
0.04999999999999999
>>> curve_aer.get_rate(1, yield_calculation_convention="Continuous")
0.04879016416943205
>>> curve_aer.get_rate(1, yield_calculation_convention="Unknown")
Traceback (most recent call last):
    ...
ValueError: Unknown yield calculation convention: Unknown

>>> curve_bey = FlatCurveBEY(0.05, "2020-01-01")
>>> curve_bey.discount_t(1)
0.9518143961927424
>>> curve_bey.discount_date("2021-01-01")
0.9518143961927424
>>> curve_bey.get_rate(1, yield_calculation_convention="Annual")
0.050625
>>> curve_bey.get_rate(1, yield_calculation_convention="BEY")
0.05
>>> curve_bey.get_rate(1, yield_calculation_convention="Continuous")
0.049385225180742925
>>> curve_bey.get_rate(1, yield_calculation_convention="Unknown")
Traceback (most recent call last):
    ...
ValueError: Unknown yield calculation convention: Unknown
"""

from typing import Optional, Union
import numpy as np
import pandas as pd
from pyfian.utils.day_count import DayCountBase, get_day_count_convention
from pyfian.visualization.mixins import YieldCurvePlotMixin
from pyfian.yield_curves.base_curve import YieldCurveBase
from pyfian.time_value import rate_conversions as rc


class FlatCurveLog(YieldCurvePlotMixin, YieldCurveBase):
    """
    FlatCurveLog represents a flat curve with continuously compounded (log) rates.

    This class is implemented to model a yield curve where the rate is constant and compounded continuously. It is useful for pricing and discounting cash flows under the continuous compounding convention, which is common in quantitative finance.

    Parameters
    ----------
    log_rate : float
        Continuously compounded rate (as decimal, e.g. 0.05 for 5%).
    curve_date : str or datetime-like
        The curve settlement date.
    day_count_convention : str or DayCountBase, optional
        The day count convention to use. Defaults to "actual/365".
    """

    def __init__(
        self,
        log_rate: float,
        curve_date: Union[str, pd.Timestamp],
        day_count_convention: Optional[str | DayCountBase] = "actual/365",
    ) -> None:
        self.log_rate: float = log_rate
        self.curve_date: pd.Timestamp = pd.to_datetime(curve_date)
        self.yield_calculation_convention: str = "Continuous"
        # Raise if day_count_convention is neither str nor DayCountBase
        if not isinstance(day_count_convention, (str, DayCountBase)):
            raise TypeError(
                "day_count_convention must be either a string or a DayCountBase instance."
            )
        self.day_count_convention: DayCountBase = (
            get_day_count_convention(day_count_convention)
            if isinstance(day_count_convention, str)
            else day_count_convention
        )

    def as_dict(self) -> dict:
        """
        Return curve parameters and metadata as a dictionary.
        """
        return {
            "log_rate": self.log_rate,
            "curve_date": self.curve_date,
        }

    def discount_t(self, t: float, spread: float = 0) -> float:
        """
        Discount a cash flow by time t (in years) using log rate.

        The spread is added to the yield in the original curve.

        The formula used is:

        .. math::

            D(t) = e^{-(r + s) t}

        where:
        - D(t) is the discount factor at time t
        - r is the continuously compounded rate for the period
        - s is the spread

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

    def discount_to_rate(
        self, discount_factor: float, t: float, spread: float = 0
    ) -> float:
        """
        Convert a discount factor for a period t to a rate.

        The formula used is:

        .. math::

            r = -\\frac{\\log(D(t))}{t} - s

        where:
        - D(t) is the discount factor at time t
        - r is the Bond Equivalent Yield (BEY) for the period
        - s is the spread

        Parameters
        ----------
        discount_factor : float
            Discount factor to convert.
        t : float
            Time period (in years).
        spread : float, optional
            Spread to subtract from the rate to get a Risk Free rate. Defaults to 0.

        Returns
        -------
        float
            Continuously compounded rate (as decimal).

        Examples
        --------
        >>> curve = FlatCurveLog(0.05, "2020-01-01")
        >>> curve.discount_to_rate(0.951229424500714, 1)
        0.05
        >>> curve.discount_to_rate(0.951229424500714, 1, spread=0.01)
        0.04
        """
        # We need to solve for the rate in the equation:
        # discount_factor = np.exp(-(log_rate + spread) * t)
        # Taking the natural log of both sides:
        # np.log(discount_factor) = -(log_rate + spread) * t
        # Rearranging gives us:
        # log_rate + spread = -np.log(discount_factor) / t
        # log_rate = -np.log(discount_factor) / t - spread

        return -np.log(discount_factor) / t - spread

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
        t = self.day_count_convention.fraction(
            start=self.curve_date, current=pd.to_datetime(date)
        )
        return self.discount_t(t, spread)

    def get_rate(
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
        >>> curve.get_rate(1)
        0.05
        >>> curve.get_rate(1, yield_calculation_convention="Annual")
        np.expm1(0.05)
        >>> curve.get_rate(1, yield_calculation_convention="BEY")
        2 * ((1 + np.expm1(0.05)) ** 0.5 - 1)
        >>> curve.get_rate(1, yield_calculation_convention="Continuous")
        0.05
        >>> curve.get_rate(1, yield_calculation_convention="Unknown")
        Traceback (most recent call last):
            ...
        ValueError: Unknown yield calculation convention: Unknown
        """
        if yield_calculation_convention is None:
            yield_calculation_convention = self.yield_calculation_convention

        # Use the appropriate yield calculation convention
        return rc.convert_yield(
            self.log_rate + spread, "Continuous", yield_calculation_convention
        )

    def _get_t(self, t, spread=0):
        return self.log_rate + spread

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

        return rc.convert_yield(
            self.log_rate + spread, "Continuous", yield_calculation_convention
        )

    def __repr__(self) -> str:
        return (
            f"FlatCurveLog(log_rate={self.log_rate:.4f}, "
            f"curve_date={self.curve_date.strftime('%Y-%m-%d')})"
        )


class FlatCurveAER(YieldCurvePlotMixin, YieldCurveBase):
    """
    FlatCurveAER represents a flat curve with annual effective rates (AER).

    This class is implemented to model a yield curve where the rate is constant and compounded annually. It is useful for pricing and discounting cash flows under the annual effective rate convention, which is standard in many fixed income markets.

    Parameters
    ----------
    aer : float
        Annual effective rate (as decimal, e.g. 0.05 for 5%).
    curve_date : str or datetime-like
        The curve settlement date.
    day_count_convention : str or DayCountBase, optional
        The day count convention to use. Defaults to "actual/365".
    """

    def __init__(
        self,
        aer: float,
        curve_date: Union[str, pd.Timestamp],
        day_count_convention: Optional[str | DayCountBase] = "actual/365",
    ) -> None:
        self.aer: float = aer
        self.curve_date: pd.Timestamp = pd.to_datetime(curve_date)
        self.yield_calculation_convention: str = "Annual"
        # Raise if day_count_convention is neither str nor DayCountBase
        if not isinstance(day_count_convention, (str, DayCountBase)):
            raise TypeError(
                "day_count_convention must be either a string or a DayCountBase instance."
            )
        self.day_count_convention: DayCountBase = (
            get_day_count_convention(day_count_convention)
            if isinstance(day_count_convention, str)
            else day_count_convention
        )

    def as_dict(self) -> dict:
        """
        Return curve parameters and metadata as a dictionary.
        """
        return {
            "aer": self.aer,
            "curve_date": self.curve_date,
        }

    def discount_t(self, t: float, spread: float = 0) -> float:
        """
        Discount a cash flow by time t (in years) using annual effective rate.

        The spread is added to the yield in the original curve.

        The formula used is

        .. math::

            D(t) = (1 + r + s)^{-t}

        where
        - D(t) is the discount factor at time t
        - r is the annual effective rate (AER) for the period
        - s is the spread

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

    def discount_to_rate(
        self, discount_factor: float, t: float, spread: float = 0
    ) -> float:
        """
        Convert a discount factor for a period t to a rate.

        The formula used is:

        .. math::

            r = (\\frac{1}{D(t)})^{\\frac{1}{t}} - 1 - s

        where:
        - D(t) is the discount factor at time t
        - r is the Bond Equivalent Yield (BEY) for the period
        - s is the spread

        Parameters
        ----------
        discount_factor : float
            Discount factor.
        t : float
            Time in years.
        spread : float, optional
            Spread to subtract from the yield to get a Risk Free rate. Defaults to 0.

        Returns
        -------
        float
            Annual effective rate (AER).

        Examples
        --------
        >>> curve = FlatCurveAER(0.05, "2020-01-01")
        >>> curve.discount_to_rate(0.9523809523809523, 1)
        0.05
        >>> curve.discount_to_rate(0.9523809523809523, 1, spread=0.01)
        0.04
        """
        # We need to solve for the rate in the equation:
        # discount_factor = 1 / (1 + aer + spread) ** t
        # Inverting this gives us:
        # (1 + aer + spread) ** t = 1 / discount_factor
        # Taking the t-th root:
        # 1 + aer + spread = (1 / discount_factor) ** (1 / t)
        # Finally, we can solve for the rate:
        # aer = (1 / discount_factor) ** (1 / t) - 1 - spread
        return (1 / discount_factor) ** (1 / t) - 1 - spread

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
        t = self.day_count_convention.fraction(
            start=self.curve_date, current=pd.to_datetime(date)
        )
        return self.discount_t(t, spread)

    def get_rate(
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
        >>> curve.get_rate(1)
        0.05
        >>> curve.get_rate(1, yield_calculation_convention="BEY")
        2 * ((1 + 0.05) ** 0.5 - 1)
        >>> curve.get_rate(1, yield_calculation_convention="Continuous")
        np.log(1 + 0.05)
        >>> curve.get_rate(1, yield_calculation_convention="Unknown")
        Traceback (most recent call last):
            ...
        ValueError: Unknown yield calculation convention: Unknown
        """
        if yield_calculation_convention is None:
            yield_calculation_convention = self.yield_calculation_convention

        return rc.convert_yield(
            self.aer + spread, "Annual", yield_calculation_convention
        )

    def _get_t(self, t, spread=0):
        return self.aer + spread

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

        return rc.convert_yield(
            self.aer + spread, "Annual", yield_calculation_convention
        )

    def __repr__(self) -> str:
        return (
            f"FlatCurveAER(aer={self.aer:.4f}, "
            f"curve_date={self.curve_date.strftime('%Y-%m-%d')})"
        )


class FlatCurveBEY(YieldCurvePlotMixin, YieldCurveBase):
    """
    FlatCurveBEY represents a flat curve with bond equivalent yields (BEY).

    This class is implemented to model a yield curve where the rate is constant and quoted as a bond equivalent yield. BEY is a market convention for quoting yields on semiannual coupon bonds.

    Parameters
    ----------
    bey : float
        Bond equivalent yield (as decimal, e.g. 0.05 for 5%).
    curve_date : str or datetime-like
        The curve settlement date.
    day_count_convention : str or DayCountBase, optional
        The day count convention to use. Defaults to "30/360".
    """

    def __init__(
        self,
        bey: float,
        curve_date: Union[str, pd.Timestamp],
        day_count_convention: Optional[str | DayCountBase] = "30/360",
    ) -> None:
        self.bey: float = bey
        self.curve_date: pd.Timestamp = pd.to_datetime(curve_date)
        self.yield_calculation_convention: str = "BEY"
        # Raise if day_count_convention is neither str nor DayCountBase
        if not isinstance(day_count_convention, (str, DayCountBase)):
            raise TypeError(
                "day_count_convention must be either a string or a DayCountBase instance."
            )
        self.day_count_convention: DayCountBase = (
            get_day_count_convention(day_count_convention)
            if isinstance(day_count_convention, str)
            else day_count_convention
        )

    def as_dict(self) -> dict:
        """
        Return curve parameters and metadata as a dictionary.
        """
        return {
            "bey": self.bey,
            "curve_date": self.curve_date,
        }

    def discount_t(self, t: float, spread: float = 0) -> float:
        """
        Discount a cash flow by time t (in years) using annual effective rate.

        The spread is added to the yield in the original curve.

        The formula used is

        .. math::

            D(t) = (1 + (r + s) / 2 )^{-t * 2}

        where
        - D(t) is the discount factor at time t
        - r is the Bond Equivalent Yield (BEY) for the period
        - s is the spread

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
        0.9518143961927424
        """
        return 1 / (1 + (self.bey + spread) / 2) ** (t * 2)

    def discount_to_rate(
        self, discount_factor: float, t: float, spread: float = 0
    ) -> float:
        """
        Convert a discount factor for a period t to a rate.

        The formula used is:

        .. math::

            r = 2 * ((\\frac{1}{D(t)})^{\\frac{1}{t * 2}} - 1) - s

        where:
        - D(t) is the discount factor at time t
        - r is the Bond Equivalent Yield (BEY) for the period
        - s is the spread

        Parameters
        ----------
        discount_factor : float
            Discount factor.
        t : float
            Time in years.
        spread : float, optional
            Spread to subtract from the yield to get a Risk Free rate. Defaults to 0.

        Returns
        -------
        float
            Bond Equivalent Yield (BEY).

        Examples
        --------
        >>> curve = FlatCurveAER(0.05, "2020-01-01")
        >>> curve.discount_to_rate(0.975609756097561, 1)
        0.05
        >>> curve.discount_to_rate(0.9523809523809523, 1, spread=0.01)
        0.04
        """
        # We need to solve for the rate in the equation:
        # discount_factor = 1 / (1 + (bey + spread) / 2) ** (t * 2)
        # Inverting this gives us:
        # (1 + (bey + spread) / 2) ** (t * 2) = 1 / discount_factor
        # Taking the t-th root:
        # 1 + (bey + spread) / 2 = (1 / discount_factor) ** (1 / (t * 2))
        # Finally, we can solve for the rate:
        # bey = 2 * ((1 / discount_factor) ** (1 / (t * 2)) - 1) - spread
        return 2 * ((1 / discount_factor) ** (1 / (t * 2)) - 1) - spread

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
        t = self.day_count_convention.fraction(
            start=self.curve_date, current=pd.to_datetime(date)
        )
        return self.discount_t(t, spread=spread)

    def get_rate(
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
        >>> curve.get_rate(1)
        0.05
        >>> curve.get_rate(1, yield_calculation_convention="Annual")
        0.050625
        >>> curve.get_rate(1, yield_calculation_convention="BEY")
        0.05
        >>> curve.get_rate(1, yield_calculation_convention="Continuous")
        0.049385225180742925
        >>> curve.get_rate(1, yield_calculation_convention="Unknown")
        Traceback (most recent call last):
            ...
        ValueError: Unknown yield calculation convention: Unknown
        """
        if yield_calculation_convention is None:
            yield_calculation_convention = self.yield_calculation_convention

        return rc.convert_yield(self.bey + spread, "BEY", yield_calculation_convention)

    def _get_t(self, t, spread=0):
        return self.bey + spread

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
        0.05
        >>> curve.date_rate("2022-01-01", yield_calculation_convention="Annual")
        0.050625
        >>> curve.date_rate("2022-01-01", yield_calculation_convention="BEY")
        0.05
        >>> curve.date_rate("2022-01-01", yield_calculation_convention="Continuous")
        0.049385225180742925
        >>> curve.date_rate("2022-01-01", yield_calculation_convention="Unknown")
        Traceback (most recent call last):
            ...
        ValueError: Unknown yield calculation convention: Unknown
        """
        if yield_calculation_convention is None:
            yield_calculation_convention = self.yield_calculation_convention

        return rc.convert_yield(self.bey + spread, "BEY", yield_calculation_convention)

    def __repr__(self) -> str:
        return (
            f"FlatCurveBEY(bey={self.bey:.4f}, "
            f"curve_date={self.curve_date.strftime('%Y-%m-%d')})"
        )
