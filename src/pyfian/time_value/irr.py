"""
irr.py

Module for computing the Internal Rate of Return (IRR) from a series of cash flows.
"""

import numpy_financial as npf


def npv(rate: float, cash_flows: list[float]) -> float:
    """
    Compute the Net Present Value (NPV) for a series of cash flows.

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
