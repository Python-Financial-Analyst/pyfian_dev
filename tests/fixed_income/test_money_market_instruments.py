import warnings
import matplotlib
from pyfian.fixed_income.money_market_instruments import (
    TreasuryBill,
    CertificateOfDeposit,
    CommercialPaper,
    BankersAcceptance,
)
import pandas as pd

from pyfian.yield_curves.flat_curve import FlatCurveAER


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

    def test_inherited_methods(self):
        tbill = TreasuryBill("2025-01-01", "2025-07-01", notional=1000)
        # set_bond_price and set_yield_to_maturity
        tbill.set_bond_price(950, settlement_date="2025-01-01")
        tbill.set_yield_to_maturity(0.05, settlement_date="2025-01-01")
        # get_settlement_date, get_yield_to_maturity, get_bond_price
        assert tbill.get_settlement_date() is not None
        assert tbill.get_yield_to_maturity() is not None
        assert tbill.get_bond_price() is not None
        # to_dataframe
        df = tbill.to_dataframe()
        assert df is not None
        # cash_flows
        flows = tbill.cash_flows()
        assert isinstance(flows, list)
        # price_from_yield
        price = tbill.price_from_yield(0.05)
        assert isinstance(price, float)
        # clean_price and dirty_price
        clean = tbill.clean_price(950)
        dirty = tbill.dirty_price(950)
        assert isinstance(clean, float)
        assert isinstance(dirty, float)
        # filter_payment_flow
        filtered = tbill.filter_payment_flow(settlement_date="2025-01-01")
        assert isinstance(filtered, dict)
        # calculate_time_to_payments
        ttp = tbill.calculate_time_to_payments(settlement_date="2025-01-01")
        assert isinstance(ttp, dict)
        # set_settlement_date
        sdt = tbill.set_settlement_date("2025-01-01")
        assert sdt is not None
        # plot_cash_flows (should not raise)

        # Change matplotlib backend not to graph and ignore warnings context
        matplotlib.use("Agg")
        # ignore warning context
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tbill.plot_cash_flows()

        # dv01, effective_convexity
        assert isinstance(tbill.dv01(), float)
        assert isinstance(tbill.effective_convexity(), float)
        # g_spread, i_spread, z_spread (pass dummy None for curve)
        assert isinstance(
            tbill.g_spread(benchmark_ytm=0.02, yield_calculation_convention="Annual"),
            float,
        )
        assert isinstance(
            tbill.i_spread(
                benchmark_curve=FlatCurveAER(
                    0.02, curve_date=pd.Timestamp("2025-01-01")
                ),
                yield_calculation_convention="Annual",
            ),
            float,
        )
        assert isinstance(
            tbill.z_spread(
                benchmark_curve=FlatCurveAER(
                    0.02, curve_date=pd.Timestamp("2025-01-01")
                ),
                yield_calculation_convention="Annual",
            ),
            float,
        )


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

    def test_inherited_methods(self):
        cd = CertificateOfDeposit("2025-01-01", "2025-07-01", cpn=2.5, notional=5000)
        cd.set_bond_price(4900, settlement_date="2025-01-01")
        cd.set_yield_to_maturity(0.03, settlement_date="2025-01-01")
        assert cd.get_settlement_date() is not None
        assert cd.get_yield_to_maturity() is not None
        assert cd.get_bond_price() is not None
        df = cd.to_dataframe()
        assert df is not None
        flows = cd.cash_flows()
        assert isinstance(flows, list)
        price = cd.price_from_yield(0.03)
        assert isinstance(price, float)
        clean = cd.clean_price(4900)
        dirty = cd.dirty_price(4900)
        assert isinstance(clean, float)
        assert isinstance(dirty, float)
        filtered = cd.filter_payment_flow(settlement_date="2025-01-01")
        assert isinstance(filtered, dict)
        ttp = cd.calculate_time_to_payments(settlement_date="2025-01-01")
        assert isinstance(ttp, dict)
        sdt = cd.set_settlement_date("2025-01-01")
        assert sdt is not None

        # Change matplotlib backend not to graph and ignore warnings context
        matplotlib.use("Agg")
        # ignore warning context
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cd.plot_cash_flows()

        assert isinstance(cd.dv01(), float)
        assert isinstance(cd.effective_convexity(), float)
        assert isinstance(cd.g_spread(benchmark_ytm=0.02), float)
        assert isinstance(
            cd.i_spread(
                benchmark_curve=FlatCurveAER(
                    0.02, curve_date=pd.Timestamp("2025-01-01")
                ),
                yield_calculation_convention="Annual",
            ),
            float,
        )
        assert isinstance(
            cd.z_spread(
                benchmark_curve=FlatCurveAER(
                    0.02, curve_date=pd.Timestamp("2025-01-01")
                ),
                yield_calculation_convention="Annual",
            ),
            float,
        )


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

    def test_inherited_methods(self):
        cp = CommercialPaper("2025-01-01", "2025-04-01", notional=2000)
        cp.set_bond_price(1950, settlement_date="2025-01-01")
        cp.set_yield_to_maturity(0.04, settlement_date="2025-01-01")
        assert cp.get_settlement_date() is not None
        assert cp.get_yield_to_maturity() is not None
        assert cp.get_bond_price() is not None
        df = cp.to_dataframe()
        assert df is not None
        flows = cp.cash_flows()
        assert isinstance(flows, list)
        price = cp.price_from_yield(0.04)
        assert isinstance(price, float)
        clean = cp.clean_price(1950)
        dirty = cp.dirty_price(1950)
        assert isinstance(clean, float)
        assert isinstance(dirty, float)
        filtered = cp.filter_payment_flow(settlement_date="2025-01-01")
        assert isinstance(filtered, dict)
        ttp = cp.calculate_time_to_payments(settlement_date="2025-01-01")
        assert isinstance(ttp, dict)
        sdt = cp.set_settlement_date("2025-01-01")
        assert sdt is not None

        # Change matplotlib backend not to graph and ignore warnings context
        matplotlib.use("Agg")
        # ignore warning context
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cp.plot_cash_flows()

        assert isinstance(cp.dv01(), float)
        assert isinstance(cp.effective_convexity(), float)
        assert isinstance(cp.g_spread(benchmark_ytm=0.02), float)
        assert isinstance(
            cp.i_spread(
                benchmark_curve=FlatCurveAER(
                    0.02, curve_date=pd.Timestamp("2025-01-01")
                ),
                yield_calculation_convention="Annual",
            ),
            float,
        )
        assert isinstance(
            cp.z_spread(
                benchmark_curve=FlatCurveAER(
                    0.02, curve_date=pd.Timestamp("2025-01-01")
                ),
                yield_calculation_convention="Annual",
            ),
            float,
        )


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

    def test_inherited_methods(self):
        ba = BankersAcceptance("2025-01-01", "2025-03-01", notional=1500)
        ba.set_bond_price(1450, settlement_date="2025-01-01")
        ba.set_yield_to_maturity(0.03, settlement_date="2025-01-01")
        assert ba.get_settlement_date() is not None
        assert ba.get_yield_to_maturity() is not None
        assert ba.get_bond_price() is not None
        df = ba.to_dataframe()
        assert df is not None
        flows = ba.cash_flows()
        assert isinstance(flows, list)
        price = ba.price_from_yield(0.03)
        assert isinstance(price, float)
        clean = ba.clean_price(1450)
        dirty = ba.dirty_price(1450)
        assert isinstance(clean, float)
        assert isinstance(dirty, float)
        filtered = ba.filter_payment_flow(settlement_date="2025-01-01")
        assert isinstance(filtered, dict)
        ttp = ba.calculate_time_to_payments(settlement_date="2025-01-01")
        assert isinstance(ttp, dict)
        sdt = ba.set_settlement_date("2025-01-01")
        assert sdt is not None

        # Change matplotlib backend not to graph and ignore warnings context
        matplotlib.use("Agg")
        # ignore warning context
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ba.plot_cash_flows()
        assert isinstance(ba.dv01(), float)
        assert isinstance(ba.effective_convexity(), float)
        assert isinstance(
            ba.g_spread(benchmark_ytm=0.02, yield_calculation_convention="Annual"),
            float,
        )
        assert isinstance(
            ba.i_spread(
                benchmark_curve=FlatCurveAER(
                    0.02, curve_date=pd.Timestamp("2025-01-01")
                ),
                yield_calculation_convention="Annual",
            ),
            float,
        )
        assert isinstance(
            ba.z_spread(
                benchmark_curve=FlatCurveAER(
                    0.02, curve_date=pd.Timestamp("2025-01-01")
                ),
                yield_calculation_convention="Annual",
            ),
            float,
        )
