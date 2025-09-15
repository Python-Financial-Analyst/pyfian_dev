pyfian.yield_curves.flat_curve
==============================

.. py:module:: pyfian.yield_curves.flat_curve

.. autoapi-nested-parse::

   flat_curve.py

   Module for flat yield curve models. Implements:

   - FlatCurveLog: Flat curve with continuously compounded (log) rates.
   - FlatCurveAER: Flat curve with annual effective rates (AER).
   - FlatCurveBEY: Flat curve with bond equivalent yields (BEY).

   Each class provides a different convention for representing flat yield curves, useful for pricing, discounting, and rate conversions in fixed income analytics.

   .. rubric:: Examples

   >>> from pyfian.yield_curves.flat_curve import FlatCurveLog, FlatCurveAER, FlatCurveBEY
   >>> curve_log = FlatCurveLog(0.05, "2020-01-01")
   >>> curve_log.discount_t(1)
   np.float64(0.9512294245)
   >>> curve_log.discount_date("2021-01-01")
   np.float64(0.951099128)
   >>> curve_log.get_rate(1)
   0.05
   >>> curve_log.get_rate(1, yield_calculation_convention="Annual")
   np.float64(0.0512710964)
   >>> curve_log.get_rate(1, yield_calculation_convention="BEY")
   np.float64(0.050630241)
   >>> curve_log.get_rate(1, yield_calculation_convention="Continuous")
   0.05
   >>> curve_log.get_rate(1, yield_calculation_convention="Unknown")
   Traceback (most recent call last):
       ...
   ValueError: Unknown or unsupported yield calculation convention: Unknown

   >>> curve_aer = FlatCurveAER(0.05, "2020-01-01")
   >>> curve_aer.discount_t(1)
   0.9523809524
   >>> curve_aer.discount_date("2021-01-01")
   0.9522536545
   >>> curve_aer.get_rate(1)
   0.05
   >>> curve_aer.get_rate(1, yield_calculation_convention="BEY")
   np.float64(0.0493901532)
   >>> curve_aer.get_rate(1, yield_calculation_convention="Continuous")
   np.float64(0.0487901642)
   >>> curve_aer.get_rate(1, yield_calculation_convention="Unknown")
   Traceback (most recent call last):
       ...
   ValueError: Unknown or unsupported yield calculation convention: Unknown

   >>> curve_bey = FlatCurveBEY(0.05, "2020-01-01")
   >>> curve_bey.discount_t(1)
   0.9518143961927424
   >>> curve_bey.discount_date("2021-01-01")
   0.9518143961927424
   >>> curve_bey.get_rate(1, yield_calculation_convention="Annual")
   np.float64(0.050625)
   >>> curve_bey.get_rate(1, yield_calculation_convention="BEY")
   0.05
   >>> curve_bey.get_rate(1, yield_calculation_convention="Continuous")
   np.float64(0.0493852252)
   >>> curve_bey.get_rate(1, yield_calculation_convention="Unknown")
   Traceback (most recent call last):
       ...
   ValueError: Unknown or unsupported yield calculation convention: Unknown



Classes
-------

.. autoapisummary::

   pyfian.yield_curves.flat_curve.FlatCurveLog
   pyfian.yield_curves.flat_curve.FlatCurveAER
   pyfian.yield_curves.flat_curve.FlatCurveBEY


Module Contents
---------------

