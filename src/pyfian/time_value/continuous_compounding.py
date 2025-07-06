"""
continuous_compounding.py

Module for calculations using continuous compounding.
"""

import math


def future_value_continuous(pv: float, rate: float, time: float) -> float:
    """
    Computes the future value with continuous compounding.

    Parameters:
        pv (float): Present value
        rate (float): Annual interest rate (as decimal)
        time (float): Time in years

    Returns:
        float: Future value
    """
    return pv * math.exp(rate * time)


def present_value_continuous(fv: float, rate: float, time: float) -> float:
    """
    Computes the present value with continuous compounding.

    Parameters:
        fv (float): Future value
        rate (float): Annual interest rate (as decimal)
        time (float): Time in years

    Returns:
        float: Present value
    """
    return fv * math.exp(-rate * time)


def effective_annual_rate_continuous(rate: float) -> float:
    """
    Converts a continuously compounded rate to an effective annual rate.

    Parameters:
        rate (float): Continuously compounded rate (as decimal)

    Returns:
        float: Effective annual rate (as decimal)
    """
    return math.exp(rate) - 1


def continuous_rate_from_effective(effective_rate: float) -> float:
    """
    Converts an effective annual rate to a continuously compounded rate.

    Parameters:
        effective_rate (float): Effective annual rate (as decimal)

    Returns:
        float: Continuously compounded rate (as decimal)
    """
    return math.log(1 + effective_rate)


if __name__ == "__main__":
    # Example usage
    pv = 1000
    r = 0.05
    t = 3

    fv = future_value_continuous(pv, r, t)
    print("Future Value (continuous):", fv)
    print("Present Value (continuous):", present_value_continuous(fv, r, t))
    print("Effective Annual Rate:", effective_annual_rate_continuous(r))
    print("Continuous Rate from EAR:", continuous_rate_from_effective(0.05127))
