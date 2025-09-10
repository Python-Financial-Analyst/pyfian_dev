"""
interpolated_curve.py

Implements InterpolatedCurve using cubic spline interpolation.
"""

from typing import Optional, Union
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from scipy.optimize import minimize
from pyfian.utils.day_count import DayCountBase, get_day_count_convention
from pyfian.yield_curves.zero_coupon_curve import ZeroCouponCurve


class InterpolatedCurve(ZeroCouponCurve):
    """
    InterpolatedCurve represents a yield curve for zero-coupon rates at different maturities.

    The curve can be set using a dictionary of zero-coupon rates and supports interpolation
    for maturities not explicitly provided.

    It can also be derived setting a group of maturities and a group of bonds with prices,
    where the bonds are used to infer the zero-coupon rates using the maturities as pivots for
    an interpolated curve.

    Parameters
    ----------
    curve_date : str or datetime-like
        Date of the curve.
    maturities : list of float, optional
        List of maturities (in years) to make curve pivot points.
        If zero_rates is provided, maturities will be inferred from its keys.
        If both maturities and zero_rates are None, default maturities will be used: [0.5, 1, 2, 3, 5, 7, 10, 20, 30].
    zero_rates : dict, optional
        Dictionary mapping maturities (in years) to zero-coupon rates (as decimals). If provided, maturities will be inferred from its keys.
    bonds : list, optional
        List of bonds used to infer the zero-coupon rates.
    day_count_convention : str or DayCountBase, optional
        Day count convention to use (default is None). If None, "actual/365" will be used.
    yield_calculation_convention : str, optional
        Yield calculation convention to use (default is None).
        Supported conventions: "Annual", "BEY", "Continuous". If None, "Annual" will be used.

    Attributes
    ----------
    curve_date : pd.Timestamp
        Date of the curve.
    maturities : list of float
        List of maturities (in years) for which zero-coupon rates are available.
    zero_rates : dict
        Dictionary of zero-coupon rates keyed by maturity (in years).
    bonds : list, optional
        List of bonds used to infer the zero-coupon rates.
    day_count_convention : DayCountBase
        Day count convention used for calculations.
    yield_calculation_convention : str
        Yield calculation convention used for rate conversions.
    maturities : list of float
        List of maturities (in years) for which zero-coupon rates are available.

    Methods
    -------
    as_dict()
        Convert the curve to a dictionary.
    discount_t(t, spread=0)
        Discount a cash flow by time t (in years).
    discount_to_rate(discount_factor, t, spread, yield_calculation_convention=None)
        Convert a discount factor for a period t to a rate.
    discount_date(date, spread=0)
        Discount a cash flow to a specific date.
    get_rate(t, yield_calculation_convention=None, spread=0)
        Get the rate for a cash flow by time t (in years).
    date_rate(date, yield_calculation_convention=None, spread=0)
        Get the rate for a cash flow by date.
    get_t(t, spread=0)
        Get the interpolated zero-coupon rate for time t (in years).

    Example
    -------
    .. code-block:: python

        import pandas as pd
        from pyfian.yield_curves.zero_coupon_curve import ZeroCouponCurve

        zero_rates = {
            1: 0.04,   # 1 year maturity, 4% rate
            2: 0.042,  # 2 year maturity, 4.2% rate
            5: 0.045,  # 5 year maturity, 4.5% rate
        }
        curve_date = "2025-08-22"
        curve = InterpolatedCurve(zero_rates=zero_rates, curve_date=curve_date)
        # Get discount factor for 2 years
        df = curve.discount_t(2)
        # Get rate for 2 years
        rate = curve.get_rate(2)
        print(f"Discount factor for 2 years: {df}")
        print(f"Zero-coupon rate for 2 years: {rate}")
    """

    def __init__(
        self,
        curve_date: Union[str, pd.Timestamp],
        maturities: Optional[list[float]] = None,
        zero_rates: Optional[dict[float, float]] = None,
        bonds: Optional[list] = None,
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
            else self._validate_yield_calculation_convention(
                yield_calculation_convention
            )
        )
        # Raise an error if maturities neither maturities nor zero_rates are provided
        if zero_rates is None:
            self.maturities = (
                maturities
                if maturities is not None
                else [0.5, 1, 2, 3, 5, 7, 10, 20, 30]
            )
            self.zero_rates = {m: None for m in self.maturities}
        else:
            self.zero_rates = self._prepare_zero_rates(zero_rates)
            self.maturities = list(zero_rates.keys())

        # raise error if any bond has no price
        if bonds is not None:
            for bond in bonds:
                price = bond.get_price()
                if price is None:
                    raise ValueError("All bonds must have a price to infer zero rates.")
        self.bonds = (
            sorted(bonds, key=lambda b: b.maturity) if bonds is not None else None
        )

        # If bonds are provided, infer zero rates
        if self.bonds is not None and zero_rates is None:
            self._infer_zero_rates_from_bonds(self.bonds)

    def _infer_zero_rates_from_bonds(self, bonds):
        """
        Infer zero-coupon rates from the provided bonds and maturities using interpolation.
        """
        # Placeholder for actual implementation
        # This method should set self.zero_rates based on bond prices and maturities

        # Get duration and yield to Maturity for each bond
        initial_guesses = {}
        max_maturity = self.curve_date
        for bond in bonds:
            bond_duration = bond.effective_duration()
            bond_yield = bond.yield_to_maturity(bond.get_price())
            initial_guesses[bond_duration] = bond_yield
            if bond.maturity > max_maturity:
                max_maturity = bond.maturity

        # Interpolate the initial guesses to the maturities
        guess_maturities = list(initial_guesses.keys())
        guess_rates = list(initial_guesses.values())

        # Get difference in years between curve date and max maturity, equally counting leap years
        years_max_maturity = (max_maturity - self.curve_date).days / 365.25

        # Filter maturities
        maturities_check = [m >= years_max_maturity for m in self.maturities]

        # Get maturity of the first maturity greater than max_maturity
        if any(maturities_check):
            first_greater_maturity = self.maturities[maturities_check.index(True)]
            maturities = [m for m in self.maturities if m <= first_greater_maturity]
        else:
            maturities = self.maturities.copy()
            # Add max_maturity if not already in maturities
            while maturities[-1] < years_max_maturity:
                maturities.append(maturities[-1] + maturities[-1] - maturities[-2])

        interp_func = interp1d(
            guess_maturities, guess_rates, bounds_error=False, fill_value="extrapolate"
        )

        zero_rates = {m: interp_func(m) for m in maturities}

        initial_rates = np.array(list(zero_rates.values()))
        # zero_rates_array = initial_rates

        # Make an objective function to minimize the root squared differences between bond prices and
        # the prices calculated using the zero-coupon rates
        def objective(zero_rates_array):
            zero_rates_dict = {m: r for m, r in zip(maturities, zero_rates_array)}
            test_curve = InterpolatedCurve(
                curve_date=self.curve_date,
                maturities=maturities,
                zero_rates=zero_rates_dict,
            )

            total_error = 0.0
            for bond in bonds:
                price = bond.get_price()
                npv, present_values = bond.value_with_curve(test_curve, price=price)
                # print(
                #     f"Maturity Date: {bond.maturity}, Bond Price: {price}, NPV: {npv}, PV: {npv + price}"
                # )
                total_error += (npv) ** 2 * (
                    60 / (len(present_values) - 1)
                ) ** 0.5  # Weight by number of rates
            # print(f"Total Error: {total_error**.5 * 1e3}")
            return total_error**0.5  # Scale to avoid very small numbers

        # Minimize the objective function to find the best-fitting zero rates
        result = minimize(
            objective,
            initial_rates,
            method="L-BFGS-B",
            tol=1e-6,
            options={"maxiter": 1000},
        )
        # zero_rates_array = result.x
        if not result.success:
            raise ValueError(
                "Optimization failed to find a valid solution."
            )  # pragma: no cover

        # Update the zero rates with the optimized values
        self.zero_rates = {m: r for m, r in zip(maturities, result.x)}
        self.maturities = maturities

    def __repr__(self):
        return f"InterpolatedCurve(maturities={self.maturities}, zero_rates={self.zero_rates}, curve_date={self.curve_date.strftime('%Y-%m-%d')})"


if __name__ == "__main__":  # pragma: no cover
    from pyfian.fixed_income.fixed_rate_bond import FixedRateBullet

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
    maturities = []
    for offset, cpn in list_maturities_rates:
        not_zero_coupon = date + offset > one_year_offset
        maturities.append((date + offset - date).days / 365)

        bond = FixedRateBullet(
            issue_dt=date,
            maturity=date + offset,
            cpn_freq=2 if not_zero_coupon else 0,  # Less than a year
            cpn=cpn if not_zero_coupon else 0,
            price=100 if not_zero_coupon else None,
            yield_to_maturity=None if not_zero_coupon else cpn / 100,
            settlement_date=date,
        )
        # self = bond
        bonds.append(bond)
    curve = InterpolatedCurve(
        curve_date="2025-08-22", bonds=bonds, maturities=maturities
    )
    # self = curve

    for bond in bonds:
        price = bond.get_price()
        if price is None:
            continue
        pv, flows_pv = bond.value_with_curve(curve)
        maturity_date = bond.maturity
        print(
            f"Maturity Date: {maturity_date}, Bond Price: {price}, PV: {pv}, Difference: {price - pv}"
        )

    print(curve.to_dataframe())
