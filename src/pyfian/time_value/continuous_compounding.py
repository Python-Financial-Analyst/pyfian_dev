"""
continuous_compounding.py

Module for calculations using continuous compounding.
"""

import math


def future_value_continuous(pv: float, rate: float, time: float) -> float:
    """
    Compute the future value with continuous compounding.

    Parameters
    ----------
    pv : float
        Present value.
    rate : float
        Annual interest rate (as decimal).
    time : float
        Time in years.

    Returns
    -------
    float
        Future value.

    Examples
    --------
    >>> future_value_continuous(1000, 0.05, 3)
    1157.625
    """
    return pv * math.exp(rate * time)


def present_value_continuous(fv: float, rate: float, time: float) -> float:
    """
    Compute the present value with continuous compounding.

    Parameters
    ----------
    fv : float
        Future value.
    rate : float
        Annual interest rate (as decimal).
    time : float
        Time in years.

    Returns
    -------
    float
        Present value.

    Examples
    --------
    >>> present_value_continuous(1157.625, 0.05, 3)
    1000.0
    """
    return fv * math.exp(-rate * time)


def effective_annual_rate_continuous(rate: float) -> float:
    """
    Convert a continuously compounded rate to an effective annual rate.

    Parameters
    ----------
    rate : float
        Continuously compounded rate (as decimal).

    Returns
    -------
    float
        Effective annual rate (as decimal).

    Examples
    --------
    >>> effective_annual_rate_continuous(0.05)
    0.05127109637602411
    """
    return math.exp(rate) - 1


def continuous_rate_from_effective(effective_rate: float) -> float:
    """
    Convert an effective annual rate to a continuously compounded rate.

    Parameters
    ----------
    effective_rate : float
        Effective annual rate (as decimal).

    Returns
    -------
    float
        Continuously compounded rate (as decimal).

    Examples
    --------
    >>> continuous_rate_from_effective(0.05127109637602411)
    0.05
    """
    return math.log(1 + effective_rate)
