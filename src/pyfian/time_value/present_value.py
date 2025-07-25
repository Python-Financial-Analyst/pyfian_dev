def present_value_annuity(payment: float, rate: float, periods: int) -> float:
    r"""
    Calculate the present value of a fixed annuity.

    The present value of a fixed annuity is given by:

    .. math::
        PV = P \times \frac{1 - (1 + r)^{-n}}{r}

    where:
        - :math:`PV` is the present value
        - :math:`P` is the payment per period
        - :math:`r` is the interest rate per period
        - :math:`n` is the total number of periods

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
        Present value of the fixed annuity.

    Examples
    --------
    >>> present_value_annuity(100, 0.05, 10)
    772.1734929184818
    """
    pv = payment * ((1 - (1 + rate) ** -periods) / rate)
    return pv


def present_value_growing_annuity(
    payment: float, rate: float, growth: float, periods: int
) -> float:
    """
    Calculate the present value of a growing annuity.

    Parameters
    ----------
    payment : float
        The initial payment amount per period.
    rate : float
        The interest rate per period (as a decimal).
    growth : float
        The growth rate of the payments (as a decimal).
    periods : int
        The total number of periods.

    Returns
    -------
    float
        Present value of the growing annuity.

    Examples
    --------
    >>> present_value_growing_annuity(100, 0.05, 0.02, 10)
    838.8105652432927
    >>> present_value_growing_annuity(100, 0.05, 0.05, 10)
    1628.894626777442
    """
    if rate == growth:
        return payment * periods * (1 + rate) ** periods
    pv = payment * ((1 - ((1 + growth) / (1 + rate)) ** periods) / (rate - growth))
    return pv


def present_value_two_stage_annuity(
    payment: float, rate1: float, rate2: float, periods1: int, periods2: int
) -> float:
    """
    Calculate the present value of a two-stage annuity.

    Parameters
    ----------
    payment : float
        The fixed payment amount per period.
    rate1 : float
        Interest rate for the first stage (as a decimal).
    rate2 : float
        Interest rate for the second stage (as a decimal).
    periods1 : int
        Number of periods in the first stage.
    periods2 : int
        Number of periods in the second stage.

    Returns
    -------
    float
        Present value of the two-stage annuity.

    Examples
    --------
    >>> present_value_two_stage_annuity(100, 0.05, 0.06, 5, 5)
    762.9973919305694
    """
    pv_stage1 = present_value_annuity(payment, rate1, periods1)
    pv_stage2 = (
        present_value_annuity(payment, rate2, periods2) / (1 + rate1) ** periods1
    )
    return pv_stage1 + pv_stage2