.. py:class:: FlatCurveLog(log_rate: float, curve_date: Union[str, pandas.Timestamp], day_count_convention: Optional[str | pyfian.utils.day_count.DayCountBase] = 'actual/365')

   Bases: :py:obj:`pyfian.visualization.mixins.YieldCurvePlotMixin`, :py:obj:`pyfian.yield_curves.base_curve.YieldCurveBase`


   FlatCurveLog represents a flat curve with continuously compounded (log) rates.

   This class is implemented to model a yield curve where the rate is constant and compounded continuously. It is useful for pricing and discounting cash flows under the continuous compounding convention, which is common in quantitative finance.

   :param log_rate: Continuously compounded rate (as decimal, e.g. 0.05 for 5%).
   :type log_rate: float
   :param curve_date: The curve settlement date.
   :type curve_date: str or datetime-like
   :param day_count_convention: The day count convention to use. Defaults to "actual/365".
   :type day_count_convention: str or DayCountBase, optional


   .. py:attribute:: log_rate
      :type:  float


   .. py:attribute:: curve_date
      :type:  pandas.Timestamp
      :value: None



   .. py:attribute:: yield_calculation_convention
      :type:  str
      :value: 'Continuous'



   .. py:attribute:: day_count_convention
      :type:  pyfian.utils.day_count.DayCountBase


   .. py:method:: as_dict() -> dict

      Return curve parameters and metadata as a dictionary.



   .. py:method:: discount_t(t: float, spread: float = 0) -> float

      Discount a cash flow by time t (in years) using log rate.

      The spread is added to the yield in the original curve.

      The formula used is:

      .. math::

          D(t) = e^{-(r + s) t}

      where:
      - D(t) is the discount factor at time t
      - r is the continuously compounded rate for the period
      - s is the spread

      :param t: Time in years.
      :type t: float
      :param spread: Spread to add to the discount rate. Defaults to 0.
      :type spread: float, optional

      :returns: Discount factor.
      :rtype: float

      .. rubric:: Examples

      >>> curve = FlatCurveLog(0.05, "2020-01-01")
      >>> curve.discount_t(1)
      np.float64(0.9512294245)
      >>> # Equivalent to: assert curve.discount_t(1) == pytest.approx(np.exp(-0.05))



   .. py:method:: discount_to_rate(discount_factor: float, t: float, spread: float = 0) -> float

      Convert a discount factor for a period t to a rate.

      The formula used is:

      .. math::

          r = -\frac{\log(D(t))}{t} - s

      where:
      - D(t) is the discount factor at time t
      - r is the Bond Equivalent Yield (BEY) for the period
      - s is the spread

      :param discount_factor: Discount factor to convert.
      :type discount_factor: float
      :param t: Time period (in years).
      :type t: float
      :param spread: Spread to subtract from the rate to get a Risk Free rate. Defaults to 0.
      :type spread: float, optional

      :returns: Continuously compounded rate (as decimal).
      :rtype: float

      .. rubric:: Examples

      >>> curve = FlatCurveLog(0.05, "2020-01-01")
      >>> curve.discount_to_rate(0.951229424500714, 1)
      np.float64(0.05)
      >>> curve.discount_to_rate(0.951229424500714, 1, spread=0.01)
      np.float64(0.04)



   .. py:method:: discount_date(date: Union[str, pandas.Timestamp], spread: float = 0) -> float

      Discount a cash flow by a target date using log rate.

      The spread is added to the yield in the original curve.

      :param date: Target date for discounting.
      :type date: str or datetime-like
      :param spread: Spread to add to the discount rate. Defaults to 0.
      :type spread: float, optional

      :returns: Discount factor.
      :rtype: float

      .. rubric:: Examples

      >>> curve = FlatCurveLog(0.05, "2020-01-01")
      >>> curve.discount_date("2021-01-01")
      np.float64(0.951099128)



   .. py:method:: get_rate(t: float, yield_calculation_convention: Optional[str] = None, spread: float = 0) -> float

      Return the log rate at time horizon t (in years).

      The spread is added to the yield in the original curve.

      yield_calculation_convention can be used to transform the yield to different conventions.

      :param t: Time in years.
      :type t: float
      :param yield_calculation_convention: Yield calculation convention to use. Must be one of "Annual", "BEY", "Continuous".
      :type yield_calculation_convention: str, optional
      :param spread: Spread to add to the yield. Defaults to 0.
      :type spread: float, optional

      :returns: Log rate (continuously compounded).
      :rtype: float

      .. rubric:: Examples

      >>> curve = FlatCurveLog(0.05, "2020-01-01")
      >>> curve.get_rate(1)
      0.05
      >>> curve.get_rate(1, yield_calculation_convention="Annual")
      np.float64(0.0512710964)
      >>> curve.get_rate(1, yield_calculation_convention="BEY")
      np.float64(0.050630241)
      >>> curve.get_rate(1, yield_calculation_convention="Continuous")
      0.05
      >>> curve.get_rate(1, yield_calculation_convention="Unknown")
      Traceback (most recent call last):
          ...
      ValueError: Unknown or unsupported yield calculation convention: Unknown



   .. py:method:: get_t(t, spread=0)


   .. py:method:: _get_t(t, spread=0)

      Get the rate for a cash flow by time t (in years).

      The spread is added to the yield in the original curve.

      :param t: Time in years to discount.
      :type t: float
      :param spread: Spread to add to the discount rate.
      :type spread: float

      :returns: Rate for the cash flow.
      :rtype: float



   .. py:method:: date_rate(date: Union[str, pandas.Timestamp], yield_calculation_convention: Optional[str] = None, spread: float = 0) -> float

      Return the log rate at a specified date.

      The spread is added to the yield in the original curve.

      yield_calculation_convention can be used to transform the yield to different conventions.

      :param date: Target date for rate.
      :type date: str or datetime-like
      :param yield_calculation_convention: Yield calculation convention to use. Must be one of "Annual", "BEY", "Continuous".
      :type yield_calculation_convention: str, optional
      :param spread: Spread to add to the yield. Defaults to 0.
      :type spread: float, optional

      :returns: Log rate (continuously compounded).
      :rtype: float

      .. rubric:: Examples

      >>> curve = FlatCurveLog(0.05, "2020-01-01")
      >>> curve.date_rate("2022-01-01")
      0.05
      >>> curve.date_rate("2022-01-01", yield_calculation_convention="Annual")
      np.float64(0.0512710964)
      >>> curve.date_rate("2022-01-01", yield_calculation_convention="BEY")
      np.float64(0.050630241)
      >>> curve.date_rate("2022-01-01", yield_calculation_convention="Continuous")
      0.05
      >>> curve.date_rate("2022-01-01", yield_calculation_convention="Unknown")
      Traceback (most recent call last):
          ...
      ValueError: Unknown or unsupported yield calculation convention: Unknown



   .. py:method:: __repr__() -> str


