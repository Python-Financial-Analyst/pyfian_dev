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
    returns = pd.DataFrame(returns) if isinstance(returns, (pd.Series, pd.DataFrame)) else np.asarray(returns)

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
    
    returns = pd.DataFrame(returns) if isinstance(returns, (pd.Series, pd.DataFrame)) else np.asarray(returns)
    
    return returns.mean(axis=axis, skipna=True)


def harmonic_mean(returns, axis=0):
    """
    Calculate the harmonic mean of percent returns.

    The harmonic mean is the reciprocal of the arithmetic mean of the reciprocals.
    It is useful for averaging ratios or rates and is less sensitive to large outliers.
    This function accepts percent returns (e.g., 0.05 for +5%), handles NaNs,
    and works with NumPy arrays and pandas Series/DataFrames.

    Parameters
    ----------
    returns : array-like, pandas.Series, or pandas.DataFrame
        Input percent returns. For example, a 5% return should be passed as 0.05.
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
    >>> harmonic_mean([0.05, 0.10, 0.02])
    0.0491...

    >>> df = pd.DataFrame({
    ...     'Fund A': [0.05, 0.02, np.nan],
    ...     'Fund B': [0.01, 0.03, 0.04]
    ... })
    >>> harmonic_mean(df)
    Fund A    0.0290...
    Fund B    0.0222...
    dtype: float64

    Notes
    -----
    This function assumes returns are in decimal form (e.g., 0.10 = 10%).
    NaN values are ignored. Returns less than or equal to zero will raise a warning
    or error since harmonic mean requires positive values.
    """
    returns = pd.DataFrame(returns) if isinstance(returns, (pd.Series, pd.DataFrame)) else np.asarray(returns)

    growth_factors = returns + 1

    if (growth_factors <= 0).any().any() if isinstance(growth_factors, pd.DataFrame) else (growth_factors <= 0).any():
        raise ValueError("All returns must be > -1 (growth factors > 0) for harmonic mean calculation.")

    if isinstance(growth_factors, pd.DataFrame):
        n = growth_factors.count(axis=axis)
        denom = growth_factors.replace(0, np.nan).rpow(-1).sum(axis=axis, skipna=True)
        hmean = n / denom
        return hmean - 1
    else:
        growth_factors = growth_factors.astype(float)
        growth_factors = growth_factors[growth_factors > 0]
        n = len(growth_factors)
        hmean = n / np.sum(1 / growth_factors)
        return hmean - 1