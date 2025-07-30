import re

import pandas as pd
import pytest

from pyfian.time_value.mortgage import calculate_payment, mortgage_cash_flows


class TestMortgageCashFlows:
    def test_mortgage_cash_flows_basic(self):
        principal_balance = 100000
        annual_rate = 0.05
        term_years = 1
        payment_interval_months = 1  # Monthly payments (1 month between payments)
        term_months = term_years * 12

        df = mortgage_cash_flows(
            principal_balance, annual_rate, term_months, payment_interval_months
        )

        assert isinstance(df, pd.DataFrame), "Output should be a pandas DataFrame."
        assert (
            len(df) == term_months // payment_interval_months
        ), "Number of payments should match term_months // payment_interval_months."

        payments = df["Payment"].unique()
        assert len(payments) == 1, "Payment amount should be constant over all periods."

        final_balance = df["Remaining Balance"].iloc[-1]
        assert (
            abs(final_balance) < 1.0
        ), f"Final remaining balance should be near zero, got {final_balance}"

    def test_mortgage_cash_flows_zero_interest(self):
        principal = 120000
        annual_rate = 0.0
        term_years = 10
        payment_interval_months = 1  # Monthly payments
        term_months = term_years * 12  # 120 months

        df = mortgage_cash_flows(
            principal, annual_rate, term_months, payment_interval_months
        )

        assert all(
            df["Interest"] == 0
        ), "With 0% interest, all interest payments should be zero."
        total_principal_paid = df["Principal"].sum()
        assert round(total_principal_paid, 2) == round(
            principal, 2
        ), "Total principal payments should equal the original principal."

    @pytest.mark.parametrize(
        "principal, annual_rate, term_months, payment_interval_months, error_msg",
        [
            (0, 0.05, 12, 1, "Principal must be greater than zero."),
            (100000, 0.05, 0, 1, "Loan term must be greater than zero months."),
            (
                100000,
                0.05,
                6,
                12,
                "Total payments must be greater than zero. "
                "Ensure term_months is greater than or equal to payment_interval_months.",
            ),
            (
                100000,
                0.05,
                12,
                0,
                "Payment interval (months) must be greater than zero.",
            ),
            (
                100000,
                0.05,
                12,
                -1,
                "Payment interval (months) must be greater than zero.",
            ),
        ],
    )
    def test_mortgage_cash_flows_value_errors(
        self, principal, annual_rate, term_months, payment_interval_months, error_msg
    ):
        with pytest.raises(ValueError, match=re.escape(error_msg)):
            mortgage_cash_flows(
                principal, annual_rate, term_months, payment_interval_months
            )


class TestCalculatePayment:
    def test_calculate_payment_zero_interval(self):
        with pytest.raises(
            ValueError, match=r"Payment interval \(months\) must be greater than zero."
        ):
            calculate_payment(100000, 0.05, 360, 0)


# if __name__ == "__main__":
#     test = TestMortgageCashFlows()
#     test.test_mortgage_cash_flows_basic()
#     test.test_mortgage_cash_flows_zero_interest()
