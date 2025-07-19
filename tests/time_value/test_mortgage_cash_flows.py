import pandas as pd
from pyfian.time_value.mortgage_cash_flows import mortgage_cash_flows


def test_mortgage_cash_flows_basic():
    principal_balance = 100000
    annual_rate = 0.05
    term_years = 1
    payment_interval_months = 12
    term_months = term_years * 12

    df = mortgage_cash_flows(principal_balance, annual_rate, term_months, payment_interval_months)

    assert isinstance(df, pd.DataFrame), "Output should be a pandas DataFrame."
    assert len(df) == term_years * payment_interval_months, (
        "Number of payments should match term * frequency."
    )

    payments = df["Payment"].unique()
    assert len(payments) == 1, "Payment amount should be constant over all periods."

    final_balance = df["Remaining Balance"].iloc[-1]
    assert abs(final_balance) < 1.0, (
        f"Final remaining balance should be near zero, got {final_balance}"
    )


def test_mortgage_cash_flows_zero_interest():
    principal = 120000
    annual_rate = 0.0
    term_years = 10
    payment_frequency = 12

    df = mortgage_cash_flows(principal, annual_rate, term_years, payment_frequency)

    assert all(df["Interest"] == 0), (
        "With 0% interest, all interest payments should be zero."
    )
    total_principal_paid = df["Principal"].sum()
    assert round(total_principal_paid, 2) == round(principal, 2), (
        "Total principal payments should equal the original principal."
    )

if __name__ == "__main__":
    test_mortgage_cash_flows_basic()
    