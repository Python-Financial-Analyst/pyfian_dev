"""
par_curve.py

Module for bootstrapping par rates and zero-coupon rates from a series of bonds. Implements:

- ParCurve: Bootstraps par rates and zero-coupon rates from a series of bonds using their prices and cash flows.

Examples
--------
>>> from pyfian.yield_curves.par_curve import ParCurve
>>> curve = ParCurve(curve_date="2025-08-22", par_rates=par_rates)
>>> curve.discount_t(1)
... # returns discount factor for 1 year
>>> curve.get_rate(1)
... # returns par rate for 1 year
"""

import pandas as pd
from typing import Optional
from scipy.optimize import fsolve


from pyfian.fixed_income.fixed_rate_bond import FixedRateBullet
from pyfian.time_value.rate_conversions import validate_yield_calculation_convention
from pyfian.utils.day_count import DayCountBase, get_day_count_convention
from pyfian.yield_curves.zero_coupon_curve import ZeroCouponCurve
from pyfian.time_value import rate_conversions as rc


class ParCurve(ZeroCouponCurve):
    """
    ParCurve.

    This class provides a mechanism for constructing a par rate curve and extracting zero-coupon rates from market bond prices, which is essential for fixed income analytics, pricing, and risk management.

    Par rates are the rates that make a Bond's present value equal to its face value.
    From a series of par rates, zero rates are obtained.

    Parameters
    ----------
    curve_date : str or datetime-like
        Date of the curve.
    par_rates : dict
        Dictionary of time (in years) and a dict with inputs to create a FixedRateBullet for each par Bond.
    zero_rates : dict
        Zero-coupon rates, keyed by maturity (in years).
    day_count_convention : str or DayCountBase, optional
        Day count convention to use (default is "actual/365").
    yield_calculation_convention : str, optional
        Yield calculation convention to use (default is None). If not specified, "Annual" will be used.

    Attributes
    ----------
    curve_date : pd.Timestamp
        Date of the curve.
    par_rates : list
        List of tuples (maturity, bond parameters) for each par bond.
    zero_rates : dict
        Bootstrapped zero-coupon rates, keyed by maturity (in years).
    day_count_convention : DayCountBase
        Day count convention used for calculations.
    yield_calculation_convention : str
        Yield calculation convention used for calculations.
    maturities : list
        List of maturities (in years) for which zero rates are available.

    Methods
    -------
    as_dict()
        Convert the curve to a dictionary.
    discount_t(t)
        Return the discount factor for time t.
    get_rate(t)
        Return the par rate for time t.
    to_dataframe()
        Return the curve data as a pandas DataFrame.

    Example
    -------
    .. code-block:: python

        import pandas as pd
        from pyfian.yield_curves.par_curve import ParCurve

        # Par rates for different periods
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
        par_rates = {}

        for offset, cpn in list_maturities_rates:
            not_zero_coupon = date + offset > one_year_offset
            bond = {
                "cpn_freq": 2 if not_zero_coupon else 0,
                "cpn": cpn if not_zero_coupon else 0,
                "bond_price": 100 if not_zero_coupon else None,
                "yield_to_maturity": None if not_zero_coupon else cpn / 100,
            }
            par_rates[offset] = bond

        curve = ParCurve(curve_date="2025-08-22", par_rates=par_rates)
        print(curve.to_dataframe())
    """

    def __init__(
        self,
        curve_date: pd.Timestamp,
        par_rates: Optional[dict[float, dict]] = None,
        zero_rates: Optional[dict[float, float]] = None,
        day_count_convention: str | DayCountBase = "actual/365",
        yield_calculation_convention: Optional[str] = None,
    ):
        if par_rates is None and zero_rates is None:
            raise ValueError("Either par_rates or zero_rates must be provided")

        self.curve_date = pd.to_datetime(curve_date)
        self.par_rates = (
            sorted(par_rates.items(), key=lambda x: x[0] + self.curve_date)
            if par_rates is not None
            else None
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

        if zero_rates is not None:
            self.zero_rates = zero_rates
        else:
            self.zero_rates = {}
            self._bootstrap_spot_rates()

        self.maturities = list(self.zero_rates.keys())

    def as_dict(self):
        """
        Convert the curve to a dictionary.

        Returns
        -------
        dict
            Dictionary containing curve parameters and metadata.
        """
        return {
            "curve_date": self.curve_date,
            "par_rates": self.par_rates,
            "zero_rates": self.zero_rates.copy(),
        }

    def _bootstrap_spot_rates(self):
        """
        Bootstrap spot rates from the provided par rates.

        Populates self.zero_rates with calculated spot rates for each bond maturity.
        """
        zero_rates = self.zero_rates

        for maturity, bond_params in self.par_rates:
            maturity_date = self.curve_date + maturity
            bond = FixedRateBullet(
                settlement_date=self.curve_date,
                issue_dt=self.curve_date,
                maturity=maturity_date,
                **bond_params,
            )
            price = bond.get_bond_price()
            payment_flow = bond.calculate_time_to_payments(bond_price=price)
            maturity = max(payment_flow)
            # curve_date must be the same as bond settlement date
            assert self.curve_date == bond.get_settlement_date(), (
                "curve_date must be the same as bond settlement date"
            )
            # For zero-coupon bond, spot rate is easy
            if len(payment_flow) == 2:
                face_value = payment_flow[maturity]
                r = (face_value / price) ** (1 / maturity) - 1
                zero_rates[maturity] = rc.convert_yield(
                    r, "Annual", self.yield_calculation_convention
                )
            else:
                # For coupon bonds, solve for spot rate using previous spot rates
                # calculate present value of payment_flows lower than the maximum available zero_rates
                max_zero_rates_maturity = max(zero_rates.keys()) if zero_rates else None
                cumulative_present_value = 0
                non_valued_payments = {}
                for t, payment in payment_flow.items():
                    if (
                        max_zero_rates_maturity is not None
                        and t <= max_zero_rates_maturity
                    ):
                        cumulative_present_value += self.discount_t(t) * payment
                    else:
                        non_valued_payments[t] = payment
                # Now we have cumulative_present_value + sum(non_valued_payments discounted with spot rates) = price
                non_valued_payments[0] = cumulative_present_value

                # Get last_available_rate
                # last_t = max_zero_rates_maturity
                # last_rate = zero_rates.get(max_zero_rates_maturity, None)
                next_t = max(non_valued_payments.keys())

                # Get Linear Extrapolation
                zero_rates[maturity] = self._get_optimal_rate(
                    # last_t, last_rate,
                    next_t,
                    non_valued_payments,
                )

    def _get_optimal_rate(
        self,
        #   last_t,
        #   last_rate,
        next_t,
        non_valued_payments,
    ):
        """
        Find the optimal spot rate for a given maturity using non-valued payments.

        Parameters
        ----------
        next_t : float
            Maturity for which to solve the spot rate.
        non_valued_payments : dict
            Payments not valued by previous spot rates.

        Returns
        -------
        float
            Optimal spot rate for the given maturity.
        """
        if next_t is None:
            raise ValueError("Invalid input parameters")
        # start_guess = (last_rate + non_valued_payments[next_t]) / 2
        positive_cash_flows = [
            (cf, cf * t) for t, cf in non_valued_payments.items() if cf > 0
        ]
        negative_cash_flows = [
            (cf, cf * t) for t, cf in non_valued_payments.items() if cf < 0
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

        def _net_present_value(rate):
            self.zero_rates[next_t] = float(rate[0])
            return sum(
                self.discount_t(t) * payment
                for t, payment in non_valued_payments.items()
            )

        # find root of _net_present_value
        root = float(fsolve(_net_present_value, x0=rate)[0])
        return root

    def __repr__(self):
        """
        Return string representation of the ParCurve.

        Returns
        -------
        str
            String representation of the curve.
        """
        return f"SpotCurve(zero_rates={self.zero_rates}, curve_date={self.curve_date.strftime('%Y-%m-%d')})"


if __name__ == "__main__":  # pragma : no cover
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
    # Make dict of t and rates instances for each bond
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
    par_rates = {}

    for offset, cpn in list_maturities_rates:
        not_zero_coupon = date + offset > one_year_offset

        bond = {
            "cpn_freq": 2 if not_zero_coupon else 0,
            "cpn": cpn if not_zero_coupon else 0,
            "bond_price": 100 if not_zero_coupon else None,
            "yield_to_maturity": None if not_zero_coupon else cpn / 100,
        }
        # self = bond
        par_rates[offset] = bond
    curve = ParCurve(curve_date="2025-08-22", par_rates=par_rates)
    # self = curve
    print(curve.to_dataframe())
