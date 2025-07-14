"""
real_rates.py

Module for computing real interest rates using the Fisher equation and related methods.
"""

def fisher_real_rate(nominal_rate: float, inflation_rate: float) -> float:
    """
    Compute the real interest rate using the approximate Fisher equation.

    Parameters
    ----------
    nominal_rate : float
        Nominal interest rate as a decimal (e.g., 0.05 for 5%).
    inflation_rate : float
        Expected inflation rate as a decimal (e.g., 0.02 for 2%).

    Returns
    -------
    float
        Approximate real interest rate as a decimal.

    Examples
    --------
    >>> fisher_real_rate(0.05, 0.02)
    0.03
    """
    return nominal_rate - inflation_rate


def fisher_exact_real_rate(nominal_rate: float, inflation_rate: float) -> float:
    """
    Compute the real interest rate using the exact Fisher equation.

    Parameters
    ----------
    nominal_rate : float
        Nominal interest rate as a decimal.
    inflation_rate : float
        Expected inflation rate as a decimal.

    Returns
    -------
    float
        Exact real interest rate as a decimal.

    Examples
    --------
    >>> round(fisher_exact_real_rate(0.05, 0.02), 6)
    0.029412
    """
    return (1 + nominal_rate) / (1 + inflation_rate) - 1


