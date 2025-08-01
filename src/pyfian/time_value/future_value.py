from pyfian.time_value.present_value import (
    present_value_annuity,
    present_value_growing_annuity,
)


def future_value_annuity(payment: float, rate: float, periods: int) -> float:
    r"""
    Calculate the future value of a fixed annuity.

    The future value of a fixed annuity is given by:

    .. math::
        FV = P \times (1 + r)^{N} \times \frac{1 - \frac{1}{(1 + r)^{N}}}{r}

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
    r"""
    Calculate the future value of a fixed annuity with an annual interest rate
    and a specified number of payments per year.

    The future value is calculated as:

    .. math::
        FV = P \times (1 + r)^{N} \times \frac{1 - \frac{1}{(1 + r)^{N}}}{r}

    where:
        - :math:`P` is the payment per period
        - :math:`r` is the periodic interest rate (annual_rate / payments_per_year)
        - :math:`N` is the total number of periods,
        with :math:`N = \text{years} \times \text{payments_per_year}`

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
    r"""
    Calculate the future value of a growing annuity.

    The future value is calculated as:

    .. math::
        FV = P \times \frac{(1 + r)^{N} - (1 + g)^{N}}{r - g}

    where:
        - :math:`FV` is the future value
        - :math:`P` is the payment at time t=0
        - :math:`r` is the interest rate per period
        - :math:`g` is the growth rate per period
        - :math:`N` is the total number of periods

    Note
    ----
        {\left(\frac{1 + r}{1 + g}\right) - 1}

    where:
        - :math:`P` is the payment at time t=0
        - :math:`r` is the interest rate per period
        - :math:`g` is the growth rate per period
        - :math:`n` is the total number of periods

    Note
    ----
    The `payment` parameter corresponds to the payment at time t=0.
    Growth is applied in the first period as well, so the payment at time t=k is:
        payment * (1 + growth)^(k+1)
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


# def future_value_growing_perpetuity(
#     payment: float, rate: float, growth: float
# ) -> float:
#     r"""
#     Calculate the present value of a growing perpetuity (infinite growing annuity).

#     The present value of a growing perpetuity is given by:

#     .. math::
#         PV = \frac{P \times (1+g)}{r - g}

#     where:
#         - :math:`PV` is the present value
#         - :math:`P` is the payment per period
#         - :math:`r` is the interest rate per period
#         - :math:`g` is the growth rate per period

#     Note
#     ----
#     The `payment` parameter corresponds to the payment at time t=0.
#     Growth is applied in the first period as well, so the payment at time t=k is:
#         payment * (1 + growth)^(k+1)
#     for each period k.


#     Parameters
#     ----------
#     payment : float
#         The initial payment amount per period.
#     rate : float
#         The interest rate per period (as a decimal).
#     growth : float
#         The growth rate of the payments (as a decimal).

#     Returns
#     -------
#     float
#         Present value of the growing perpetuity.

#     Raises
#     ------
#     ValueError
#         If rate <= growth (would result in division by zero or negative present value).

#     Examples
#     --------
#     >>> present_value_growing_perpetuity(100, 0.05, 0.02)
#     3400.0
#     """
#     if rate <= growth:
#         raise ValueError(
#             "Interest rate must be greater than growth rate for perpetuity."
#         )
#     return present_value_growing_annuity(payment, annual_rate, years, payments_per_year)


# def present_value_two_stage_annuity(
#     payment: float, rate1: float, rate2: float, periods1: int, periods2: int
# ) -> float:
#     r"""
#     Calculate the present value of a two-stage annuity.

#     The present value is calculated as:

#     .. math::
#         PV = PV_{\text{stage1}} + PV_{\text{stage2}}
#     where:
#         - :math:`PV_{\text{stage1}}` is the present value of the first stage annuity
#         - :math:`PV_{\text{stage2}}` is the present value of the second stage annuity
#     The present value of the first stage is calculated using the `present_value_annuity`
#     function, and the second stage is calculated using the `present_value_annuity`
#     function, discounted back to the present using the interest rate of the first stage.

