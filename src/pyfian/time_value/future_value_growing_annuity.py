def future_value_growing_annuity(payment: float, rate: float, growth: float, periods: int) -> float:
    """
    Calculates the future value of a growing annuity (constant growth in payments).

    Parameters:
        payment (float): Initial payment
        rate (float): Interest rate per period (as decimal)
        growth (float): Growth rate of payment per period (as decimal)
        periods (int): Number of periods

    Returns:
        float: Future value of the growing annuity
    """
    if rate == growth:
        # Avoid division by zero if r == g
        return payment * periods * (1 + rate) ** (periods - 1)
    fv = payment * ((1 + rate) ** periods - (1 + growth) ** periods) / (rate - growth)
    return fv
