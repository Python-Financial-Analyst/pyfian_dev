"""
real_rates.py

Module for computing real interest rates using the Fisher equation and related methods.
"""

def fisher_real_rate(nominal_rate: float, inflation_rate: float) -> float:
    """
    Computes the real interest rate using the Fisher equation (approximate).

    Parameters:
        nominal_rate (float): Nominal interest rate as a decimal (e.g., 0.05 for 5%)
        inflation_rate (float): Expected inflation rate as a decimal (e.g., 0.02 for 2%)

    Returns:
        float: Real interest rate as a decimal
    """
    return nominal_rate - inflation_rate


def fisher_exact_real_rate(nominal_rate: float, inflation_rate: float) -> float:
    """
    Computes the real interest rate using the exact Fisher equation.

    Parameters:
        nominal_rate (float): Nominal interest rate as a decimal
        inflation_rate (float): Expected inflation rate as a decimal

    Returns:
        float: Real interest rate as a decimal
    """
    return (1 + nominal_rate) / (1 + inflation_rate) - 1


if __name__ == "__main__":
    # Example usage
    nominal = 0.05  # 5%
    inflation = 0.02  # 2%

    print("Approximate Real Rate:", fisher_real_rate(nominal, inflation))
    print("Exact Real Rate:", fisher_exact_real_rate(nominal, inflation))
