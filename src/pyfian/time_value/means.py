import numpy as np
import pandas as pd


def geometric_mean(returns, axis=0):
    """
    Calculate the geometric mean of percent returns.

    The geometric mean is useful for evaluating investment returns over time
    because it accounts for compounding. This function accepts percent returns
    (e.g., 0.05 for +5%), handles NaNs, and works with NumPy arrays and pandas
    Series/DataFrames.

    Parameters
    ----------
    returns : array-like, pandas.Series, or pandas.DataFrame
        Input percent returns. For example, a 5% return should be passed as 0.05.
    axis : int, optional
        Axis along which the geometric mean is computed. Default is 0.
        Ignored for 1D inputs (Series or 1D arrays).

    Returns
    -------
    float or pandas.Series
        Geometric mean of the percent returns. Returns a float for 1D input and
        a Series for DataFrames.

    Raises
    ------
    ValueError
        If any values less than or equal to -1.0 are present (which would make
        1 + return ≤ 0 and thus undefined in log space).

    Examples
    --------
    >>> import numpy as np
    >>> geometric_mean([0.05, 0.10, -0.02])
    0.0416...

    >>> import pandas as pd
    >>> df = pd.DataFrame({
    ...     'Fund A': [0.05, 0.02, np.nan],
    ...     'Fund B': [0.01, -0.03, 0.04]
    ... })
    >>> geometric_mean(df)
    Fund A    0.0343...
    Fund B    0.0059...
    dtype: float64

    Notes
    -----
    This function assumes returns are in decimal form (e.g., 0.10 = 10%).
    NaN values are ignored.
    """
    returns = (
        pd.DataFrame(returns)
        if isinstance(returns, (pd.Series, pd.DataFrame))
        else np.asarray(returns)
    )

    gross_returns = 1 + returns

    if isinstance(gross_returns, pd.DataFrame):
        if (gross_returns <= 0).any().any():
            raise ValueError("All (1 + return) values must be positive.")
        log_returns = np.log(gross_returns)
        mean_log = log_returns.mean(axis=axis, skipna=True)
        return np.exp(mean_log) - 1
    else:
        gross_returns = np.asarray(gross_returns)
        if np.any(gross_returns <= 0):
            raise ValueError("All (1 + return) values must be positive.")
        log_returns = np.log(gross_returns)
        mean_log = np.nanmean(log_returns, axis=axis)
        return np.exp(mean_log) - 1


def arithmetic_mean(returns, axis=0):
    """
    Calculate the arithmetic mean of percent returns.

    The arithmetic mean is a simple average of returns, useful for understanding
    the average return over a period without considering compounding effects.
    This function accepts percent returns (e.g., 0.05 for +5%), handles NaNs,
    and works with NumPy arrays and pandas Series/DataFrames.

    Parameters
    ----------
    returns : array-like, pandas.Series, or pandas.DataFrame
        Input percent returns. For example, a 5% return should be passed as 0.05.
    axis : int, optional
        Axis along which the arithmetic mean is computed. Default is 0.
        Ignored for 1D inputs (Series or 1D arrays).

    Returns
    -------
    float or pandas.Series
        Arithmetic mean of the percent returns. Returns a float for 1D input and
        a Series for DataFrames.

    Examples
    --------
    >>> import numpy as np
    >>> arithmetic_mean([0.05, 0.10, -0.02])
    0.0433...

    >>> import pandas as pd
    >>> df = pd.DataFrame({
    ...     'Fund A': [0.05, 0.02, np.nan],
    ...     'Fund B': [0.01, -0.03, 0.04]
    ... })
    >>> arithmetic_mean(df)
    Fund A    0.0350...
    Fund B   -0.0033...
    dtype: float64

    Notes
    -----
    This function assumes returns are in decimal form (e.g., 0.10 = 10%).
    NaN values are ignored.
    """

    returns = (
        pd.DataFrame(returns)
        if isinstance(returns, (pd.Series, pd.DataFrame))
        else np.asarray(returns)
    )
    if isinstance(returns, pd.DataFrame) or isinstance(returns, pd.Series):
        return returns.mean(axis=axis)
    else:
        return np.nanmean(returns, axis=axis)


