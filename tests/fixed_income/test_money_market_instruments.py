from pyfian.fixed_income.money_market_instruments import (
    TreasuryBill,
    CertificateOfDeposit,
    CommercialPaper,
    BankersAcceptance,
)
import pandas as pd


class TestTreasuryBill:
    def test_defaults(self):
        tbill = TreasuryBill("2025-01-01", "2025-07-01", notional=1000)
        assert tbill.cpn == 0.0
        assert tbill.cpn_freq == 1
        assert tbill.notional == 1000
        assert tbill.day_count_convention.name == "actual/360"
        assert tbill.maturity == pd.to_datetime("2025-07-01")

    def test_override_day_count_convention(self):
        tbill = TreasuryBill(
            "2025-01-01", "2025-07-01", notional=1000, day_count_convention="actual/365"
        )
        assert tbill.day_count_convention.name == "actual/365"


class TestCertificateOfDeposit:
    def test_defaults(self):
        cd = CertificateOfDeposit("2025-01-01", "2025-07-01", cpn=2.5, notional=5000)
        assert cd.cpn == 2.5
        assert cd.cpn_freq == 1
        assert cd.notional == 5000
        assert cd.day_count_convention.name == "actual/360"
        assert cd.maturity == pd.to_datetime("2025-07-01")

    def test_override_day_count_convention(self):
        cd = CertificateOfDeposit(
            "2025-01-01",
            "2025-07-01",
            cpn=2.5,
            notional=5000,
            day_count_convention="actual/365",
        )
        assert cd.day_count_convention.name == "actual/365"

        cd = CertificateOfDeposit(
            "2025-01-01",
            pd.Timestamp("2025-01-01") + pd.offsets.DateOffset(days=90),
            cpn=0.12 / 100,
            notional=20000000,
            day_count_convention="actual/365",
            #   settlement_date=pd.Timestamp('2025-01-01'),
            #   bond_price=20000000,
        )
        cd.set_bond_price(
            bond_price=20000000, settlement_date=pd.Timestamp("2025-01-01")
        )
        cd.get_yield_to_maturity()


class TestCommercialPaper:
    def test_defaults(self):
        cp = CommercialPaper("2025-01-01", "2025-04-01", notional=2000)
        assert cp.cpn == 0.0
        assert cp.cpn_freq == 1
        assert cp.notional == 2000
        assert cp.day_count_convention.name == "actual/360"
        assert cp.maturity == pd.to_datetime("2025-04-01")

    def test_override_day_count_convention(self):
        cp = CommercialPaper(
            "2025-01-01", "2025-04-01", notional=2000, day_count_convention="actual/365"
        )
        assert cp.day_count_convention.name == "actual/365"


class TestBankersAcceptance:
    def test_defaults(self):
        ba = BankersAcceptance("2025-01-01", "2025-03-01", notional=1500)
        assert ba.cpn == 0.0
        assert ba.cpn_freq == 1
        assert ba.notional == 1500
        assert ba.day_count_convention.name == "actual/360"
        assert ba.maturity == pd.to_datetime("2025-03-01")

    def test_override_day_count_convention(self):
        ba = BankersAcceptance(
            "2025-01-01", "2025-03-01", notional=1500, day_count_convention="actual/365"
        )
        assert ba.day_count_convention.name == "actual/365"