.. py:class:: FlatCurveAER(aer: float, curve_date: Union[str, pandas.Timestamp], day_count_convention: Optional[str | pyfian.utils.day_count.DayCountBase] = 'actual/365')

   Bases: :py:obj:`pyfian.visualization.mixins.YieldCurvePlotMixin`, :py:obj:`pyfian.yield_curves.base_curve.YieldCurveBase`


   FlatCurveAER represents a flat curve with annual effective rates (AER).

   This class is implemented to model a yield curve where the rate is constant and compounded annually. It is useful for pricing and discounting cash flows under the annual effective rate convention, which is standard in many fixed income markets.

   :param aer: Annual effective rate (as decimal, e.g. 0.05 for 5%).
   :type aer: float
   :param curve_date: The curve settlement date.
   :type curve_date: str or datetime-like
   :param day_count_convention: The day count convention to use. Defaults to "actual/365".
   :type day_count_convention: str or DayCountBase, optional


   .. py:attribute:: aer
      :type:  float


   .. py:attribute:: curve_date
      :type:  pandas.Timestamp
      :value: None



   .. py:attribute:: yield_calculation_convention
      :type:  str
      :value: 'Annual'



   .. py:attribute:: day_count_convention
      :type:  pyfian.utils.day_count.DayCountBase


   .. py:method:: as_dict() -> dict

      Return curve parameters and metadata as a dictionary.



   .. py:method:: discount_t(t: float, spread: float = 0) -> float

      Discount a cash flow by time t (in years) using annual effective rate.

      The spread is added to the yield in the original curve.

      The formula used is

      .. math::

          D(t) = (1 + r + s)^{-t}

      where
      - D(t) is the discount factor at time t
      - r is the annual effective rate (AER) for the period
      - s is the spread

      :param t: Time in years.
      :type t: float
      :param spread: Spread to add to the yield. Defaults to 0.
      :type spread: float, optional

      :returns: Discount factor.
      :rtype: float

      .. rubric:: Examples

      >>> curve = FlatCurveAER(0.05, "2020-01-01")
      >>> curve.discount_t(1)
      0.9523809524



   .. py:method:: discount_to_rate(discount_factor: float, t: float, spread: float = 0) -> float

      Convert a discount factor for a period t to a rate.

      The formula used is:

      .. math::

          r = (\frac{1}{D(t)})^{\frac{1}{t}} - 1 - s

      where:
      - D(t) is the discount factor at time t
      - r is the Bond Equivalent Yield (BEY) for the period
      - s is the spread

      :param discount_factor: Discount factor.
      :type discount_factor: float
      :param t: Time in years.
      :type t: float
      :param spread: Spread to subtract from the yield to get a Risk Free rate. Defaults to 0.
      :type spread: float, optional

      :returns: Annual effective rate (AER).
      :rtype: float

      .. rubric:: Examples

      >>> curve = FlatCurveAER(0.05, "2020-01-01")
      >>> curve.discount_to_rate(0.9523809523809523, 1)
      0.05
      >>> curve.discount_to_rate(0.9523809523809523, 1, spread=0.01)
      0.04



   .. py:method:: discount_date(date: Union[str, pandas.Timestamp], spread: float = 0) -> float

      Discount a cash flow by a target date using annual effective rate.

      The spread is added to the yield in the original curve.

      :param date: Target date for discounting.
      :type date: str or datetime-like
      :param spread: Spread to add to the discount rate. Defaults to 0.
      :type spread: float, optional

      :returns: Discount factor.
      :rtype: float

      .. rubric:: Examples

      >>> curve = FlatCurveAER(0.05, "2020-01-01")
      >>> curve.discount_date("2021-01-01")
      0.9522536545



   .. py:method:: get_rate(t: float, yield_calculation_convention: Optional[str] = None, spread: float = 0) -> float

      Return the annual effective rate at time horizon t (in years).

      The spread is added to the yield in the original curve.

      yield_calculation_convention can be used to transform the yield to different conventions.

      :param t: Time in years.
      :type t: float
      :param yield_calculation_convention: Yield calculation convention to use. Must be one of "Annual", "BEY", "Continuous".
      :type yield_calculation_convention: str, optional
      :param spread: Spread to add to the yield. Defaults to 0.
      :type spread: float, optional

      :returns: Annual effective rate.
      :rtype: float

      .. rubric:: Examples

      >>> curve = FlatCurveAER(0.05, "2020-01-01")
      >>> curve.get_rate(1)
      0.05
      >>> curve.get_rate(1, yield_calculation_convention="BEY")
      np.float64(0.0493901532)
      >>> curve.get_rate(1, yield_calculation_convention="Continuous")
      np.float64(0.0487901642)
      >>> curve.get_rate(1, yield_calculation_convention="Unknown")
      Traceback (most recent call last):
          ...
      ValueError: Unknown or unsupported yield calculation convention: Unknown



   .. py:method:: get_t(t, spread=0)


   .. py:method:: _get_t(t, spread=0)

      Get the rate for a cash flow by time t (in years).

      The spread is added to the yield in the original curve.

      :param t: Time in years to discount.
      :type t: float
      :param spread: Spread to add to the discount rate.
      :type spread: float

      :returns: Rate for the cash flow.
      :rtype: float



   .. py:method:: date_rate(date: Union[str, pandas.Timestamp], yield_calculation_convention: Optional[str] = None, spread: float = 0) -> float

      Return the annual effective rate at a specified date.

      The spread is added to the yield in the original curve.

      yield_calculation_convention can be used to transform the yield to different conventions.

      :param date: Target date for rate.
      :type date: str or datetime-like
      :param yield_calculation_convention: Yield calculation convention to use. Must be one of "Annual", "BEY", "Continuous".
      :type yield_calculation_convention: str, optional
      :param spread: Spread to add to the yield. Defaults to 0.
      :type spread: float, optional

      :returns: Annual effective rate.
      :rtype: float

      .. rubric:: Examples

      >>> curve = FlatCurveAER(0.05, "2020-01-01")
      >>> curve.date_rate("2022-01-01")
      0.05
      >>> curve.date_rate("2022-01-01", yield_calculation_convention="BEY")
      np.float64(0.0493901532)
      >>> curve.date_rate("2022-01-01", yield_calculation_convention="Continuous")
      np.float64(0.0487901642)
      >>> curve.date_rate("2022-01-01", yield_calculation_convention="Unknown")
      Traceback (most recent call last):
          ...
      ValueError: Unknown or unsupported yield calculation convention: Unknown



   .. py:method:: __repr__() -> str


