pyfian.yield_curves.par_curve
=============================

.. py:module:: pyfian.yield_curves.par_curve

.. autoapi-nested-parse::

   par_curve.py

   Module for bootstrapping par rates and zero-coupon rates from a series of bonds. Implements:

   - ParCurve: Bootstraps par rates and zero-coupon rates from a series of bonds using their prices and cash flows.

   .. rubric:: Examples

   >>> from pyfian.yield_curves.par_curve import ParCurve
   >>> list_maturities_rates = [
   ...         (pd.DateOffset(months=1), 4.49),
   ...         (pd.DateOffset(months=3), 4.32),
   ...         (pd.DateOffset(months=6), 4.14),
   ...         (pd.DateOffset(years=1), 3.95),
   ...         (pd.DateOffset(years=2), 3.79),
   ...         (pd.DateOffset(years=3), 3.75),
   ...         (pd.DateOffset(years=5), 3.86),
   ...         (pd.DateOffset(years=7), 4.07),
   ...         (pd.DateOffset(years=10), 4.33),
   ...         (pd.DateOffset(years=20), 4.89),
   ...         (pd.DateOffset(years=30), 4.92),
   ...     ]
   >>> date = pd.Timestamp("2025-08-22")
   >>> one_year_offset = date + pd.DateOffset(years=1)
   >>> par_rates = {}

   >>> for offset, cpn in list_maturities_rates:
   ...     not_zero_coupon = date + offset > one_year_offset
   ...     bond = {
   ...         "cpn_freq": 2 if not_zero_coupon else 0,
   ...         "cpn": cpn if not_zero_coupon else 0,
   ...         "price": 100 if not_zero_coupon else None,
   ...         "yield_to_maturity": None if not_zero_coupon else cpn / 100,
   ...     }
   ...     par_rates[offset] = bond
   >>> curve = ParCurve(curve_date="2025-08-22", par_rates=par_rates, yield_calculation_convention="BEY")
   >>> curve.discount_t(1)
   np.float64(0.9616401157)
   >>> curve.get_rate(1)
   np.float64(0.0395)



Attributes
----------

.. autoapisummary::

   pyfian.yield_curves.par_curve.list_maturities_rates


Classes
-------

.. autoapisummary::

   pyfian.yield_curves.par_curve.ParCurve


Module Contents
---------------

.. py:class:: ParCurve(curve_date: pandas.Timestamp, par_rates: Optional[dict[float, dict]] = None, zero_rates: Optional[dict[float, float]] = None, day_count_convention: str | pyfian.utils.day_count.DayCountBase = 'actual/365', yield_calculation_convention: Optional[str] = None)

   Bases: :py:obj:`pyfian.yield_curves.spot_curve.SpotCurve`


   ParCurve.

   This class provides a mechanism for constructing a par rate curve and extracting zero-coupon rates from market bond prices, which is essential for fixed income analytics, pricing, and risk management.

   Par rates are the rates that make a Bond's present value equal to its face value.
   From a series of par rates, zero rates are obtained.

   :param curve_date: Date of the curve.
   :type curve_date: str or datetime-like
   :param par_rates: Dictionary of time (in years) and a dict with inputs to create a FixedRateBullet for each par Bond.
   :type par_rates: dict
   :param zero_rates: Zero-coupon rates, keyed by maturity (in years).
   :type zero_rates: dict
   :param day_count_convention: Day count convention to use (default is "actual/365").
   :type day_count_convention: str or DayCountBase, optional
   :param yield_calculation_convention: Yield calculation convention to use (default is None). If not specified, "Annual" will be used.
   :type yield_calculation_convention: str, optional

   .. attribute:: curve_date

      Date of the curve.

      :type: pd.Timestamp

   .. attribute:: par_rates

      List of tuples (maturity, bond parameters) for each par bond.

      :type: list

   .. attribute:: zero_rates

      Bootstrapped zero-coupon rates, keyed by maturity (in years).

      :type: dict

   .. attribute:: day_count_convention

      Day count convention used for calculations.

      :type: DayCountBase

   .. attribute:: yield_calculation_convention

      Yield calculation convention used for calculations.

      :type: str

   .. attribute:: maturities

      List of maturities (in years) for which zero rates are available.

      :type: list

   .. method:: as_dict()

      Convert the curve to a dictionary.

   .. method:: discount_t(t)

      Return the discount factor for time t.

   .. method:: get_rate(t)

      Return the par rate for time t.

   .. method:: to_dataframe()

      Return the curve data as a pandas DataFrame.


   .. rubric:: Example

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
               "price": 100 if not_zero_coupon else None,
               "yield_to_maturity": None if not_zero_coupon else cpn / 100,
           }
           par_rates[offset] = bond

       curve = ParCurve(curve_date="2025-08-22", par_rates=par_rates)
       print(curve.to_dataframe())


   .. py:attribute:: curve_date
      :value: None



   .. py:attribute:: par_rates


   .. py:attribute:: day_count_convention
      :type:  pyfian.utils.day_count.DayCountBase


   .. py:attribute:: yield_calculation_convention
      :type:  str
      :value: 'Annual'



   .. py:attribute:: maturities


   .. py:method:: as_dict()

      Convert the curve to a dictionary.

      :returns: Dictionary containing curve parameters and metadata.
      :rtype: dict



   .. py:method:: _bootstrap_spot_rates()

      Bootstrap spot rates from the provided par rates.

      Populates self.zero_rates with calculated spot rates for each bond maturity.



   .. py:method:: __repr__()

      Return string representation of the ParCurve.

      :returns: String representation of the curve.
      :rtype: str



.. py:data:: list_maturities_rates

