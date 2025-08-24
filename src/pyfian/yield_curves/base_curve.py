from abc import ABC, abstractmethod
from typing import Optional, Union
import pandas as pd

from pyfian.utils.day_count import DayCountBase


# Abstract base class for yield curves


class YieldCurveBase(ABC):
    """
    Abstract base class for yield curves.
    """

    curve_date: pd.Timestamp
    day_count_convention: DayCountBase

    @abstractmethod
    def discount_t(self, t: float, spread: float = 0) -> float:  # pragma: no cover
        """
        Discount a cash flow by time t (in years).
        """
        pass

    @abstractmethod
    def discount_date(
        self, date: Union[str, pd.Timestamp], spread: float = 0
    ) -> float:  # pragma: no cover
        """
        Discount a cash flow by a target date.
        """
        pass

    @abstractmethod
    def __call__(
        self,
        t: float,
        yield_calculation_convention: Optional[str] = None,
        spread: float = 0,
    ) -> float:  # pragma: no cover
        """
        Return the rate at time horizon t (in years).
        """
        pass

    @abstractmethod
    def date_rate(
        self,
        date: Union[str, pd.Timestamp],
        yield_calculation_convention: Optional[str] = None,
        spread: float = 0,
    ) -> float:  # pragma: no cover
        """
        Return the rate at a specified date.
        """
        pass

    @abstractmethod
    def discount_to_rate(
        self, discount_factor: float, t: float, spread: float
    ) -> float:  # pragma: no cover
        """
        Convert a discount factor to a rate.
        """
        raise NotImplementedError("discount_to_rate must be implemented in subclass.")

    def forward_t_start_t_end(
        self,
        t_start: float,
        t_end: float,
        spread_start: float = 0,
        spread_end: float = 0,
        spread_forward: float = 0,
    ) -> float:
        """
        Calculate the forward rate between two time horizons.

        You can adjust the spreads for each time horizon. For example, if you want
        to use the curve but adjust it to a specific spread, you can use
        the `spread_start` and `spread_end` parameters. If you want the result to revert to a curve without a spread, you can apply
        the `spread_forward` parameter that subtracts from the forward rate.

        Parameters
        ----------
        t_start : float
            Start time in years.
        t_end : float
            End time in years.
        spread_start : float, optional
            Spread to apply at the start time (default is 0).
        spread_end : float, optional
            Spread to apply at the end time (default is 0).
        spread_forward : float, optional
            Spread to subtract from the forward rate (default is 0).

        Returns
        -------
        float
            Forward rate between t_start and t_end.

        Notes
        -----
        This method computes the forward rate implied by the discount factors
        at t_start and t_end, adjusted for spreads.
        """
        dt = t_end - t_start
        descuento_t_start = self.discount_t(t_start, spread=spread_start)
        descuento_t_end = self.discount_t(t_end, spread=spread_end)
        return self.discount_to_rate(
            descuento_t_start / descuento_t_end, dt, spread=spread_forward
        )

    def forward_t_start_dt(
        self,
        t_start: float,
        dt: float,
        spread_start: float = 0,
        spread_end: float = 0,
        spread_forward: float = 0,
    ) -> float:
        """
        Calculate the forward rate given a start time and a time increment.

        You can adjust the spreads for each time horizon. For example, if you want
        to use the curve but adjust it to a specific spread, you can use
        the `spread_start` and `spread_end` parameters. If you want the result to revert to a curve without a spread, you can apply
        the `spread_forward` parameter that subtracts from the forward rate.

        Parameters
        ----------
        t_start : float
            Start time in years.
        dt : float
            Time increment in years.
        spread_start : float, optional
            Spread to apply at the start time (default is 0).
        spread_end : float, optional
            Spread to apply at the end time (default is 0).
        spread_forward : float, optional
            Spread to subtract from the forward rate (default is 0).

        Returns
        -------
        float
            Forward rate between t_start and t_start + dt.

        Notes
        -----
        This method is a convenience wrapper for `forward_t_start_t_end`.
        """
        t_end = t_start + dt
        return self.forward_t_start_t_end(
            t_start, t_end, spread_start, spread_end, spread_forward
        )

    def forward_dt(
        self,
        fecha_tasa: Union[str, pd.Timestamp],
        dt: float,
        spread_start: float = 0,
        spread_end: float = 0,
        spread_forward: float = 0,
    ) -> float:
        """
        Calculate the forward rate from a given date and time increment.

        You can adjust the spreads for each time horizon. For example, if you want
        to use the curve but adjust it to a specific spread, you can use
        the `spread_start` and `spread_end` parameters. If you want the result to revert to a curve without a spread, you can apply
        the `spread_forward` parameter that subtracts from the forward rate.

        Parameters
        ----------
        fecha_tasa : Union[str, pd.Timestamp]
            Start date for the forward rate calculation.
        dt : float
            Time increment in years.
        spread_start : float, optional
            Spread to apply at the start date (default is 0).
        spread_end : float, optional
            Spread to apply at the end date (default is 0).
        spread_forward : float, optional
            Spread to subtract from the forward rate (default is 0).

        Returns
        -------
        float
            Forward rate from fecha_tasa over dt years.

        Notes
        -----
        This method converts the start date to a time fraction and delegates to `forward_t_start_dt`.
        """
        t_start = self.day_count_convention.fraction(
            start=self.curve_date, current=pd.to_datetime(fecha_tasa)
        )
        return self.forward_t_start_dt(
            t_start, dt, spread_start, spread_end, spread_forward
        )

    def forward_dates(
        self,
        start_date: Union[str, pd.Timestamp],
        end_date: Union[str, pd.Timestamp],
        spread_start: float = 0,
        spread_end: float = 0,
        spread_forward: float = 0,
    ) -> float:
        """
        Calculate the forward rate between two dates.

        You can adjust the spreads for each time horizon. For example, if you want
        to use the curve but adjust it to a specific spread, you can use
        the `spread_start` and `spread_end` parameters. If you want the result to revert to a curve without a spread, you can apply
        the `spread_forward` parameter that subtracts from the forward rate.

        Parameters
        ----------
        start_date : Union[str, pd.Timestamp]
            Start date for the forward rate calculation.
        end_date : Union[str, pd.Timestamp]
            End date for the forward rate calculation.
        spread_start : float, optional
            Spread to apply at the start date (default is 0).
        spread_end : float, optional
            Spread to apply at the end date (default is 0).
        spread_forward : float, optional
            Spread to subtract from the forward rate (default is 0).

        Returns
        -------
        float
            Forward rate between start_date and end_date.

        Notes
        -----
        This method computes the time fraction between the two dates and delegates to `forward_dt`.
        """
        dt = self.day_count_convention.fraction(
            start=pd.to_datetime(start_date), current=pd.to_datetime(end_date)
        )
        return self.forward_dt(start_date, dt, spread_start, spread_end, spread_forward)

    def to_dataframe(self, maturities: Optional[list] = None) -> pd.DataFrame:
        """
        Export curve data to a pandas DataFrame.
        Uses __call__ for each maturity.
        """
        if maturities is None:
            maturities = [0.25, 0.5, 1, 2, 5, 10]
        data = {"Maturity": maturities, "Rate": [self(m) for m in maturities]}
        return pd.DataFrame(data)

    @abstractmethod
    def as_dict(self) -> dict:  # pragma: no cover
        """
        Return curve parameters and metadata as a dictionary.
        """
        raise NotImplementedError("as_dict must be implemented in subclass.")

    @classmethod
    def from_dict(cls, data: dict) -> "YieldCurveBase":
        """
        Instantiate a curve from a dictionary.
        """
        return cls(**data)

    def compare_to(
        self, other: "YieldCurveBase", maturities: Optional[list] = None
    ) -> pd.DataFrame:
        """
        Compare this curve to another curve (e.g., difference in rates, spreads).
        Returns a DataFrame with columns: Current Curve, Compared Curve, Spread.
        The discount_t and discount_to_rate are applied only to the compared curve.
        """
        if maturities is None:
            maturities = [0.25, 0.5, 1, 2, 5, 10]
        current_rates = [self(m) for m in maturities]
        compared_rates = [
            self.discount_to_rate(other.discount_t(m), m, spread=0) for m in maturities
        ]
        spread = [c - o for c, o in zip(current_rates, compared_rates)]
        df = pd.DataFrame(
            {
                "Maturity": maturities,
                "Current Curve": current_rates,
                "Compared Curve": compared_rates,
                "Spread": spread,
            }
        )
        return df
