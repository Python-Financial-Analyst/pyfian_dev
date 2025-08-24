"""
zero_coupon_curve.py

Implements ZeroCouponCurve for zero-coupon rates.
"""

from typing import Optional, Union
import pandas as pd
from pyfian.time_value.rate_conversions import validate_yield_calculation_convention
from pyfian.utils.day_count import DayCountBase, get_day_count_convention
from pyfian.yield_curves.base_curve import YieldCurveBase
from pyfian.time_value import rate_conversions as rc


class ZeroCouponCurve(YieldCurveBase):
    """
    ZeroCouponCurve represents a yield curve for zero-coupon rates at different maturities.

    Parameters
    ----------
    zero_rates : dict
        Dictionary mapping maturities (in years) to zero-coupon rates (as decimals).
    curve_date : str or datetime-like
        Date of the curve.
    day_count_convention : str or DayCountBase, optional
        Day count convention to use (default is None). If None, "actual/365" will be used.
    yield_calculation_convention : str, optional
        Yield calculation convention to use (default is None).
        Supported conventions: "Annual", "BEY", "Continuous". If None, "Annual" will be used.
    """

    def __init__(
        self,
        zero_rates: dict[float, float],
        curve_date: Union[str, pd.Timestamp],
        day_count_convention: Optional[str | DayCountBase] = "actual/365",
        yield_calculation_convention: Optional[str] = None,
    ):
        self.curve_date = pd.to_datetime(curve_date)

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

        self.yield_calculation_convention: str = (
            "Annual"
            if yield_calculation_convention is None
            else validate_yield_calculation_convention(yield_calculation_convention)
        )
        self.zero_rates = self._prepare_zero_rates(zero_rates)

    def as_dict(self):
        """Convert the curve to a dictionary."""
        return {
            "zero_rates": self.zero_rates,
            "curve_date": self.curve_date,
            "day_count_convention": self.day_count_convention,
            "yield_calculation_convention": self.yield_calculation_convention,
        }

    def _prepare_zero_rates(self, zero_rates):
        """Prepare zero rates for the curve sorted by time and with time fractions."""
        # # Ensure all dates in dict are datetime objects
        # zero_rates = {pd.to_datetime(k): v for k, v in zero_rates.items()}
        # Ensure zero rates are sorted by maturity
        zero_rates = dict(sorted(zero_rates.items()))
        return zero_rates

    def discount_t(self, t: float, spread: float = 0) -> float:
        """
        Discount a cash flow by time t (in years).

        The formula used is:

        .. math:: PV = \\frac{1}{(1 + r)^{t}}

        where:

        - :math:`PV` is the present value
        - :math:`r` is the annual effective rate (AER) for the period
        - :math:`t` is the time in years

        Parameters
        ----------
        t : float
            Time in years to discount.
        spread : float
            Spread to add to the discount rate.

        Returns
        -------
        float
            Present value of the cash flow.

        """
        rate = self(t, spread=spread, yield_calculation_convention="Annual")
        return 1 / (1 + rate) ** t

    def discount_to_rate(
        self,
        discount_factor: float,
        t: float,
        spread: float,
        yield_calculation_convention: Optional[str] = None,
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

        """
        if yield_calculation_convention is None:
            yield_calculation_convention = self.yield_calculation_convention
        rate = (1 / discount_factor) ** (1 / t) - 1
        rate = rc.convert_yield(rate, "Annual", yield_calculation_convention)
        return rate - spread

    def discount_date(self, date: Union[str, pd.Timestamp], spread: float = 0) -> float:
        """
        Discount a cash flow to a specific date.

        The spread is added to the yield in the original curve.

        Parameters
        ----------
        date : Union[str, pd.Timestamp]
            Date to discount to.
        spread : float
            Spread to add to the discount rate.

        Returns
        -------
        float
            Present value of the cash flow.

        """
        t = self.day_count_convention.fraction(
            start=self.curve_date, current=pd.to_datetime(date)
        )
        return self.discount_t(t, spread)

    def __call__(
        self,
        t: float,
        yield_calculation_convention: Optional[str] = None,
        spread: float = 0,
    ) -> float:
        """
        Get the rate for a cash flow by time t (in years).

        The spread is added to the yield in the original curve.

        yield_calculation_convention can be used to transform the yield to different conventions.

        Parameters
        ----------
        t : float
            Time in years to discount.
        spread : float
            Spread to add to the discount rate.

        Returns
        -------
        float
            Rate for the cash flow.
        """
        if yield_calculation_convention is None:
            yield_calculation_convention = self.yield_calculation_convention
        return rc.convert_yield(
            self._get_rate(t) + spread,
            self.yield_calculation_convention,
            yield_calculation_convention,
        )

    def date_rate(
        self,
        date: Union[str, pd.Timestamp],
        yield_calculation_convention: Optional[str] = None,
        spread: float = 0,
    ) -> float:
        """
        Get the rate for a cash flow by date.

        The spread is added to the yield in the original curve.

        yield_calculation_convention can be used to transform the yield to different conventions.

        Parameters
        ----------
        date : Union[str, pd.Timestamp]
            Date to get the rate for.
        yield_calculation_convention : Optional[str]
            Yield calculation convention to use (default is None).
        spread : float
            Spread to add to the rate.

        Returns
        -------
        float
            Rate for the cash flow.
        """

        if yield_calculation_convention is None:
            yield_calculation_convention = self.yield_calculation_convention
        t = self.day_count_convention.fraction(
            start=self.curve_date, current=pd.to_datetime(date)
        )
        return rc.convert_yield(
            self._get_rate(t) + spread,
            self.yield_calculation_convention,
            yield_calculation_convention,
        )

    def _get_rate(self, t: float) -> float:
        # Simple linear interpolation between known maturities
        assert t >= 0, "Maturity must be non-negative"
        maturities = list(self.zero_rates.keys())
        if t <= maturities[0]:
            return self.zero_rates[maturities[0]]
        if t >= maturities[-1]:
            return self.zero_rates[maturities[-1]]
        else:
            for i in range(len(maturities) - 1):
                if maturities[i] <= t <= maturities[i + 1]:
                    r1, r2 = (
                        self.zero_rates[maturities[i]],
                        self.zero_rates[maturities[i + 1]],
                    )
                    t1, t2 = maturities[i], maturities[i + 1]
                    break
            return r1 + (r2 - r1) * (t - t1) / (t2 - t1)

    def __repr__(self):
        return f"ZeroCouponCurve(zero_rates={self.zero_rates}, curve_date={self.curve_date.strftime('%Y-%m-%d')})"


class ZeroCouponCurveByDate(ZeroCouponCurve):
    """
    ZeroCouponCurveByDate is a subclass of ZeroCouponCurve that allows for the input of zero rates as a function of dates.

    Parameters
    ----------
    zero_rates_dates : dict[pd.Timestamp | str, float]
        Dictionary with dates as keys and zero rates as values.
    curve_date : Union[str, pd.Timestamp]
        The curve settlement date.
    day_count_convention : str or DayCountBase, optional
        Day count convention to use (default is None). If None, "actual/365" will be used.
    yield_calculation_convention : str, optional
        Yield calculation convention to use (default is None).
        Supported conventions: "Annual", "BEY", "Continuous". If None, "Annual" will be used.
    """

    def __init__(
        self,
        zero_rates_dates: dict[pd.Timestamp | str, float],
        curve_date: Union[str, pd.Timestamp],
        day_count_convention: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ):
        self.curve_date = pd.to_datetime(curve_date)

        self.yield_calculation_convention: str = (
            "Annual"
            if yield_calculation_convention is None
            else validate_yield_calculation_convention(yield_calculation_convention)
        )

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

        self.zero_rates_dates = {
            pd.to_datetime(k): v for k, v in zero_rates_dates.items()
        }
        self.zero_rates = self._prepare_zero_rates(self.zero_rates_dates)

    def as_dict(self):
        return {
            "zero_rates_dates": self.zero_rates_dates,
            "curve_date": self.curve_date,
            "day_count_convention": self.day_count_convention,
            "yield_calculation_convention": self.yield_calculation_convention,
        }

    def _prepare_zero_rates(self, zero_rates_date: dict[pd.Timestamp, float]):
        # Convert the zero rates to a format that uses dates instead of times using the day count convention
        zero_rates = {}
        for d, r in zero_rates_date.items():
            t = self.day_count_convention.fraction(start=self.curve_date, current=d)
            zero_rates[t] = r
        return zero_rates
