"""
curve_combination.py

Module for combining yield curves. Implements:

- CombinedCurve: Combines a benchmark yield curve and a spread curve to produce a total yield curve.
"""

import pandas as pd

from typing import Optional, Union

from pyfian.fixed_income.fixed_rate_bond import FixedRateBullet
from pyfian.time_value.rate_conversions import validate_yield_calculation_convention
from pyfian.utils.day_count import DayCountBase, get_day_count_convention
from pyfian.yield_curves.base_curve import YieldCurveBase
from pyfian.yield_curves.credit_spread import (
    CreditSpreadCurveBase,
    FlatCreditSpreadCurve,
)
from pyfian.time_value import rate_conversions as rc
from pyfian.yield_curves.zero_coupon_curve import ZeroCouponCurve


class CombinedCurve(ZeroCouponCurve):
    """
    CombinedCurve combines a benchmark curve and a spread curve.

    This class provides a mechanism for constructing a total yield curve by combining a base curve (e.g., risk-free) and a spread curve (e.g., credit spread), which is essential for pricing, discounting, and risk management in fixed income analytics.

    Parameters
    ----------
    benchmark_curve : object
            The base yield curve (e.g., ZeroCouponCurve, FlatCurveAER).
    spread_curve : object
            The credit spread curve (e.g., CreditSpreadCurve, FlatCreditSpreadCurve).
    day_count_convention : str | DayCountBase
            The day count convention to use (default is "actual/365").
    yield_calculation_convention : str, optional
            The yield calculation convention to use (default is None). Supported: "Annual", "BEY", "Continuous". If None, "Annual" will be used.
    """

    def __init__(
        self,
        benchmark_curve: YieldCurveBase,
        spread_curve: CreditSpreadCurveBase,
        day_count_convention: str | DayCountBase = "actual/365",
        yield_calculation_convention: Optional[str] = None,
    ):
        self.benchmark_curve = benchmark_curve
        self.spread_curve = spread_curve
        assert benchmark_curve.curve_date == spread_curve.curve_date, (
            "Curve dates must match."
        )
        self.curve_date = benchmark_curve.curve_date
        self.benchmark_yield_calculation_convention = (
            self.benchmark_curve.yield_calculation_convention
        )
        self.spread_yield_calculation_convention = (
            self.spread_curve.yield_calculation_convention
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
        self.yield_calculation_convention: str = (
            "Annual"
            if yield_calculation_convention is None
            else validate_yield_calculation_convention(yield_calculation_convention)
        )

        self.maturities = sorted(
            list(
                set(getattr(self.benchmark_curve, "maturities", []))
                | set(getattr(self.spread_curve, "maturities", []))
            )
        )

    def as_dict(self):
        return {
            "benchmark_curve": self.benchmark_curve,
            "spread_curve": self.spread_curve,
            "yield_calculation_convention": self.yield_calculation_convention,
            "day_count_convention": self.day_count_convention,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CombinedCurve":
        benchmark_curve = data["benchmark_curve"]
        spread_curve = data["spread_curve"]
        day_count_convention = data["day_count_convention"]
        yield_calculation_convention = data["yield_calculation_convention"]

        return cls(
            benchmark_curve=benchmark_curve,
            spread_curve=spread_curve,
            day_count_convention=day_count_convention,
            yield_calculation_convention=yield_calculation_convention,
        )

    def get_rate(
        self,
        t: float,
        yield_calculation_convention: Optional[str] = None,
        spread: float = 0,
    ) -> float:
        """
        Get the combined rate (benchmark + spread) for a cash flow by time t (in years).

        The spread is added to the yield in the original curve.

        yield_calculation_convention can be used to transform the yield to different conventions.

        Parameters
        ----------
        t : float
                Time in years to discount.
        spread : float
                Spread to add to the discount rate.
        yield_calculation_convention : Optional[str]
                Yield calculation convention to use (default is None).

        Returns
        -------
        float
                Rate for the cash flow.
        """
        if yield_calculation_convention is None:
            yield_calculation_convention = self.yield_calculation_convention

        # Get the base and spread rates
        base_rate = self.benchmark_curve.get_rate(t, spread=spread)
        spread_rate = self.spread_curve._get_t(t)

        # Convert the base_rate to the self.spread_curve_yield_curve_convention
        base_rate = rc.convert_yield(
            base_rate,
            self.benchmark_yield_calculation_convention,
            self.spread_yield_calculation_convention,
        )

        # Add spread to base_rate
        total_rate = base_rate + spread_rate

        # Convert total_rate back to the original
        return rc.convert_yield(
            total_rate,
            self.spread_yield_calculation_convention,
            yield_calculation_convention,
        )

    def date_rate(
        self,
        date: Union[str, "pd.Timestamp"],
        yield_calculation_convention: Optional[str] = None,
        spread: float = 0,
    ) -> float:
        """
        Get the combined rate (benchmark + spread) for a cash flow by date.

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
        # Call the combined curve with the calculated time fraction
        return self.get_rate(t, yield_calculation_convention, spread)

    def __repr__(self):
        return f"CombinedCurve(benchmark_curve={self.benchmark_curve}, spread_curve={self.spread_curve})"


if __name__ == "__main__":
    # Example usage
    from pyfian.yield_curves.flat_curve import FlatCurveAER, FlatCurveBEY
    from pyfian.yield_curves.credit_spread import (
        CreditSpreadCurveBase,
        CreditSpreadCurve,
    )

    curve_date = pd.Timestamp("2023-01-01")
    benchmark_curve = FlatCurveAER(
        aer=0.04, curve_date=curve_date
    )  # Initialize your benchmark curve
    spread_curve = FlatCreditSpreadCurve(
        spread=0.03, curve_date=curve_date
    )  # Initialize your spread curve
    combined_curve = CombinedCurve(benchmark_curve, spread_curve)
    combined_curve.compare_to(benchmark_curve)

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
    # Initialize your benchmark curve
    benchmark_curve_bey = FlatCurveBEY(
        bey=0.02, curve_date=curve_date
    )  # pragma: no cover
    spread_curve = CreditSpreadCurve.spread_from_bonds(
        benchmark_curve=benchmark_curve_bey, bonds=bonds
    )

    self = combined_curve = CombinedCurve(benchmark_curve_bey, spread_curve)
    combined_curve.compare_to(other=benchmark_curve_bey)

    for bond in bonds:
        bond_price = bond.get_bond_price()
        if bond_price is None:
            continue
        pv, flows_pv = bond.value_with_curve(combined_curve)
        maturity_date = bond.maturity
        print(
            f"Maturity: {maturity_date}, Price: {bond_price}, PV: {pv}, Diff: {bond_price - pv}"
        )
