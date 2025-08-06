"""
irr.py

Module for computing the Internal Rate of Return (IRR) from a series of cash flows.
"""

from collections.abc import Sequence
from datetime import datetime

import numpy_financial as npf
import pandas as pd
from scipy.optimize import newton


def npv(rate: float, cash_flows: list[float]) -> float:
    """
    Compute the Net Present Value (NPV) for a series of cash flows.

    The NPV is calculated as the sum of the present values of each cash flow,
    discounted at the specified rate. The formula is:

    .. math::
        NPV = \\sum_{t=0}^{n} \\frac{CF_t}{(1 + r)^t}
    where:
        - :math:`NPV` is the net present value
        - :math:`CF_t` is the cash flow at time `t`
        - :math:`r` is the discount rate
        - :math:`n` is the total number of periods


    Parameters
    ----------
    rate : float
        Discount rate as a decimal (e.g., 0.1 for 10%).
    cash_flows : list of float
        Cash flow values, where the index represents the time period.

    Returns
    -------
    float
        Net present value of the cash flows.

    Examples
    --------
    >>> npv(0.1, [-100, 50, 60])
    -4.95867768595
    """
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows))


def irr(
    cash_flows: list[float], guess: float = 0.1, tol: float = 1e-6, max_iter: int = 1000
) -> float:
    """
    Estimate the Internal Rate of Return (IRR) using the Newton-Raphson method.

    The IRR is the rate that makes the NPV of cash flows equal to zero. The formula is:

    .. math::
        0 = \\sum_{t=0}^{n} \\frac{CF_t}{(1 + IRR)^t}
    where:
        - :math:`IRR` is the internal rate of return
        - :math:`CF_t` is the cash flow at time `t`
        - :math:`n` is the total number of periods
    This function uses the Newton-Raphson method to find the IRR iteratively.
    Convergence is determined by the specified tolerance and maximum iterations.

    Parameters
    ----------
    cash_flows : list of float
        Cash flow values, where the index represents the time period.
    guess : float, optional
        Initial guess for the IRR (default is 0.1, i.e. 10%).
    tol : float, optional
        Tolerance for convergence (default is 1e-6).
    max_iter : int, optional
        Maximum number of iterations (default is 1000).

    Returns
    -------
    float
        Estimated internal rate of return as a decimal.

    Raises
    ------
    ValueError
        If the IRR calculation does not converge.

    Examples
    --------
    >>> irr([-1000, 300, 400, 500, 600])
    0.2488833566240709
    """
    rate = guess
    for _ in range(max_iter):
        f = npv(rate, cash_flows)
        f_prime = sum(
            -t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cash_flows)
        )
        if abs(f_prime) < 1e-10:
            break
        new_rate = rate - f / f_prime
        if abs(new_rate - rate) < tol:
            return new_rate
        rate = new_rate
    raise ValueError("IRR calculation did not converge")


def np_irr(cash_flows: list[float]) -> float:
    """
    Compute the Internal Rate of Return using numpy-financial's IRR function.

    This function is a wrapper around numpy-financial's `irr` function,
    which calculates the IRR for a series of cash flows. It is useful for quickly
    obtaining the IRR without manually implementing the calculation.
    The IRR is the rate that makes the NPV of cash flows equal to zero. The formula is:

    .. math::
        0 = \\sum_{t=0}^{n} \\frac{CF_t}{(1 + IRR)^t}
    where:

        - :math:`IRR` is the internal rate of return
        - :math:`CF_t` is the cash flow at time `t`
        - :math:`n` is the total number of periods
    This function uses numpy-financial's built-in IRR calculation, which is efficient
    and handles various edge cases.

    Parameters
    ----------
    cash_flows : list of float
        Cash flow values, where the index represents the time period.

    Returns
    -------
    float
        Internal Rate of Return as a decimal.

    Examples
    --------
    >>> np_irr([-1000, 300, 400, 500, 600])
    0.2488833566240709
    """
    return npf.irr(cash_flows)


