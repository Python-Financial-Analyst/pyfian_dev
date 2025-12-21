pyfian.yield_curves.base_curve
==============================

.. py:module:: pyfian.yield_curves.base_curve

.. autoapi-nested-parse::

   base_curve.py

   Module for abstract base classes for yield curves and related curve models.

   Implements:

   - CurveBase: Abstract base class for all curve types, providing common interface and utilities.
   - YieldCurveBase: Abstract base class for yield curves, extending CurveBase with discounting and rate calculation methods.

   These classes define the structure and required methods for curve models used in fixed income analytics, including discounting, rate calculation, forward rates, and comparison utilities.



Attributes
----------

.. autoapisummary::

   pyfian.yield_curves.base_curve.MATURITIES


Classes
-------

.. autoapisummary::

   pyfian.yield_curves.base_curve.CurveBase
   pyfian.yield_curves.base_curve.YieldCurveBase


Module Contents
---------------

.. py:data:: MATURITIES
   :value: [0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30]


.. py:class:: CurveBase

   Bases: :py:obj:`abc.ABC`


   Abstract base class for all curves.

   :param curve_date: Date of the curve.
   :type curve_date: pd.Timestamp
   :param day_count_convention: Day count convention used for time calculations.
   :type day_count_convention: DayCountBase

   .. attribute:: curve_date

      Date of the curve.

      :type: pd.Timestamp

   .. attribute:: day_count_convention

      Day count convention used for time calculations.

      :type: DayCountBase

   .. method:: _get_t(t, spread=0)

      Get the rate for a cash flow by time t (in years).

   .. method:: to_dataframe(maturities=None)

      Export curve data to a pandas DataFrame.

   .. method:: as_dict()

      Return curve parameters and metadata as a dictionary.

   .. method:: from_dict(data)

      Instantiate a curve from a dictionary.

   .. method:: clone_with_new_date(new_date)

      Clone the curve with a new date.



   .. py:attribute:: curve_date
      :type:  pandas.Timestamp


   .. py:attribute:: day_count_convention
      :type:  pyfian.utils.day_count.DayCountBase


   .. py:method:: _get_t(t: float, spread: float = 0) -> float
      :abstractmethod:


      Get the rate for a cash flow by time t (in years).

      The spread is added to the yield in the original curve.

      :param t: Time in years to discount.
      :type t: float
      :param spread: Spread to add to the discount rate.
      :type spread: float

      :returns: Rate for the cash flow.
      :rtype: float



   .. py:method:: get_t(t: float, spread: float = 0) -> float
      :abstractmethod:



   .. py:method:: to_dataframe(maturities: Optional[list] = None) -> pandas.DataFrame

      Export curve data to a pandas DataFrame.
      Uses __call__ for each maturity.



   .. py:method:: as_dict() -> dict
      :abstractmethod:


      Return curve parameters and metadata as a dictionary.



   .. py:method:: from_dict(data: dict) -> CurveBase
      :classmethod:


      Instantiate a curve from a dictionary.



   .. py:method:: clone_with_new_date(new_date: Union[str, pandas.Timestamp]) -> CurveBase

      Clone the curve with a new date.



