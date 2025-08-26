"""
credit_spread.py

Implements CreditSpreadCurve for credit spreads at different maturities.
"""

from abc import abstractmethod
from typing import Optional, Union
import pandas as pd
from pyfian.fixed_income.fixed_rate_bond import FixedRateBullet
from pyfian.utils.day_count import DayCountBase, get_day_count_convention
from pyfian.visualization.mixins import YieldCurvePlotMixin
from pyfian.yield_curves.base_curve import CurveBase, YieldCurveBase
from pyfian.yield_curves.flat_curve import FlatCurveBEY
from scipy.optimize import fsolve
from pyfian.time_value import rate_conversions as rc


# Make an abstract CreditSpreadCurve class
class CreditSpreadCurveBase(YieldCurvePlotMixin, CurveBase):
    yield_calculation_convention: str

    """
    CreditSpreadCurveBase is an abstract base class for credit spread curves.
    """

    @abstractmethod
    def date_spread(self, date: Union[str, pd.Timestamp], spread: float = 0) -> float:
        """
        Get the spread for a given date.
        """
        pass

    @abstractmethod
    def _get_rate(self, t: float, spread: float = 0) -> float:
        """
        Get the spread for a given maturity.
        """
        pass


class CreditSpreadCurve(CreditSpreadCurveBase):
    """
    CreditSpreadCurve represents a curve of credit spreads (in decimals) at different maturities.

    Parameters
    ----------
    curve_date : str or datetime-like
        Date of the curve.
    benchmark_curve : YieldCurveBase, optional
        The benchmark yield curve to compare against (e.g., risk-free curve).
    bonds : list[FixedRateBullet] or tuple[FixedRateBullet], optional
        List or tuple of FixedRateBullet bond objects to bootstrap the spread curve from.
    spreads : dict[float, float], optional
        Dictionary mapping maturities (in years) to credit spreads (as decimals).
    day_count_convention : str or DayCountBase, optional
        Day count convention to use (default is "actual/365").
    yield_calculation_convention : str, optional
        Yield calculation convention to use (default is "Annual"). Supported: "Annual", "BEY", "Continuous".

    Attributes
    ----------
    spreads : dict[float, float]
        Dictionary of credit spreads by maturity (in years).
    curve_date : pd.Timestamp
        Date of the curve.
    bonds : list[FixedRateBullet] or None
        List of bonds used for bootstrapping, if provided.
    benchmark_curve : YieldCurveBase or None
        Benchmark yield curve.
    day_count_convention : DayCountBase
        Day count convention used for time calculations.
    yield_calculation_convention : str
        Yield calculation convention used for rate conversions.

    Methods
    -------
    as_dict()
        Convert the curve to a dictionary.
    __call__(t, spread=0)
        Get the spread for a given maturity (in years), optionally adding a spread.
    date_spread(date, spread=0)
        Get the spread for a given date, optionally adding a spread.
    spread_from_bonds(benchmark_curve, bonds)
        Class method to derive the spread curve from bond data and a benchmark curve.
    """

    def __init__(
        self,
        curve_date: Union[str, pd.Timestamp],
        benchmark_curve: Optional[YieldCurveBase] = None,
        bonds: Optional[
            list[FixedRateBullet] | tuple[FixedRateBullet]
        ] = None,  # TODO: With future custom bonds add FixedRateBullet base Class
        spreads: Optional[dict[float, float]] = None,
        day_count_convention: Optional[str | DayCountBase] = "actual/365",
        yield_calculation_convention: Optional[str] = None,
    ):
        if (spreads is None or len(spreads) == 0) and (
            bonds is None or benchmark_curve is None
        ):
            raise ValueError(
                "Either spreads or bonds and benchmark curve must be provided"
            )

        self.bonds = (
            sorted(bonds, key=lambda x: x.maturity) if bonds is not None else None
        )
        self.benchmark_curve = benchmark_curve

        self.curve_date = pd.to_datetime(curve_date)
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
            else yield_calculation_convention
        )
        if isinstance(spreads, dict):
            self.spreads = self._prepare_spreads(spreads)
        else:
            self.spreads = {}
            self._bootstrap_spreads()

        self.maturities = list(self.spreads.keys())

    def as_dict(self):
        """Convert the curve to a dictionary."""
        return {
            "spreads": self.spreads.copy(),
            "curve_date": self.curve_date,
            "bonds": self.bonds,
            "benchmark_curve": self.benchmark_curve,
            "day_count_convention": self.day_count_convention,
            "yield_calculation_convention": self.yield_calculation_convention,
        }

    def _prepare_spreads(self, spreads):
        """Prepare spreads for the curve sorted by time and with time fractions."""
        spreads = dict(sorted(spreads.items()))
        return spreads

    def _get_rate(self, t: float, spread: float = 0) -> float:
        """
        Get the rate for a cash flow by time t (in years).

        The spread is added to the yield in the original curve.

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
        return self._get_spread(t) + spread

    def date_spread(self, date: Union[str, pd.Timestamp], spread: float = 0) -> float:
        """ """
        t = self.day_count_convention.fraction(
            start=self.curve_date, current=pd.to_datetime(date)
        )
        return self._get_rate(t, spread)

    def _get_spread(self, t: float) -> float:
        # Simple linear interpolation between known maturities
        assert t >= 0, "Maturity must be non-negative"
        maturities = list(self.spreads.keys())
        if t <= maturities[0]:
            return self.spreads[maturities[0]]
        if t >= maturities[-1]:
            return self.spreads[maturities[-1]]
        else:
            for i in range(len(maturities) - 1):
                if maturities[i] <= t <= maturities[i + 1]:
                    s1, s2 = (
                        self.spreads[maturities[i]],
                        self.spreads[maturities[i + 1]],
                    )
                    t1, t2 = maturities[i], maturities[i + 1]
                    break
            return s1 + (s2 - s1) * (t - t1) / (t2 - t1)

    @classmethod
    def spread_from_bonds(
        cls,
        benchmark_curve: YieldCurveBase,
        bonds: list[FixedRateBullet] | tuple[FixedRateBullet],
    ):
        # Implement the logic to derive the spread curve from bond data
        spread_curve = cls(
            curve_date=benchmark_curve.curve_date,
            benchmark_curve=benchmark_curve,
            day_count_convention=benchmark_curve.day_count_convention,
            yield_calculation_convention=benchmark_curve.yield_calculation_convention,
            bonds=bonds,
        )

        return spread_curve

    def _bootstrap_spreads(self):
        spreads = self.spreads

        for bond in self.bonds:
            price = bond.get_bond_price()
            settlement_date = bond.get_settlement_date()
            payment_flow = bond.calculate_time_to_payments(bond_price=price)
            payment_dates = bond.filter_payment_flow(bond_price=price)

            maturity = self.day_count_convention.fraction(
                start=self.curve_date, current=bond.maturity
            )
            maturity_date = max(payment_dates)
            # curve_date must be the same as bond settlement date
            assert self.curve_date == settlement_date, (
                "curve_date must be the same as bond settlement date"
            )
            # For zero-coupon bond, spot rate is easy
            if len(payment_flow) == 2:
                face_value = payment_dates[maturity_date]
                r = (face_value / price) ** (1 / maturity) - 1
                r_convention = rc.convert_yield(
                    r, "Annual", self.yield_calculation_convention
                )
                b_rate = self.benchmark_curve.date_rate(
                    maturity_date, self.yield_calculation_convention
                )
                spreads[maturity] = r_convention - b_rate
            else:
                # For coupon bonds, solve for spot rate using previous spot rates
                # calculate present value of payment_flows lower than the maximum available zero_rates
                max_zero_rates_maturity = max(spreads.keys()) if spreads else None
                cumulative_present_value = 0
                non_valued_payments = {}
                for d, payment in payment_dates.items():
                    t = self.day_count_convention.fraction(
                        start=self.curve_date, current=d
                    )
                    if (
                        max_zero_rates_maturity is not None
                        and t <= max_zero_rates_maturity
                    ):
                        # get spread in annual terms
                        b = self.benchmark_curve.date_rate(
                            d,
                            yield_calculation_convention=self.yield_calculation_convention,
                        )
                        s = self.date_spread(d)
                        r = rc.convert_yield(
                            b + s,
                            self.yield_calculation_convention,
                            self.benchmark_curve.yield_calculation_convention,
                        )
                        adj_s = r - b
                        cumulative_present_value += (
                            self.benchmark_curve.discount_date(d, spread=adj_s)
                            * payment
                        )
                    else:
                        non_valued_payments[d] = payment
                # Now we have cumulative_present_value + sum(non_valued_payments discounted with spot rates) = price
                non_valued_payments[settlement_date] = cumulative_present_value

                # Get last_available_rate
                # last_t = max_zero_rates_maturity
                # last_rate = zero_rates.get(max_zero_rates_maturity, None)
                next_date = max(non_valued_payments.keys())

                # Get Linear Extrapolation
                spreads[maturity] = self._get_optimal_spread(
                    next_date,
                    non_valued_payments,
                )

    def _get_optimal_spread(
        self,
        next_date,
        non_valued_payments,
    ):
        if next_date is None:
            raise ValueError("Invalid input parameters")
        next_t = self.day_count_convention.fraction(
            start=self.curve_date, current=next_date
        )
        # start_guess = (last_rate + non_valued_payments[next_t]) / 2
        positive_cash_flows = [
            (
                cf,
                cf
                * self.day_count_convention.fraction(start=self.curve_date, current=d),
            )
            for d, cf in non_valued_payments.items()
            if cf > 0
        ]
        negative_cash_flows = [
            (
                cf,
                cf
                * self.day_count_convention.fraction(start=self.curve_date, current=d),
            )
            for d, cf in non_valued_payments.items()
            if cf < 0
        ]
        positive_cf, positive_cf_t = list(zip(*positive_cash_flows))
        negative_cf, negative_cf_t = list(zip(*negative_cash_flows))
        sum_positive_cf, sum_negative_cf = sum(positive_cf), sum(negative_cf)
        weighted_t_positive = (
            sum(positive_cf_t) / sum_positive_cf if sum_positive_cf else 0
        )
        weighted_t_negative = (
            sum(negative_cf_t) / sum_negative_cf if sum_negative_cf else 0
        )

        rate = (sum_positive_cf / -sum_negative_cf) ** (
            1 / (weighted_t_positive - weighted_t_negative)
        ) - 1
        spread = rate - self.benchmark_curve.date_rate(next_t)

        def _net_present_value(spread):
            self.spreads[next_t] = float(spread[0])
            # return sum(
            #     curve.discount_t(t) * payment
            #     for t, payment in non_valued_payments.items()
            # )
            pv = 0
            for d, payment in non_valued_payments.items():
                b = self.benchmark_curve.date_rate(
                    d, yield_calculation_convention=self.yield_calculation_convention
                )
                s = self.date_spread(d)
                r = rc.convert_yield(
                    b + s,
                    self.yield_calculation_convention,
                    self.benchmark_curve.yield_calculation_convention,
                )
                adj_s = r - b
                pv += self.benchmark_curve.discount_date(d, spread=adj_s) * payment
            return pv

        # find root of _net_present_value
        root = float(fsolve(_net_present_value, x0=spread)[0])
        return root

    def __repr__(self):
        return f"CreditSpreadCurve(spreads={self.spreads}, curve_date={self.curve_date.strftime('%Y-%m-%d')})"


class FlatCreditSpreadCurve(CreditSpreadCurveBase):
    """
    FlatCreditSpreadCurve represents a flat (constant) credit spread curve.

    Parameters
    ----------
    spread : float
        Credit spread (as decimal, e.g. 0.01 for 100bps).
    curve_date : str or datetime-like
        The curve settlement date.
    yield_calculation_convention : str, optional
        Yield calculation convention to use (default is "Annual"). Supported: "Annual", "BEY", "Continuous".

    Attributes
    ----------
    spread : float
        The constant credit spread.
    curve_date : pd.Timestamp
        Date of the curve.
    yield_calculation_convention : str
        Yield calculation convention used for rate conversions.

    Methods
    -------
    as_dict()
        Convert the curve to a dictionary.
    __call__(t, spread=0)
        Get the spread for a given maturity (always returns the constant spread).
    date_spread(date, spread=0)
        Get the spread for a given date (always returns the constant spread).
    """

    def __init__(
        self,
        spread: float,
        curve_date: Union[str, pd.Timestamp],
        yield_calculation_convention: Optional[str] = None,
    ):
        self.spread: float = spread
        self.curve_date: pd.Timestamp = pd.to_datetime(curve_date)
        self.yield_calculation_convention: str = (
            "Annual"
            if yield_calculation_convention is None
            else yield_calculation_convention
        )

    def as_dict(self) -> dict:
        """
        Convert the curve to a dictionary.
        """
        return {
            "spread": self.spread,
            "curve_date": self.curve_date,
            "yield_calculation_convention": self.yield_calculation_convention,
        }

    def _get_rate(self, t: float, spread: float = 0) -> float:
        """
        Get the spread for a given maturity.

        Parameters
        ----------
        t : float
            The maturity (in years).
        spread : float, optional
            An additional spread to add (default is 0).

        Returns
        -------
        float
            The spread for the given maturity.
        """
        return self.spread + spread

    def date_spread(self, date: Union[str, pd.Timestamp], spread: float = 0) -> float:
        """
        Get the spread for a given date.

        Parameters
        ----------
        date : Union[str, pd.Timestamp]
            The date to get the spread for.
        spread : float, optional
            An additional spread to add (default is 0).

        Returns
        -------
        float
            The spread for the given date.
        """
        return self._get_rate(0, spread)

    def __repr__(self) -> str:
        return f"FlatCreditSpreadCurve(spread={self.spread}, curve_date={self.curve_date.strftime('%Y-%m-%d')})"


if __name__ == "__main__":
    # Example usage
    # Par rates for different periods
    # 1-month	 4.49
    # 3-month	 4.32
    # 6-month	 4.14
    # 1-year	 3.95
    # 2-year	 3.79
    # 3-year	 3.75
    # 5-year	 3.86
    # 7-year	 4.07
    # 10-year	 4.33
    # 20-year	 4.89
    # 30-year	 4.92
    # Make FixedRateBullet instances for each bond
    list_maturities_rates = [
        (pd.DateOffset(months=1), 4.49),
        (pd.DateOffset(months=3), 4.32),
        (pd.DateOffset(months=6), 4.14),
        (pd.DateOffset(years=1), 3.95),
        (pd.DateOffset(years=2), 3.79),
        (pd.DateOffset(years=3), 3.75),
        (pd.DateOffset(years=5), 3.86),
        (pd.DateOffset(years=7), 4.07),
        (pd.DateOffset(years=10), 4.33),
        (pd.DateOffset(years=20), 4.89),
        (pd.DateOffset(years=30), 4.92),
    ]
    date = pd.Timestamp("2025-08-22")
    one_year_offset = date + pd.DateOffset(years=1)
    bonds = []
    for offset, cpn in list_maturities_rates:
        not_zero_coupon = date + offset > one_year_offset
        bond = FixedRateBullet(
            issue_dt=date,
            maturity=date + offset,
            cpn_freq=2 if not_zero_coupon else 0,  # Less than a year
            cpn=cpn if not_zero_coupon else 0,
            bond_price=100 if not_zero_coupon else None,
            yield_to_maturity=None if not_zero_coupon else cpn / 100,
            settlement_date=date,
        )
        # self = bond
        bonds.append(bond)

    # Example usage
    curve_date = date
    benchmark_curve = FlatCurveBEY(
        bey=0.02, curve_date=curve_date
    )  # Initialize your benchmark curve
    spread_curve = CreditSpreadCurve(
        curve_date=curve_date, benchmark_curve=benchmark_curve, bonds=bonds
    )
    spread_curve_2 = CreditSpreadCurve.spread_from_bonds(
        benchmark_curve=benchmark_curve, bonds=bonds
    )
    # self = spread_curve
