"""
Module: custom_flow_bond
------

Provides the CustomFlowBond class for modeling fixed income instruments with user-defined amortization and coupon flows.
Coupons can be specified as explicit values or as percentages of the remaining notional for each period.

"""

from pyfian.fixed_income.fixed_rate_bond import FixedRateBullet
import pandas as pd
from typing import Optional, Union


class CustomFlowBond(FixedRateBullet):
    """
    CustomFlowBond allows user-defined amortization and coupon flows.

    Coupons can be set as explicit values for each period, or as percentages of the remaining notional.
    If a coupon value is provided for a period, it overrides the percentage calculation.
    If a single float is provided for custom_coupon_rates, it applies the same percentage for all periods.

    Examples
    --------
    >>> import pandas as pd
    >>> from pyfian.fixed_income.custom_flow_bond import CustomFlowBond
    >>> dates = [pd.Timestamp('2025-01-01'), pd.Timestamp('2026-01-01'), pd.Timestamp('2027-01-01')]
    >>> amortization = {dates[0]: 30, dates[1]: 30, dates[2]: 40}
    >>> coupons = {dates[0]: 5, dates[1]: 4, dates[2]: 3}
    >>> bond = CustomFlowBond(
    ...     issue_dt='2025-01-01',
    ...     maturity='2027-01-01',
    ...     notional=100,
    ...     custom_amortization=amortization,
    ...     custom_coupons=coupons
    ... )
    >>> bond.payment_flow
    {Timestamp('2025-01-01 00:00:00'): 35, Timestamp('2026-01-01 00:00:00'): 34, Timestamp('2027-01-01 00:00:00'): 43}

    >>> coupon_rates = 5.0
    >>> bond2 = CustomFlowBond(
    ...     issue_dt='2025-01-01',
    ...     maturity='2027-01-01',
    ...     notional=100,
    ...     custom_amortization=amortization,
    ...     custom_coupon_rates=coupon_rates
    ... )
    >>> bond2.coupon_flow
    {Timestamp('2025-01-01 00:00:00'): 5.0, Timestamp('2026-01-01 00:00:00'): 3.5, Timestamp('2027-01-01 00:00:00'): 2.0}

    Attributes
    ----------
    custom_amortization : Dict[pd.Timestamp, float]
        Amortization amounts by payment date.
    custom_coupons : Dict[pd.Timestamp, float]
        Coupon amounts by payment date.
    custom_coupon_rates : Union[Dict[pd.Timestamp, float], float, None]
        Coupon rates (percent per period) by payment date, or a single float for all periods.
    payment_flow : Dict[pd.Timestamp, float]
        Total payment (coupon + amortization) by payment date.
    coupon_flow : Dict[pd.Timestamp, float]
        Coupon payment by payment date.
    amortization_flow : Dict[pd.Timestamp, float]
        Amortization payment by payment date.
    """

    def __init__(
        self,
        issue_dt: Union[str, pd.Timestamp],
        maturity: Union[str, pd.Timestamp],
        notional: float = 100,
        custom_amortization: Optional[dict[pd.Timestamp, float]] = None,
        custom_coupons: Optional[dict[pd.Timestamp, float]] = None,
        custom_coupon_rates: Optional[Union[dict[pd.Timestamp, float], float]] = None,
        **kwargs,
    ):
        """
        Initialize a CustomFlowBond.

        Parameters
        ----------
        issue_dt : str or pd.Timestamp
            Issue date of the bond.
        maturity : str or pd.Timestamp
            Maturity date of the bond.
        notional : float, optional
            Initial notional value (default is 100).
        custom_amortization : dict, optional
            Amortization amounts by payment date.
        custom_coupons : dict, optional
            Coupon amounts by payment date.
        custom_coupon_rates : dict or float, optional
            Coupon rates (percent per period) by payment date, or a single float for all periods.
        **kwargs
            Additional arguments passed to FixedRateBullet.
        """
        self.custom_amortization = custom_amortization or {}
        self.custom_coupons = custom_coupons or {}
        self.custom_coupon_rates = custom_coupon_rates or {}
        super().__init__(
            issue_dt=issue_dt,
            maturity=maturity,
            cpn=0,
            cpn_freq=0,
            notional=notional,
            **kwargs,
        )

        # Override payment flows
        self.payment_flow, self.coupon_flow, self.amortization_flow = (
            self.make_payment_flow()
        )
        if sum(self.amortization_flow.values()) != self.notional:
            raise ValueError(
                "Total amortization does not equal notional."
                f"notional: {self.notional}, "
                f"amortization: {sum(self.amortization_flow.values())}"
            )

    def make_payment_flow(self):
        """
        Build the payment schedule using custom amortization and coupon flows.

        Coupons can be set as explicit values or as percentages of the remaining notional.
        If a coupon value is provided for a period, it overrides the percentage calculation.

        Returns
        -------
        dict_payments : Dict[pd.Timestamp, float]
            Total payment (coupon + amortization) by payment date.
        dict_coupons : Dict[pd.Timestamp, float]
            Coupon payment by payment date.
        dict_amortization : Dict[pd.Timestamp, float]
            Amortization payment by payment date.
        """
        # Gather all relevant dates
        all_dates = (
            set(self.custom_amortization.keys())
            | set(self.custom_coupons.keys())
            | {self.maturity}
        )
        if isinstance(self.custom_coupon_rates, dict):
            all_dates |= set(self.custom_coupon_rates.keys())

        dict_payments = {}
        dict_coupons = {}
        dict_amortization = {}

        remaining_notional = self.notional

        for dt in sorted(all_dates):
            if self.custom_amortization:
                amort = self.custom_amortization.get(dt, 0.0)
            else:
                if dt == self.maturity:
                    amort = remaining_notional

            # Coupon: use value if provided, else percent if provided
            if dt in self.custom_coupons:
                coupon = self.custom_coupons[dt]
            elif self.custom_coupon_rates is not None and self.custom_coupon_rates:
                if isinstance(self.custom_coupon_rates, dict):
                    rate = self.custom_coupon_rates.get(dt, 0.0)
                else:
                    rate = self.custom_coupon_rates
                coupon = remaining_notional * rate / 100.0
            else:
                coupon = 0.0

            dict_payments[dt] = coupon + amort
            dict_coupons[dt] = coupon
            dict_amortization[dt] = amort

            remaining_notional -= amort

        return dict_payments, dict_coupons, dict_amortization
