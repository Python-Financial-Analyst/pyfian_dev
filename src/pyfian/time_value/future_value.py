"""
Module for calculating future values with different growth assumptions.
"""

def future_value_annuity(
    payment: float,
    rate: float,
    periods: int
) -> float:
    """
    Calculates the future value of a series of equal payments with discrete compounding.

    Parameters
    ----------
    payment : float
        Amount invested each period (e.g., annually).
    rate : float
        Interest rate per period (as decimal).
    periods : int
        Number of periods (e.g., years).

    Returns
    -------
    float
        Future value of the investment.

    Examples
    --------
    >>> future_value_annuity(1000, 0.05, 10)
    12577.89  # example value
    """
    fv = payment * (((1 + rate) ** periods - 1) / rate)
    return fv


def future_value_growing_annuity(
    payment: float,
    rate: float,
    growth: float,
    periods: int
) -> float:
    """
    Calculates the future value of a growing annuity (constant growth in payments).

    Parameters
    ----------
    payment : float
        Initial payment.
    rate : float
        Interest rate per period (as decimal).
    growth : float
        Growth rate of payment per period (as decimal).
    periods : int
        Number of periods.

    Returns
    -------
    float
        Future value of the growing annuity.

    Notes
    -----
    If the interest rate equals the growth rate, a simplified formula is used
    to avoid division by zero.

    Examples
    --------
    >>> future_value_growing_annuity(1000, 0.05, 0.03, 10)
    13268.75  # example value
    """
    if rate == growth:
        # Avoid division by zero if r == g
        return payment * periods * (1 + rate) ** (periods - 1)

    fv = payment * ((1 + rate) ** periods - (1 + growth) ** periods) / (rate - growth)
    return fv



def future_value_two_stage_growth(
    D0: float,
    r: float,
    g1: float,
    n1: int,
    g2: float,
    n2: int
) -> float:
    """
    Calculates the future value of a two-stage growing investment.

    Parameters
    ----------
    D0 : float
        Initial investment per period.
    r : float
        Interest rate per period (as decimal).
    g1 : float
        Growth rate during first stage.
    n1 : int
        Number of periods in first stage.
    g2 : float
        Growth rate during second stage.
    n2 : int
        Number of periods in second stage.

    Returns
    -------
    float
        Future value at the end of (n1 + n2) periods.

    Examples
    --------
    >>> future_value_two_stage_growth(100, 0.05, 0.02, 5, 0.03, 10)
    1766.55  # example value
    """
    total_years = n1 + n2
    total_fv = 0.0

    for t in range(total_years):
        if t < n1:
            payment = D0 * (1 + g1) ** t
        else:
            base = D0 * (1 + g1) ** (n1 - 1)
            payment = base * (1 + g2) ** (t - n1 + 1)

        fv = payment * (1 + r) ** (total_years - t - 1)
        total_fv += fv

    return total_fv