.. py:class:: YieldCurveBase

   Bases: :py:obj:`CurveBase`


   Abstract base class for yield curves.

   :param curve_date: Date of the curve.
   :type curve_date: pd.Timestamp
   :param day_count_convention: Day count convention used for time calculations.
   :type day_count_convention: DayCountBase
   :param yield_calculation_convention: Yield calculation convention used for rate conversions.
   :type yield_calculation_convention: str

   .. attribute:: curve_date

      Date of the curve.

      :type: pd.Timestamp

   .. attribute:: day_count_convention

      Day count convention used for time calculations.

      :type: DayCountBase

   .. attribute:: yield_calculation_convention

      Yield calculation convention used for rate conversions.

      :type: str

   .. method:: discount_t(t, spread=0)

      Discount a cash flow by time t (in years).

   .. method:: discount_date(date, spread=0)

      Discount a cash flow by a target date.

   .. method:: get_rate(t, yield_calculation_convention=None, spread=0)

      Return the rate at time horizon t (in years).

   .. method:: date_rate(date, yield_calculation_convention=None, spread=0)

      Return the rate at a specified date.

   .. method:: discount_to_rate(discount_factor, t, spread)

      Convert a discount factor to a rate.

   .. method:: forward_t_start_t_end(t_start, t_end, spread_start=0, spread_end=0, spread_forward=0)

      Calculate the forward rate between two time horizons.

   .. method:: forward_t_start_dt(t_start, dt, spread_start=0, spread_end=0, spread_forward=0)

      Calculate the forward rate given a start time and a time increment.

   .. method:: forward_dt(date, dt, spread_start=0, spread_end=0, spread_forward=0)

      Calculate the forward rate from a given date and time increment.

   .. method:: forward_dates(start_date, end_date, spread_start=0, spread_end=0, spread_forward=0)

      Calculate the forward rate between two dates.

   .. method:: compare_to(other, maturities=None)

      Compare this curve to another curve.



   .. py:attribute:: curve_date
      :type:  pandas.Timestamp


   .. py:attribute:: day_count_convention
      :type:  pyfian.utils.day_count.DayCountBase


   .. py:attribute:: yield_calculation_convention
      :type:  str


   .. py:method:: discount_t(t: float, spread: float = 0) -> float
      :abstractmethod:


      Discount a cash flow by time t (in years).



   .. py:method:: discount_date(date: Union[str, pandas.Timestamp], spread: float = 0) -> float
      :abstractmethod:


      Discount a cash flow by a target date.



   .. py:method:: get_rate(t: float, yield_calculation_convention: Optional[str] = None, spread: float = 0) -> float
      :abstractmethod:


      Return the rate at time horizon t (in years).



   .. py:method:: date_rate(date: Union[str, pandas.Timestamp], yield_calculation_convention: Optional[str] = None, spread: float = 0) -> float
      :abstractmethod:


      Return the rate at a specified date.



   .. py:method:: discount_to_rate(discount_factor: float, t: float, spread: float) -> float
      :abstractmethod:


      Convert a discount factor to a rate.



   .. py:method:: forward_t_start_t_end(t_start: float, t_end: float, spread_start: float = 0, spread_end: float = 0, spread_forward: float = 0) -> float

      Calculate the forward rate between two time horizons.

      You can adjust the spreads for each time horizon. For example, if you want
      to use the curve but adjust it to a specific spread, you can use
      the `spread_start` and `spread_end` parameters. If you want the result to revert to a curve without a spread, you can apply
      the `spread_forward` parameter that subtracts from the forward rate.

      :param t_start: Start time in years.
      :type t_start: float
      :param t_end: End time in years.
      :type t_end: float
      :param spread_start: Spread to apply at the start time (default is 0).
      :type spread_start: float, optional
      :param spread_end: Spread to apply at the end time (default is 0).
      :type spread_end: float, optional
      :param spread_forward: Spread to subtract from the forward rate (default is 0).
      :type spread_forward: float, optional

      :returns: Forward rate between t_start and t_end.
      :rtype: float

      .. rubric:: Notes

      This method computes the forward rate implied by the discount factors
      at t_start and t_end, adjusted for spreads.



   .. py:method:: forward_t_start_dt(t_start: float, dt: float, spread_start: float = 0, spread_end: float = 0, spread_forward: float = 0) -> float

      Calculate the forward rate given a start time and a time increment.

      You can adjust the spreads for each time horizon. For example, if you want
      to use the curve but adjust it to a specific spread, you can use
      the `spread_start` and `spread_end` parameters. If you want the result to revert to a curve without a spread, you can apply
      the `spread_forward` parameter that subtracts from the forward rate.

      :param t_start: Start time in years.
      :type t_start: float
      :param dt: Time increment in years.
      :type dt: float
      :param spread_start: Spread to apply at the start time (default is 0).
      :type spread_start: float, optional
      :param spread_end: Spread to apply at the end time (default is 0).
      :type spread_end: float, optional
      :param spread_forward: Spread to subtract from the forward rate (default is 0).
      :type spread_forward: float, optional

      :returns: Forward rate between t_start and t_start + dt.
      :rtype: float

      .. rubric:: Notes

      This method is a convenience wrapper for `forward_t_start_t_end`.



   .. py:method:: forward_dt(date: Union[str, pandas.Timestamp], dt: float, spread_start: float = 0, spread_end: float = 0, spread_forward: float = 0) -> float

      Calculate the forward rate from a given date and time increment.

      You can adjust the spreads for each time horizon. For example, if you want
      to use the curve but adjust it to a specific spread, you can use
      the `spread_start` and `spread_end` parameters. If you want the result to revert to a curve without a spread, you can apply
      the `spread_forward` parameter that subtracts from the forward rate.

      :param date: Start date for the forward rate calculation.
      :type date: Union[str, pd.Timestamp]
      :param dt: Time increment in years.
      :type dt: float
      :param spread_start: Spread to apply at the start date (default is 0).
      :type spread_start: float, optional
      :param spread_end: Spread to apply at the end date (default is 0).
      :type spread_end: float, optional
      :param spread_forward: Spread to subtract from the forward rate (default is 0).
      :type spread_forward: float, optional

      :returns: Forward rate from date over dt years.
      :rtype: float

      .. rubric:: Notes

      This method converts the start date to a time fraction and delegates to `forward_t_start_dt`.



   .. py:method:: forward_dates(start_date: Union[str, pandas.Timestamp], end_date: Union[str, pandas.Timestamp], spread_start: float = 0, spread_end: float = 0, spread_forward: float = 0) -> float

      Calculate the forward rate between two dates.

      You can adjust the spreads for each time horizon. For example, if you want
      to use the curve but adjust it to a specific spread, you can use
      the `spread_start` and `spread_end` parameters. If you want the result to revert to a curve without a spread, you can apply
      the `spread_forward` parameter that subtracts from the forward rate.

      :param start_date: Start date for the forward rate calculation.
      :type start_date: Union[str, pd.Timestamp]
      :param end_date: End date for the forward rate calculation.
      :type end_date: Union[str, pd.Timestamp]
      :param spread_start: Spread to apply at the start date (default is 0).
      :type spread_start: float, optional
      :param spread_end: Spread to apply at the end date (default is 0).
      :type spread_end: float, optional
      :param spread_forward: Spread to subtract from the forward rate (default is 0).
      :type spread_forward: float, optional

      :returns: Forward rate between start_date and end_date.
      :rtype: float

      .. rubric:: Notes

      This method computes the time fraction between the two dates and delegates to `forward_dt`.



   .. py:method:: compare_to(other: YieldCurveBase, maturities: Optional[list] = None) -> pandas.DataFrame

      Compare this curve to another curve (e.g., difference in rates, spreads).
      Returns a DataFrame with columns: Current Curve, Compared Curve, Spread.
      The discount_t and discount_to_rate are applied only to the compared curve.



