"""
Unit tests for interest_income.py

Each function is tested in a separate class using pytest.
"""

import numpy as np
from pyfian.time_value import interest_income


class TestInterestIncomeContinuous:
    def test_basic(self):
        assert np.isclose(
            interest_income.interest_income_continuous(0.05, 1), 0.05127109637602412
        )

    def test_notional(self):
        assert np.isclose(
            interest_income.interest_income_continuous(0.05, 2, 1000),
            105.17091807564763,
        )


class TestInterestIncomeEffective:
    def test_basic(self):
        assert np.isclose(
            interest_income.interest_income_effective(0.05, 180), 0.024113688402427045
        )

    def test_notional(self):
        assert np.isclose(
            interest_income.interest_income_effective(0.05, 365, notional=100), 5.0
        )


class TestInterestIncomeNominalPeriods:
    def test_basic(self):
        assert np.isclose(
            interest_income.interest_income_nominal_periods(0.06, 12, 6), 0.03
        )

    def test_notional(self):
        assert np.isclose(
            interest_income.interest_income_nominal_periods(0.06, 4, 2, 1000), 30.0
        )


class TestInterestIncomeNominalDays:
    def test_basic(self):
        assert np.isclose(
            interest_income.interest_income_nominal_days(0.06, 30, 90),
            0.014794520547945205,
        )

    def test_notional(self):
        assert np.isclose(
            interest_income.interest_income_nominal_days(0.06, 30, 180, notional=1000),
            29.58904109589041,
        )


class TestInterestIncomeMoneyMarketDiscount:
    def test_basic(self):
        assert np.isclose(
            interest_income.interest_income_money_market_discount(0.06, 180), 0.03
        )

    def test_notional(self):
        assert np.isclose(
            interest_income.interest_income_money_market_discount(
                0.06, 90, notional=1000
            ),
            15.0,
        )


class TestInterestIncomeMoneyMarketAddonNotional:
    def test_basic(self):
        assert np.isclose(
            interest_income.interest_income_money_market_addon_notional(0.06, 180),
            0.02912621359223301,
        )

    def test_notional(self):
        assert np.isclose(
            interest_income.interest_income_money_market_addon_notional(
                0.06, 180, notional=1000
            ),
            29.12621359223301,
        )


class TestInterestIncomeMoneyMarketAddonInvestment:
    def test_basic(self):
        assert np.isclose(
            interest_income.interest_income_money_market_addon_investment(0.06, 180),
            0.03,
        )

    def test_notional(self):
        assert np.isclose(
            interest_income.interest_income_money_market_addon_investment(
                0.06, 180, notional=1000
            ),
            30.0,
        )


class TestInterestIncomeBEY:
    def test_basic(self):
        assert np.isclose(interest_income.interest_income_bey(0.06, 2), 0.06)

    def test_notional(self):
        assert np.isclose(
            interest_income.interest_income_bey(0.06, 2, notional=1000), 60.0
        )