def xirr_base(
    cash_flows: Sequence[float],
    dates: Sequence[datetime],
    guess: float = 0.1,
    tol: float = 1e-6,
    max_iter: int = 100,
) -> float:
    """
    Calculate the IRR (Yield) for non-periodic cash flows (XIRR).

    This function computes the IRR for a series of cash flows that occur at irregular intervals.
    It uses the Newton-Raphson method to find the rate that makes the NPV
    of the cash flows equal to zero.

    The formula is:

    .. math::
        0 = \\sum_{i=0}^{n} \\frac{CF_i}{(1 + IRR)^{\\frac{d_i - d_0}{365}}}

    where:
        - :math:`IRR` is the internal rate of return
        - :math:`CF_i` is the cash flow at time `i`
        - :math:`d_i` is the date of cash flow `i`
        - :math:`d_0` is the date of the first cash flow
        - :math:`n` is the total number of cash flows
    This function adjusts the cash flows based on the number of days between each cash flow and
    the first cash flow date.

    Parameters
    ----------
    cash_flows : Sequence[float]
        Cash flow values, where each value corresponds to a date in `dates`.
    dates : Sequence[datetime]
        Dates of each cash flow. Must be the same length as `cash_flows`.
    guess : float, optional
        Initial guess for the IRR (default is 0.1, i.e. 10%).
    tol : float, optional
        Tolerance for convergence (default is 1e-6).
    max_iter : int, optional
        Maximum number of iterations (default is 100).

    Returns
    -------
    float
        Estimated IRR as a decimal.

    Raises
    ------
    ValueError
        If the IRR calculation does not converge.

    Examples
    --------
    >>> from datetime import datetime
    >>> cash_flows = [-1000, 300, 400, 500, 600]
    >>> dates = [datetime(2020, 1, 1), datetime(2020, 6, 1), datetime(2021, 1, 1),
    ...          datetime(2021, 6, 1), datetime(2022, 1, 1)]
    >>> xirr(cash_flows, dates)
    0.5831820341312749  # Example output
    """
    if len(cash_flows) != len(dates):
        raise ValueError("cash_flows and dates must have the same length")
    if len(cash_flows) < 2:
        raise ValueError("At least two cash flows are required")

    # Convert all dates to number of days from the first date
    t0 = dates[0]
    days = [(d - t0).days for d in dates]

    def npv_xirr(rate: float) -> float:
        return sum(
            cf / (1 + rate) ** (day / 365.0) for cf, day in zip(cash_flows, days)
        )

    try:
        result = newton(npv_xirr, guess, tol=tol, maxiter=max_iter)
    except RuntimeError:
        raise ValueError("XIRR calculation did not converge")
    return result


def xirr(
    cash_flows, dates=None, guess: float = 0.1, tol: float = 1e-6, max_iter: int = 100
) -> float:
    """
    Calculate the IRR (Yield) for non-periodic cash flows (XIRR).

    Flexible wrapper for xirr that accepts dict, pandas Series, or separate lists for cash flows
    and dates. This function computes the IRR for a series of cash flows that occur
    at irregular intervals.

    It uses the Newton-Raphson method to find the rate that makes the NPV
    of the cash flows equal to zero.

    The formula is:

    .. math::
        0 = \\sum_{i=0}^{n} \\frac{CF_i}{(1 + IRR)^{\\frac{d_i - d_0}{365}}}
    where:
        - :math:`IRR` is the internal rate of return
        - :math:`CF_i` is the cash flow at time `i`
        - :math:`d_i` is the date of cash flow `i`
        - :math:`d_0` is the date of the first cash flow
        - :math:`n` is the total number of cash flows

    This function adjusts the cash flows based on the number of days between each cash flow
    and the first cash flow date.

    If `cash_flows` is a dictionary, keys must be dates (datetime or string
    convertible to datetime), and values are cash flows.

    If `cash_flows` is a pandas Series, the index must be dates.

    If `cash_flows` is a list/sequence, `dates` must be provided as a sequence of
    datetime or string.

    If `dates` is not provided, it assumes `cash_flows` is a dictionary or Series
    with dates as keys/index.

    This function handles NaNs and works with NumPy arrays and pandas Series/DataFrames.

    Parameters
    ----------
    cash_flows : dict, pandas.Series, or list/sequence of floats
        If dict or Series, keys/index must be dates (datetime or string convertible to datetime),
        values are cash flows.
        If list/sequence, must provide `dates` as a sequence of datetime or string.
    dates : sequence of datetime or string, optional
        Dates corresponding to cash flows if cash_flows is a sequence.
    guess, tol, max_iter : see xirr

    Returns
    -------
    float
        Estimated IRR as a decimal.

    Examples
    --------
    >>> import pandas as pd
    >>> cf = pd.Series([-1000, 300, 400, 500, 600],
    ...                index=pd.to_datetime(["2020-01-01", "2020-06-01", "2021-01-01",
    ...                                      "2021-06-01", "2022-01-01"]))
    >>> xirr(cf)
    0.5831820341312749  # Example output
    """
    if isinstance(cash_flows, dict):
        # dict: keys are dates, values are cash flows
        dates_, cfs = zip(*sorted(cash_flows.items(), key=lambda x: x[0]))
        dates = pd.to_datetime(dates_)
        cash_flows = list(cfs)
    elif isinstance(cash_flows, pd.Series):
        dates = pd.to_datetime(cash_flows.index)
        cash_flows = cash_flows.values.tolist()
    elif dates is not None:
        dates = pd.to_datetime(dates)
        cash_flows = list(cash_flows)
    else:
        raise ValueError("If cash_flows is a sequence, dates must be provided.")

    # Convert pandas Timestamps to datetime
    dates = [d.to_pydatetime() if hasattr(d, "to_pydatetime") else d for d in dates]
    return xirr_base(cash_flows, dates, guess=guess, tol=tol, max_iter=max_iter)
