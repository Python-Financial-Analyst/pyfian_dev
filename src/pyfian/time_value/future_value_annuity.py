def future_value_annuity(payment: float, rate: float, periods: int) -> float:
    """
    Calculates the future value of a series of equal annual payments using discrete compounding.

    Parameters:
        payment (float): Amount invested each period (e.g., annually)
        rate (float): Interest rate per period (as a decimal, e.g., 0.05 for 5%)
        periods (int): Number of periods (e.g., years)

    Returns:
        float: Future value of the investment
    """
    fv = payment * (((1 + rate) ** periods - 1) / rate)
    return fv
