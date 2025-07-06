"""
irr.py

Module for computing the Internal Rate of Return (IRR) from a series of cash flows.
"""

import numpy as np


def npv(rate: float, cash_flows: list[float]) -> float:
    """
    Computes the Net Present Value (NPV) for a series of cash flows.

    Parameters:
        rate (float): Discount rate as a decimal
        cash_flows (list of float): Cash flow values, where index represents time

    Returns:
        float: Net present value
    """
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows))


def irr(cash_flows: list[float], guess: float = 0.1, tol: float = 1e-6, max_iter: int = 1000) -> float:
    """
    Estimates the Internal Rate of Return (IRR) using Newton-Raphson method.

    Parameters:
        cash_flows (list of float): Cash flow values, where index represents time
        guess (float): Initial guess for IRR
        tol (float): Tolerance for convergence
        max_iter (int): Maximum number of iterations

    Returns:
        float: Estimated IRR as a decimal

    Raises:
        ValueError: If IRR does not converge
    """
    rate = guess
    for _ in range(max_iter):
        f = npv(rate, cash_flows)
        f_prime = sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cash_flows))
        if abs(f_prime) < 1e-10:
            break
        new_rate = rate - f / f_prime
        if abs(new_rate - rate) < tol:
            return new_rate
        rate = new_rate
    raise ValueError("IRR calculation did not converge")


def np_irr(cash_flows: list[float]) -> float:
    """
    Computes IRR using NumPy's built-in IRR function.

    Parameters:
        cash_flows (list of float): Cash flow values

    Returns:
        float: Internal Rate of Return as a decimal
    """
    return np.irr(cash_flows)


if __name__ == "__main__":
    # Example usage
    example_cash_flows = [-1000, 300, 400, 500, 600]
    
    print("Custom IRR:", irr(example_cash_flows))
    print("NumPy IRR:", np_irr(example_cash_flows))
