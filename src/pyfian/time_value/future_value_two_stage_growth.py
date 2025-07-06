def future_value_two_stage_growth(D0: float, r: float, g1: float, n1: int, g2: float, n2: int) -> float:
    """
    Calculates the future value of a two-stage growing investment.

    Parameters:
        D0 (float): Initial investment per period
        r (float): Interest rate per period (as decimal)
        g1 (float): Growth rate during first stage
        n1 (int): Number of periods in first stage
        g2 (float): Growth rate during second stage
        n2 (int): Number of periods in second stage

    Returns:
        float: Future value at the end of (n1 + n2) periods
    """
    total_years = n1 + n2
    total_fv = 0

    for t in range(total_years):
        if t < n1:
            payment = D0 * (1 + g1) ** t
        else:
            base = D0 * (1 + g1) ** (n1 - 1)
            payment = base * (1 + g2) ** (t - n1 + 1)

        fv = payment * (1 + r) ** (total_years - t - 1)
        total_fv += fv

    return total_fv