.. py:class:: FlatCurveBEY(bey: float, curve_date: Union[str, pandas.Timestamp], day_count_convention: Optional[str | pyfian.utils.day_count.DayCountBase] = '30/360')

   Bases: :py:obj:`pyfian.visualization.mixins.YieldCurvePlotMixin`, :py:obj:`pyfian.yield_curves.base_curve.YieldCurveBase`


   FlatCurveBEY represents a flat curve with bond equivalent yields (BEY).

   This class is implemented to model a yield curve where the rate is constant and quoted as a bond equivalent yield. BEY is a market convention for quoting yields on semiannual coupon bonds.

   :param bey: Bond equivalent yield (as decimal, e.g. 0.05 for 5%).
   :type bey: float
   :param curve_date: The curve settlement date.
   :type curve_date: str or datetime-like
   :param day_count_convention: The day count convention to use. Defaults to "30/360".
   :type day_count_convention: str or DayCountBase, optional


   .. py:attribute:: bey
      :type:  float


   .. py:attribute:: curve_date
      :type:  pandas.Timestamp
      :value: None



   .. py:attribute:: yield_calculation_convention
      :type:  str
      :value: 'BEY'



   .. py:attribute:: day_count_convention
      :type:  pyfian.utils.day_count.DayCountBase


   .. py:method:: as_dict() -> dict

      Return curve parameters and metadata as a dictionary.



   .. py:method:: discount_t(t: float, spread: float = 0) -> float

      Discount a cash flow by time t (in years) using annual effective rate.

      The spread is added to the yield in the original curve.

      The formula used is

      .. math::

          D(t) = (1 + (r + s) / 2 )^{-t * 2}

      where
      - D(t) is the discount factor at time t
      - r is the Bond Equivalent Yield (BEY) for the period
      - s is the spread

      :param t: Time in years.
      :type t: float
      :param spread: Spread to add to the discount rate. Defaults to 0.
      :type spread: float, optional

      :returns: Discount factor.
      :rtype: float

      .. rubric:: Examples

      >>> curve = FlatCurveBEY(0.05, "2020-01-01")
      >>> curve.discount_t(1)
      0.9518143961927424



   .. py:method:: discount_to_rate(discount_factor: float, t: float, spread: float = 0) -> float

      Convert a discount factor for a period t to a rate.

      The formula used is:

      .. math::

          r = 2 * ((\frac{1}{D(t)})^{\frac{1}{t * 2}} - 1) - s

      where:
      - D(t) is the discount factor at time t
      - r is the Bond Equivalent Yield (BEY) for the period
      - s is the spread

      :param discount_factor: Discount factor.
      :type discount_factor: float
      :param t: Time in years.
      :type t: float
      :param spread: Spread to subtract from the yield to get a Risk Free rate. Defaults to 0.
      :type spread: float, optional

      :returns: Bond Equivalent Yield (BEY).
      :rtype: float

      .. rubric:: Examples

      >>> curve = FlatCurveAER(0.05, "2020-01-01")
      >>> curve.discount_to_rate(0.975609756097561, 1)
      0.025
      >>> curve.discount_to_rate(0.9523809523809523, 1, spread=0.01)
      0.04



   .. py:method:: discount_date(date: Union[str, pandas.Timestamp], spread: float = 0) -> float

      Discount a cash flow by a target date using annual effective rate.

      The spread is added to the yield in the original curve.

      :param date: Target date for discounting.
      :type date: str or datetime-like
      :param spread: Spread to add to the discount rate. Defaults to 0.
      :type spread: float, optional

      :returns: Discount factor.
      :rtype: float

      .. rubric:: Examples

      >>> curve = FlatCurveBEY(0.05, "2020-01-01")
      >>> curve.discount_date("2021-01-01")
      0.9518143961927424



   .. py:method:: get_rate(t: float, yield_calculation_convention: Optional[str] = None, spread: float = 0) -> float

      Return the annual effective rate at time horizon t (in years).

      The spread is added to the yield in the original curve.

      yield_calculation_convention can be used to transform the yield to different conventions.

      :param t: Time in years.
      :type t: float
      :param yield_calculation_convention: Yield calculation convention to use. Must be one of "Annual", "BEY", "Continuous".
      :type yield_calculation_convention: str, optional
      :param spread: Spread to add to the yield. Defaults to 0.
      :type spread: float, optional

      :returns: Annual effective rate.
      :rtype: float

      .. rubric:: Examples

      >>> curve = FlatCurveBEY(0.05, "2020-01-01")
      >>> curve.get_rate(1)
      0.05
      >>> curve.get_rate(1, yield_calculation_convention="Annual")
      np.float64(0.050625)
      >>> curve.get_rate(1, yield_calculation_convention="BEY")
      0.05
      >>> curve.get_rate(1, yield_calculation_convention="Continuous")
      np.float64(0.0493852252)
      >>> curve.get_rate(1, yield_calculation_convention="Unknown")
      Traceback (most recent call last):
          ...
      ValueError: Unknown or unsupported yield calculation convention: Unknown



   .. py:method:: get_t(t, spread=0)


   .. py:method:: _get_t(t, spread=0)

      Get the rate for a cash flow by time t (in years).

      The spread is added to the yield in the original curve.

      :param t: Time in years to discount.
      :type t: float
      :param spread: Spread to add to the discount rate.
      :type spread: float

      :returns: Rate for the cash flow.
      :rtype: float



   .. py:method:: date_rate(date: Union[str, pandas.Timestamp], yield_calculation_convention: Optional[str] = None, spread: float = 0) -> float

      Return the annual effective rate at a specified date.

      The spread is added to the yield in the original curve.

      yield_calculation_convention can be used to transform the yield to different conventions.

      :param date: Target date for rate.
      :type date: str or datetime-like
      :param yield_calculation_convention: Yield calculation convention to use. Must be one of "Annual", "BEY", "Continuous".
      :type yield_calculation_convention: str, optional

      :returns: Annual effective rate.
      :rtype: float

      .. rubric:: Examples

      >>> curve = FlatCurveBEY(0.05, "2020-01-01")
      >>> curve.date_rate("2022-01-01")
      0.05
      >>> curve.date_rate("2022-01-01", yield_calculation_convention="Annual")
      np.float64(0.050625)
      >>> curve.date_rate("2022-01-01", yield_calculation_convention="BEY")
      0.05
      >>> curve.date_rate("2022-01-01", yield_calculation_convention="Continuous")
      np.float64(0.0493852252)
      >>> curve.date_rate("2022-01-01", yield_calculation_convention="Unknown")
      Traceback (most recent call last):
          ...
      ValueError: Unknown or unsupported yield calculation convention: Unknown



   .. py:method:: __repr__() -> str


