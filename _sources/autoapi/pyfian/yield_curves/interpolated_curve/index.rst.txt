pyfian.yield_curves.interpolated_curve
======================================

.. py:module:: pyfian.yield_curves.interpolated_curve

.. autoapi-nested-parse::

   interpolated_curve.py

   Implements InterpolatedCurve using cubic spline interpolation.



Attributes
----------

.. autoapisummary::

   pyfian.yield_curves.interpolated_curve.list_maturities_rates


Classes
-------

.. autoapisummary::

   pyfian.yield_curves.interpolated_curve.InterpolatedCurve


Module Contents
---------------

.. py:class:: InterpolatedCurve(curve_date: Union[str, pandas.Timestamp], maturities: Optional[list[float]] = None, zero_rates: Optional[dict[float, float]] = None, bonds: Optional[list] = None, day_count_convention: Optional[str | pyfian.utils.day_count.DayCountBase] = 'actual/365', yield_calculation_convention: Optional[str] = None)

   Bases: :py:obj:`pyfian.yield_curves.zero_coupon_curve.ZeroCouponCurve`


   InterpolatedCurve represents a yield curve for zero-coupon rates at different maturities.

   The curve can be set using a dictionary of zero-coupon rates and supports interpolation
   for maturities not explicitly provided.

   It can also be derived setting a group of maturities and a group of bonds with prices,
   where the bonds are used to infer the zero-coupon rates using the maturities as pivots for
   an interpolated curve.

   :param curve_date: Date of the curve.
   :type curve_date: str or datetime-like
   :param maturities: List of maturities (in years) to make curve pivot points.
                      If zero_rates is provided, maturities will be inferred from its keys.
                      If both maturities and zero_rates are None, default maturities will be used: [0.5, 1, 2, 3, 5, 7, 10, 20, 30].
   :type maturities: list of float, optional
   :param zero_rates: Dictionary mapping maturities (in years) to zero-coupon rates (as decimals). If provided, maturities will be inferred from its keys.
   :type zero_rates: dict, optional
   :param bonds: List of bonds used to infer the zero-coupon rates.
   :type bonds: list, optional
   :param day_count_convention: Day count convention to use (default is None). If None, "actual/365" will be used.
   :type day_count_convention: str or DayCountBase, optional
   :param yield_calculation_convention: Yield calculation convention to use (default is None).
                                        Supported conventions: "Annual", "BEY", "Continuous". If None, "Annual" will be used.
   :type yield_calculation_convention: str, optional

   .. attribute:: curve_date

      Date of the curve.

      :type: pd.Timestamp

   .. attribute:: maturities

      List of maturities (in years) for which zero-coupon rates are available.

      :type: list of float

   .. attribute:: zero_rates

      Dictionary of zero-coupon rates keyed by maturity (in years).

      :type: dict

   .. attribute:: bonds

      List of bonds used to infer the zero-coupon rates.

      :type: list, optional

   .. attribute:: day_count_convention

      Day count convention used for calculations.

      :type: DayCountBase

   .. attribute:: yield_calculation_convention

      Yield calculation convention used for rate conversions.

      :type: str

   .. attribute:: maturities

      List of maturities (in years) for which zero-coupon rates are available.

      :type: list of float

   .. method:: as_dict()

      Convert the curve to a dictionary.

   .. method:: discount_t(t, spread=0)

      Discount a cash flow by time t (in years).

   .. method:: discount_to_rate(discount_factor, t, spread, yield_calculation_convention=None)

      Convert a discount factor for a period t to a rate.

   .. method:: discount_date(date, spread=0)

      Discount a cash flow to a specific date.

   .. method:: get_rate(t, yield_calculation_convention=None, spread=0)

      Get the rate for a cash flow by time t (in years).

   .. method:: date_rate(date, yield_calculation_convention=None, spread=0)

      Get the rate for a cash flow by date.

   .. method:: get_t(t, spread=0)

      Get the interpolated zero-coupon rate for time t (in years).


   .. rubric:: Example

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


   .. py:attribute:: curve_date
      :value: None



   .. py:attribute:: day_count_convention
      :type:  pyfian.utils.day_count.DayCountBase


   .. py:attribute:: yield_calculation_convention
      :type:  str
      :value: 'Annual'



   .. py:attribute:: bonds


   .. py:method:: _infer_zero_rates_from_bonds(bonds)

      Infer zero-coupon rates from the provided bonds and maturities using interpolation.



   .. py:method:: __repr__()


.. py:data:: list_maturities_rates

