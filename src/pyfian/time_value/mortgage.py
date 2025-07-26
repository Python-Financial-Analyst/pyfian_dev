import pandas as pd


def calculate_payment(
    principal: float,
    annual_rate: float,
    term_months: int,
    payment_interval_months: int = 1,
) -> float:
    """
    Calculate the fixed payment per payment period for a mortgage.

    This function computes the payment amount due each payment period given
    the principal, annual interest rate, total loan term in months, and the
    interval between payments in months.

    Parameters
    ----------
    principal : float
        The original loan amount.
    annual_rate : float
        The annual nominal interest rate as a decimal (e.g., 0.04 for 4%).
    term_months : int
        The total loan term expressed in months.
    payment_interval_months : int, optional
        The number of months between payments (default is 1 for monthly payments).
        If None, defaults to 1 (monthly payments).

    Returns
    -------
    float
        The fixed payment amount due each payment period.

    Raises
    ------
    ValueError
        If payment_interval_months is zero or negative, or if total_payments is zero.

    Examples
    --------
    >>> calculate_payment(200000, 0.04, 360, 1)
    954.8305909309076

    >>> calculate_payment(100000, 0.05, 180, 3)
    2378.9930086358786
    """
    if payment_interval_months <= 0:
        raise ValueError("Payment interval (months) must be greater than zero.")

    payments_per_year = 12 / payment_interval_months
    total_payments = term_months // payment_interval_months
    if total_payments <= 0:
        raise ValueError(
            "Total payments must be greater than zero. Ensure term_months "
            "is greater than or equal to payment_interval_months."
        )

    periodic_rate = annual_rate / payments_per_year

    if periodic_rate == 0:
        return principal / total_payments

    return principal * periodic_rate / (1 - (1 + periodic_rate) ** -total_payments)


def generate_amortization_schedule(
    principal: float,
    annual_rate: float,
    term_months: int,
    payment_interval_months: int,
) -> pd.DataFrame:
    """
    Generate the full amortization schedule as a pandas DataFrame.

    Parameters
    ----------
    principal : float
        The original loan amount.
    annual_rate : float
        The annual nominal interest rate as a decimal.
    term_months : int
        The total loan term in months.
    payment_interval_months : int
        The number of months between payments.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing columns: Period, Payment, Interest,
        Principal, Remaining Balance.

    Examples
    --------
    >>> df = generate_amortization_schedule(200000, 0.04, 360, 1)
    >>> df.head()
       Period  Payment  Interest  Principal  Remaining Balance
    0       1   954.83   666.67     288.16          199711.84
    1       2   954.83   665.71     289.12          199422.72
    """
    payments_per_year = 12 / payment_interval_months
    total_payments = term_months // payment_interval_months
    periodic_rate = annual_rate / payments_per_year
    payment = calculate_payment(
        principal, annual_rate, term_months, payment_interval_months
    )

    schedule = []
    remaining_balance = principal

    for period in range(1, total_payments + 1):
        interest_payment = remaining_balance * periodic_rate
        principal_payment = payment - interest_payment
        remaining_balance -= principal_payment

        schedule.append(
            {
                "Period": period,
                "Payment": round(payment, 2),
                "Interest": round(interest_payment, 2),
                "Principal": round(principal_payment, 2),
                "Remaining Balance": round(max(remaining_balance, 0), 2),
            }
        )

    return pd.DataFrame(schedule)


def mortgage_cash_flows(
    principal: float,
    annual_rate: float,
    term_months: int,
    payment_interval_months: int = 1,
) -> pd.DataFrame:
    """
    Calculate mortgage cash flows (amortization schedule).

    Parameters
    ----------
    principal : float
        The loan principal amount.
    annual_rate : float
        Annual nominal interest rate (decimal).
    term_months : int
        Loan term in months.
    payment_interval_months : int, optional
        Months between payments (default is 1 = monthly, 3 = quarterly).

    Returns
    -------
    pd.DataFrame
        Amortization schedule with Period, Payment, Interest,
        Principal, and Remaining Balance.

    Raises
    ------
    ValueError
        For invalid inputs such as negative principal, term, or payment interval.

    Examples
    --------
    >>> df = mortgage_cash_flows(200000, 0.04, 11)
    >>> print(df)
       Period  Payment  Interest  Principal  Remaining Balance
    0       1   18182.95   666.67   17516.28           182483.72
    ...
    """
    if principal <= 0:
        raise ValueError("Principal must be greater than zero.")
    if term_months <= 0:
        raise ValueError("Loan term must be greater than zero months.")
    if payment_interval_months <= 0:
        raise ValueError("Payment interval (months) must be greater than zero.")

    return generate_amortization_schedule(
        principal, annual_rate, term_months, payment_interval_months
    )


# if __name__ == "__main__":
#     df = mortgage_cash_flows(
#         principal_balance=200000,
#         annual_rate=0.04,
#         term_months=10,
#         payment_interval_months=1,
#     )
#     print(df.to_string(index=False))
