pyfian.time_value.means
=======================

.. py:module:: pyfian.time_value.means


Functions
---------

.. autoapisummary::

   pyfian.time_value.means.geometric_mean
   pyfian.time_value.means.arithmetic_mean
   pyfian.time_value.means.harmonic_mean
   pyfian.time_value.means.weighted_geometric_mean
   pyfian.time_value.means.weighted_harmonic_mean


Module Contents
---------------

.. py:function:: geometric_mean(returns, axis=0)

   Calculate the geometric mean of percent returns.

   The geometric mean is useful for evaluating investment returns over time
   because it accounts for compounding. This function accepts percent returns
   (e.g., 0.05 for +5%), handles NaNs, and works with NumPy arrays and pandas
   Series/DataFrames.

   The geometric mean is calculated as:

   .. math::
       GM = \left(\prod_{i=1}^{n} (1 + r_i)\right)^{\frac{1}{n}} - 1

   where :math:`r_i` are the individual returns.

   :param returns: Input percent returns. For example, a 5% return should be passed as 0.05.
   :type returns: array-like, pandas.Series, or pandas.DataFrame
   :param axis: Axis along which the geometric mean is computed. Default is 0.
                Ignored for 1D inputs (Series or 1D arrays).
   :type axis: int, optional

   :returns: Geometric mean of the percent returns. Returns a float for 1D input and
             a Series for DataFrames.
   :rtype: float or pandas.Series

   :raises ValueError: If any values less than or equal to -1.0 are present (which would make
       1 + return ≤ 0 and thus undefined in log space).

   .. rubric:: Examples

   >>> import numpy as np
   >>> geometric_mean([0.05, 0.10, -0.02])
   np.float64(0.04216388706767926)
   >>> import pandas as pd
   >>> df = pd.DataFrame({
   ...     'Fund A': [0.05, 0.02, np.nan],
   ...     'Fund B': [0.01, -0.03, 0.04]
   ... })
   >>> geometric_mean(df)
   Fund A    0.034891
   Fund B    0.006257
   dtype: float64

   .. rubric:: Notes

   This function assumes returns are in decimal form (e.g., 0.10 = 10%).
   NaN values are ignored.


.. py:function:: arithmetic_mean(returns, axis=0)

   Calculate the arithmetic mean of percent returns.

   The arithmetic mean is a simple average of returns, useful for understanding
   the average return over a period without considering compounding effects.
   This function accepts percent returns (e.g., 0.05 for +5%), handles NaNs,
   and works with NumPy arrays and pandas Series/DataFrames.
   The arithmetic mean is calculated as:

   .. math::
       AM = \frac{1}{n} \sum_{i=1}^{n} r_i

   :param returns: Input percent returns. For example, a 5% return should be passed as 0.05.
   :type returns: array-like, pandas.Series, or pandas.DataFrame
   :param axis: Axis along which the arithmetic mean is computed. Default is 0.
                Ignored for 1D inputs (Series or 1D arrays).
   :type axis: int, optional

   :returns: Arithmetic mean of the percent returns. Returns a float for 1D input and
             a Series for DataFrames.
   :rtype: float or pandas.Series

   .. rubric:: Examples

   >>> import numpy as np
   >>> arithmetic_mean([0.05, 0.10, -0.02])
   np.float64(0.0433333333)
   >>> import pandas as pd
   >>> df = pd.DataFrame({
   ...     'Fund A': [0.05, 0.02, np.nan],
   ...     'Fund B': [0.01, -0.03, 0.04]
   ... })
   >>> arithmetic_mean(df)
   Fund A    0.035000
   Fund B    0.006667
   dtype: float64

   .. rubric:: Notes

   This function assumes returns are in decimal form (e.g., 0.10 = 10%).
   NaN values are ignored.