def harmonic_mean(values, axis=0):
    """
    Calculate the harmonic mean of values.

    The harmonic mean is the reciprocal of the arithmetic mean of the reciprocals.
    In finance, the harmonic mean is especially useful for averaging ratios or rates
    such as price/earnings (P/E) ratios, average cost per share in dollar-cost averaging.
    It is less sensitive to large outliers and is appropriate when the data are defined
    in relation to some unit (e.g., per share, per year).

    This function accepts percent returns (e.g., 0.05 for +5%), handles NaNs,
    and works with NumPy arrays and pandas Series/DataFrames.

    Parameters
    ----------
    values : array-like, pandas.Series, or pandas.DataFrame
        Input values to calculate the harmonic mean.
    axis : int, optional
        Axis along which the harmonic mean is computed. Default is 0.
        Ignored for 1D inputs (Series or 1D arrays).

    Returns
    -------
    float or pandas.Series
        Harmonic mean of the percent returns. Returns a float for 1D input and
        a Series for DataFrames.

    Examples
    --------
    Averaging P/E ratios for three companies:
    >>> pe_ratios = [15, 20, 25]
    >>> harmonic_mean(pe_ratios)
    18.4615...

    Averaging P/E ratios in a DataFrame:
    >>> df = pd.DataFrame({
    ...     'Tech': [30, 25, 35],
    ...     'Finance': [12, 15, 18]
    ... })
    >>> harmonic_mean(df)
    Tech       29.5139...
    Finance    14.7826...
    dtype: float64

    Notes
    -----
    - The harmonic mean is appropriate for averaging rates or multiples, such as P/E ratios,
      or for calculating the average cost per share in dollar-cost averaging strategies.
    - It is not appropriate for values that can be zero or negative; all returns must be > -1.
    - This function assumes returns are in decimal form (e.g., 0.10 = 10%).
    - NaN values are ignored. Returns less than or equal to zero will raise a ValueError.
    """
    values = (
        pd.DataFrame(values)
        if isinstance(values, (pd.Series, pd.DataFrame))
        else np.asarray(values)
    )

    if (
        (values <= 0).any().any()
        if isinstance(values, pd.DataFrame)
        else (values <= 0).any()
    ):
        raise ValueError("All values must be > 0 for harmonic mean calculation.")

    if isinstance(values, pd.DataFrame):
        invert_values = 1 / values.replace(0, np.nan)
        denom = invert_values.sum(axis=axis, skipna=True)
        n = invert_values.count(axis=axis)
        hmean = n / denom
        return hmean
    else:
        values = values.astype(float)
        values = values[values > 0]
        n = len(values)
        hmean = n / np.sum(1 / values)
        return hmean


def weighted_geometric_mean(returns, weights, axis=0):
    """
    Calculate the weighted geometric mean of percent returns.

    Useful for time-weighted returns, where each return is associated
    with a weight (e.g., time period length).
    Returns and weights must be broadcastable to the same shape.

    Parameters
    ----------
    returns : array-like, pandas.Series, or pandas.DataFrame
        Input percent returns (e.g., 0.05 for +5%).
    weights : array-like, pandas.Series, or pandas.DataFrame
        Weights for each return (e.g., time in years or months).
    axis : int, optional
        Axis along which the weighted geometric mean is computed. Default is 0.

    Returns
    -------
    float or pandas.Series
        Weighted geometric mean of the percent returns.

    Examples
    --------
    >>> weighted_geometric_mean([0.05, 0.10, 0.02], [1, 2, 1])
    0.0669491...
    """
    returns = np.asarray(returns)
    weights = np.asarray(weights)
    gross_returns = 1 + returns
    filter_values = ~np.isnan(weights) & ~np.isnan(gross_returns)
    if np.any(gross_returns <= 0):
        raise ValueError("All (1 + return) values must be positive.")
    weights = weights[filter_values] / np.nansum(
        weights[filter_values], axis=axis, keepdims=True
    )
    log_returns = np.log(gross_returns)[filter_values]
    weighted_log = np.nansum(weights * log_returns, axis=axis)
    return np.exp(weighted_log) - 1


def weighted_harmonic_mean(values, weights, axis=0):
    """
    Calculate the weighted harmonic mean of values.

    In finance, this is useful for averaging ratios (e.g., P/E ratios) where each value is weighted
    by a relevant factor such as market capitalization.

    Parameters
    ----------
    values : array-like, pandas.Series, or pandas.DataFrame
        Input values to calculate the weighted harmonic mean (e.g., P/E ratios).
    weights : array-like, pandas.Series, or pandas.DataFrame
        Weights for each value (e.g., market capitalization).
    axis : int, optional
        Axis along which the weighted harmonic mean is computed. Default is 0.

    Returns
    -------
    float or pandas.Series
        Weighted harmonic mean of the values.

    Examples
    --------
    >>> pe = [15, 20, 25]
    >>> caps = [100, 200, 700]
    >>> weighted_harmonic_mean(pe, caps)
    22.3880597
    """
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    filter_values = ~np.isnan(weights) & ~np.isnan(values)
    if np.any(values[filter_values] <= 0):
        raise ValueError("All values must be > 0 for harmonic mean calculation.")
    weighted_sum = np.nansum(weights[filter_values])
    weighted_reciprocal = np.nansum(
        weights[filter_values] / values[filter_values], axis=axis
    )
    return weighted_sum / weighted_reciprocal
