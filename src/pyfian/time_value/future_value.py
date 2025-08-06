from pyfian.time_value.present_value import (
    present_value_annuity,
    present_value_growing_annuity,
)


def future_value_annuity(payment: float, rate: float, periods: int) -> float:
    """
    Calculate the future value of a fixed annuity.

    The future value of a fixed annuity is given by:

    .. math::
        FV = P \\times (1 + r)^{N} \\times \\frac{1 - \\frac{1}{(1 + r)^{N}}}{r}

    where:
        - :math:`FV` is the future value
        - :math:`P` is the payment per period
        - :math:`r` is the interest rate per period
        - :math:`N` is the total number of periods

    Parameters
    ----------
    payment : float
        The fixed payment amount per period.
    rate : float
        The interest rate per period (as a decimal).
    periods : int
        The total number of periods.

    Returns
    -------
    float
        Future value of the fixed annuity.

    Examples
    --------
    >>> future_value_annuity(100, 0.05, 10)
    1257.7892535548839
    """
    if rate == 0:
        return payment * periods
    pv = present_value_annuity(payment, rate, periods)
    fv = pv * (1 + rate) ** periods
    return fv


def future_value_annuity_annual(
    payment: float, annual_rate: float, years: int, payments_per_year: int
) -> float:
    """
    Calculate the future value of a fixed annuity with an annual interest rate
    and a specified number of payments per year.

    The future value is calculated as:

    .. math::
        FV = P \\times (1 + r)^{N} \\times \\frac{1 - \\frac{1}{(1 + r)^{N}}}{r}

    where:
        - :math:`FV` is the future value
        - :math:`P` is the payment per period
        - :math:`r` is the periodic interest rate (annual_rate / payments_per_year)
        - :math:`N` is the total number of periods,
        with :math:`N = \\text{years} \\times \\text{payments_per_year}`

    This function adjusts the interest rate and number of periods
    for non-annual payment frequencies.

    Parameters
    ----------
    payment : float
        The fixed payment amount per period.
    annual_rate : float
        The annual interest rate (as a decimal).
    years : int
        The total number of years.
    payments_per_year : int
        The number of payments per year.

    Returns
    -------
    float
        Future value of the fixed annuity.

    Examples
    --------
    >>> future_value_annuity_annual(100, 0.05, 10, 12)
    15528.22794456672
    """
    rate = annual_rate / payments_per_year
    periods = years * payments_per_year
    return future_value_annuity(payment, rate, periods)


def future_value_growing_annuity(
    payment: float, rate: float, periods: int, growth: float = 0.0
) -> float:
    """
    Calculate the future value of a growing annuity.

    The future value of a growing annuity accounts for payments that grow at a constant rate over time for a specified number of periods.

    The future value is calculated as:

    .. math::
        FV = P \\times \\frac{(1 + r)^{N} - (1 + g)^{N}}{r - g}

    where:
        - :math:`FV` is the future value
        - :math:`P` is the payment at time t=0
        - :math:`r` is the interest rate per period
        - :math:`g` is the growth rate per period
        - :math:`N` is the total number of periods

    This formula accounts for the growth of payments over time,
    where each payment grows by the growth rate in each period.

    Note
    ----
    The `payment` parameter corresponds to the payment at time t=0.
    Growth is applied in the first period as well, so the payment at time t=k is:
        :math:`P * (1 + g)^{(k+1)}`
    for each period k.

    Parameters
    ----------
    payment : float
        The initial payment amount per period.
    rate : float
        The interest rate per period (as a decimal).
    periods : int
        The total number of periods.
    growth : float, optional
        The growth rate of the payments (as a decimal). Defaults to 0.0.

    Returns
    -------
    float
        Future value of the growing annuity.

    Examples
    --------
    >>> future_value_growing_annuity(100, 0.05, 10, 0.02)
    1393.6607030611262
    >>> future_value_growing_annuity(100, 0.05, 10, 0.05)
    1628.894626777442
    """
    pv = present_value_growing_annuity(payment, rate, periods, growth)
    fv = pv * (1 + rate) ** periods
    return fv