.. py:function:: harmonic_mean(values, axis=0)

   Calculate the harmonic mean of values.

   The harmonic mean is the reciprocal of the arithmetic mean of the reciprocals.
   In finance, the harmonic mean is especially useful for averaging ratios or rates
   such as price/earnings (P/E) ratios, average cost per share in dollar-cost averaging.
   It is less sensitive to large outliers and is appropriate when the data are defined
   in relation to some unit (e.g., per share, per year).

   This function accepts percent returns (e.g., 0.05 for +5%), handles NaNs,
   and works with NumPy arrays and pandas Series/DataFrames.

   The harmonic mean is calculated as:

   .. math::
       HM = \frac{n}{\sum_{i=1}^{n} \frac{1}{x_i}}
   where :math:`x_i` are the individual values.

   :param values: Input values to calculate the harmonic mean.
   :type values: array-like, pandas.Series, or pandas.DataFrame
   :param axis: Axis along which the harmonic mean is computed. Default is 0.
                Ignored for 1D inputs (Series or 1D arrays).
   :type axis: int, optional

   :returns: Harmonic mean of the percent returns. Returns a float for 1D input and
             a Series for DataFrames.
   :rtype: float or pandas.Series

   .. rubric:: Examples

   Averaging P/E ratios for three companies:
   >>> pe_ratios = [15, 20, 25]
   >>> harmonic_mean(pe_ratios)
   np.float64(19.1489361702)

   Averaging P/E ratios in a DataFrame:
   >>> df = pd.DataFrame({
   ...     'Tech': [30, 25, 35],
   ...     'Finance': [12, 15, 18]
   ... })
   >>> harmonic_mean(df)
   Tech       29.439252
   Finance    14.594595
   dtype: float64

   .. rubric:: Notes

   - The harmonic mean is appropriate for averaging rates or multiples, such as P/E ratios,
     or for calculating the average cost per share in dollar-cost averaging strategies.
   - It is not appropriate for values that can be zero or negative; all returns must be > -1.
   - This function assumes returns are in decimal form (e.g., 0.10 = 10%).
   - NaN values are ignored. Returns less than or equal to zero will raise a ValueError.


.. py:function:: weighted_geometric_mean(returns, weights, axis=0)

   Calculate the weighted geometric mean of percent returns.

   Useful for time-weighted returns, where each return is associated
   with a weight (e.g., time period length).
   Returns and weights must be broadcastable to the same shape.

   This function accepts percent returns (e.g., 0.05 for +5%), handles NaNs,
   and works with NumPy arrays and pandas Series/DataFrames.

   The weighted geometric mean is calculated as:

   .. math::
       WGM = \left(\prod_{i=1}^{n} (1 + r_i)^{w_i}\right)^{\frac{1}{\sum w_i}} - 1
   where :math:`r_i` are the individual returns and :math:`w_i` are the weights.

   :param returns: Input percent returns (e.g., 0.05 for +5%).
   :type returns: array-like, pandas.Series, or pandas.DataFrame
   :param weights: Weights for each return (e.g., time in years or months).
   :type weights: array-like, pandas.Series, or pandas.DataFrame
   :param axis: Axis along which the weighted geometric mean is computed. Default is 0.
   :type axis: int, optional

   :returns: Weighted geometric mean of the percent returns.
   :rtype: float or pandas.Series

   .. rubric:: Examples

   >>> weighted_geometric_mean([0.05, 0.10, 0.02], [1, 2, 1])
   np.float64(0.0669491218)


.. py:function:: weighted_harmonic_mean(values, weights, axis=0)

   Calculate the weighted harmonic mean of values.

   In finance, this is useful for averaging ratios (e.g., P/E ratios) where each value is weighted
   by a relevant factor such as market capitalization.

   This function accepts values (e.g., P/E ratios) and weights (e.g., market capitalization),
   handles NaNs, and works with NumPy arrays and pandas Series/DataFrames.

   The weighted harmonic mean is calculated as:

   .. math::
       WHM = \frac{\sum_{i=1}^{n} w_i}{\sum_{i=1}^{n} \frac{w_i}{x_i}}
   where :math:`x_i` are the individual values and :math:`w_i` are the weights.

   :param values: Input values to calculate the weighted harmonic mean (e.g., P/E ratios).
   :type values: array-like, pandas.Series, or pandas.DataFrame
   :param weights: Weights for each value (e.g., market capitalization).
   :type weights: array-like, pandas.Series, or pandas.DataFrame
   :param axis: Axis along which the weighted harmonic mean is computed. Default is 0.
   :type axis: int, optional

   :returns: Weighted harmonic mean of the values.
   :rtype: float or pandas.Series

   .. rubric:: Examples

   >>> pe = [15, 20, 25]
   >>> caps = [100, 200, 700]
   >>> weighted_harmonic_mean(pe, caps)
   np.float64(22.3880597015)