#     Note
#     ----
#     The `payment` parameter corresponds to the payment at time t=0.
#     Growth is applied in the first period as well, so the payment at time t=k is:
#         payment * (1 + growth)^(k+1)
#     for each period k.

#     Parameters
#     ----------
#     payment : float
#         The fixed payment amount per period.
#     rate1 : float
#         Interest rate for the first stage (as a decimal).
#     rate2 : float
#         Interest rate for the second stage (as a decimal).
#     periods1 : int
#         Number of periods in the first stage.
#     periods2 : int
#         Number of periods in the second stage.

#     Returns
#     -------
#     float
#         Present value of the two-stage annuity.

#     Examples
#     --------
#     >>> present_value_two_stage_annuity(100, 0.05, 0.06, 5, 5)
#     762.9973919305694
#     """
#     pv_stage1 = present_value_annuity(payment, rate1, periods1)
#     pv_stage2 = (
#         present_value_annuity(payment, rate2, periods2) / (1 + rate1) ** periods1
#     )
#     return pv_stage1 + pv_stage2


# def present_value_two_stage_annuity_perpetuity(
#     payment: float,
#     rate1: float,
#     periods1: int,
#     rate2: float,
#     growth1: float = 0.0,
#     growth2: float = 0.0,
# ) -> float:
#     r"""
#     Calculate the present value of a two-stage annuity where the first stage
#     is a (possibly growing) annuity and the second stage is a (possibly growing) perpetuity.

#     The present value is calculated as:

#     .. math::
#         PV = PV_{\text{stage1}} + PV_{\text{stage2}}
#     where:
#         - :math:`PV_{\text{stage1}}` is the present value of the first stage annuity
#         - :math:`PV_{\text{stage2}}` is the present value of the second stage perpetuity.
#     The present value of the first stage is calculated using the `present_value_growing_annuity`
#     function, and the second stage is calculated using the `present_value_growing_perpetuity`
#     function.
#     The perpetuity is discounted back to the present using the interest rate of the first stage.

#     Note
#     ----
#     The `payment` parameter corresponds to the payment at time t=0.
#     Growth is applied in the first period as well, so the payment at time t=k is:
#         payment * (1 + growth)^(k+1)
#     for each period k.

#     Parameters
#     ----------
#     payment : float
#         The payment amount at time t=0.
#     rate1 : float
#         Interest rate for the first stage (as a decimal).
#     periods1 : int
#         Number of periods in the first stage.
#     rate2 : float
#         Interest rate for the second stage/perpetuity (as a decimal).
#     growth1 : float, optional
#         Growth rate for the first stage payments (as a decimal, default is 0 for level annuity).
#     growth2 : float, optional
#         Growth rate for the perpetuity payments (as a decimal, default is 0 for level perpetuity).

#     Returns
#     -------
#     float
#         Present value of the two-stage annuity with perpetuity.

#     Raises
#     ------
#     ValueError
#         If rate2 <= growth2 (would result in division by zero or negative present value).

#     Examples
#     --------
#     >>> present_value_two_stage_annuity_perpetuity(100, 0.05, 5, 0.06, 0.02, 0.01)
#     2206.1948451002554
#     """
#     # Present value of first stage (fixed annuity)
#     pv_stage1 = present_value_growing_annuity(payment, rate1, periods1, growth1)
#     # Update payment for perpetuity to reflect growth over first stage
#     payment_perpetuity = (
#         payment * (1 + growth1) ** periods1 if growth1 != 0 else payment
#     )
#     # Use present_value_growing_perpetuity for perpetuity at the end of stage 1
#     pv_perpetuity = present_value_growing_perpetuity(payment_perpetuity, rate2, growth2)
#     # Discount perpetuity back to present
#     pv_stage2 = pv_perpetuity / (1 + rate1) ** periods1
#     return pv_stage1 + pv_stage2
