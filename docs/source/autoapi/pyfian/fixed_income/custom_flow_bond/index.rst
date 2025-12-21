pyfian.fixed_income.custom_flow_bond
====================================

.. py:module:: pyfian.fixed_income.custom_flow_bond

.. autoapi-nested-parse::

   Module: custom_flow_bond
   ------

   Provides the CustomFlowBond class for modeling fixed income instruments with user-defined amortization and coupon flows.
   Coupons can be specified as explicit values or as percentages of the remaining notional for each period.



Classes
-------

.. autoapisummary::

   pyfian.fixed_income.custom_flow_bond.CustomFlowBond


Module Contents
---------------

.. py:class:: CustomFlowBond(issue_dt: Union[str, pandas.Timestamp], maturity: Union[str, pandas.Timestamp], notional: float = 100, custom_amortization: Optional[dict[pandas.Timestamp, float]] = None, custom_coupons: Optional[dict[pandas.Timestamp, float]] = None, custom_coupon_rates: Optional[Union[dict[pandas.Timestamp, float], float]] = None, **kwargs)

   Bases: :py:obj:`pyfian.fixed_income.fixed_rate_bond.FixedRateBullet`


   CustomFlowBond allows user-defined amortization and coupon flows.

   Coupons can be set as explicit values for each period, or as percentages of the remaining notional.
   If a coupon value is provided for a period, it overrides the percentage calculation.
   If a single float is provided for custom_coupon_rates, it applies the same percentage for all periods.

   .. rubric:: Examples

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

   .. attribute:: custom_amortization

      Amortization amounts by payment date.

      :type: Dict[pd.Timestamp, float]

   .. attribute:: custom_coupons

      Coupon amounts by payment date.

      :type: Dict[pd.Timestamp, float]

   .. attribute:: custom_coupon_rates

      Coupon rates (percent per period) by payment date, or a single float for all periods.

      :type: Union[Dict[pd.Timestamp, float], float, None]

   .. attribute:: payment_flow

      Total payment (coupon + amortization) by payment date.

      :type: Dict[pd.Timestamp, float]

   .. attribute:: coupon_flow

      Coupon payment by payment date.

      :type: Dict[pd.Timestamp, float]

   .. attribute:: amortization_flow

      Amortization payment by payment date.

      :type: Dict[pd.Timestamp, float]


   .. py:attribute:: custom_amortization


   .. py:attribute:: custom_coupons


   .. py:attribute:: custom_coupon_rates


   .. py:method:: make_payment_flow()

      Build the payment schedule using custom amortization and coupon flows.

      Coupons can be set as explicit values or as percentages of the remaining notional.
      If a coupon value is provided for a period, it overrides the percentage calculation.

      :returns: * **dict_payments** (*Dict[pd.Timestamp, float]*) -- Total payment (coupon + amortization) by payment date.
                * **dict_coupons** (*Dict[pd.Timestamp, float]*) -- Coupon payment by payment date.
                * **dict_amortization** (*Dict[pd.Timestamp, float]*) -- Amortization payment by payment date.



