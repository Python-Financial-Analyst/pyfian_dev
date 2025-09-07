import warnings
import matplotlib
import pytest
from pyfian.fixed_income.money_market_instruments import (
    MoneyMarketInstrument,
    TreasuryBill,
    CertificateOfDeposit,
    CommercialPaper,
    BankersAcceptance,
)
import pandas as pd

from pyfian.yield_curves.flat_curve import FlatCurveAER


class TestMoneyMarketInstrument:
    def test_invalid_inputs(self):
        # Negative notional
        with pytest.raises(
            ValueError, match=r"Notional \(face value\) cannot be negative"
        ):
            MoneyMarketInstrument("2025-01-01", "2025-07-01", notional=-1000)
        # Negative coupon
        with pytest.raises(ValueError, match="Coupon rate cannot be negative"):
            MoneyMarketInstrument(
                "2025-01-01",
                "2025-07-01",
                notional=1000,
                day_count_convention="actual/360",
                yield_calculation_convention="Discount",
                cpn=-1,
                cpn_freq=1,
            )
        # Negative coupon frequency
        with pytest.raises(
            ValueError, match="Coupon frequency must be greater or equal to zero"
        ):
            MoneyMarketInstrument(
                "2025-01-01",
                "2025-07-01",
                notional=1000,
                day_count_convention="actual/360",
                yield_calculation_convention="Discount",
                cpn=0,
                cpn_freq=-1,
            )
        # Maturity before issue date
        with pytest.raises(
            ValueError, match="Maturity date cannot be before issue date"
        ):
            MoneyMarketInstrument("2025-07-01", "2025-01-01", notional=1000)
        # Invalid day count convention
        with pytest.raises(ValueError, match="Unknown day count convention"):
            MoneyMarketInstrument(
                "2025-01-01",
                "2025-07-01",
                notional=1000,
                day_count_convention="invalid/000",
            )
        # Invalid yield calculation convention
        with pytest.raises(
            ValueError, match="Unsupported yield calculation convention"
        ):
            MoneyMarketInstrument(
                "2025-01-01",
                "2025-07-01",
                notional=1000,
                yield_calculation_convention="invalid",
            )
        # Invalid cpn_freq
        with pytest.raises(
            ValueError,
            match="Coupon frequency must be greater than zero for positive coupons",
        ):
            MoneyMarketInstrument(
                "2025-01-01", "2025-07-01", notional=1000, cpn=1, cpn_freq=0
            )
        # Invalid settlement_convention_t_plus
        with pytest.raises(
            ValueError, match=r"Settlement convention \(T\+\) cannot be negative"
        ):
            MoneyMarketInstrument(
                "2025-01-01",
                "2025-07-01",
                notional=1000,
                settlement_convention_t_plus=-1,
            )
        # Invalid settlement_date before issue date
        with pytest.raises(
            ValueError, match="Settlement date cannot be before issue date"
        ):
            MoneyMarketInstrument(
                "2025-01-01", "2025-07-01", notional=1000, settlement_date="2024-12-31"
            )
        # Invalid day_count_convention
        with pytest.raises(
            ValueError,
            match="day_count_convention must be either a string or a DayCountBase instance",
        ):
            MoneyMarketInstrument(
                "2025-01-01", "2025-07-01", notional=1000, day_count_convention=123
            )
        # Invalid record_date_t_minus
        with pytest.raises(ValueError, match=r"Record date \(T-\) cannot be negative"):
            MoneyMarketInstrument(
                "2025-01-01", "2025-07-01", notional=1000, record_date_t_minus=-2
            )
        # Invalid settlement_date after maturity
        with pytest.raises(
            ValueError, match="Settlement date cannot be after maturity date"
        ):
            MoneyMarketInstrument(
                "2025-01-01", "2025-07-01", notional=1000, settlement_date="2025-08-01"
            )
        # Invalid setting of yield_to_maturity before setting price
        with pytest.raises(
            ValueError,
            match="Settlement date must be set since there is no default settlement_date",
        ):
            mmi = MoneyMarketInstrument("2025-01-01", "2025-07-01", notional=1000)
            mmi.set_yield_to_maturity(0.05)
        # Invalid setting of price before setting settlement date
        with pytest.raises(
            ValueError,
            match="Settlement date must be set since there is no default settlement_date",
        ):
            mmi = MoneyMarketInstrument("2025-01-01", "2025-07-01", notional=1000)
            mmi.set_price(980)
        # Invalid following_coupons_day_count
        with pytest.raises(
            ValueError, match="Unsupported following coupons day count convention"
        ):
            MoneyMarketInstrument(
                "2025-01-01",
                "2025-07-01",
                notional=1000,
                following_coupons_day_count="actual/actual-ISDA",
            )

    # Create with settlement price and yield to maturity
    def test_defaults(self):
        mmi = MoneyMarketInstrument(
            "2025-01-01",
            "2025-07-01",
            notional=100,
            settlement_date="2025-01-01",
            price=98,
        )
        assert mmi.cpn == 0.0
        assert mmi.cpn_freq == 0
        assert mmi.notional == 100
        assert mmi.day_count_convention.name == "actual/365"
        assert mmi.maturity == pd.to_datetime("2025-07-01")

        mmi = MoneyMarketInstrument(
            "2025-01-01",
            "2025-07-01",
            notional=100,
            settlement_date="2025-01-01",
            yield_to_maturity=mmi.get_yield_to_maturity(),
        )
        assert mmi.cpn == 0.0
        assert mmi.cpn_freq == 0
        assert mmi.notional == 100
        assert mmi.day_count_convention.name == "actual/365"
        assert mmi.maturity == pd.to_datetime("2025-07-01")
        # assert mmi.get_price() is approximately 98 with pytest.approx
        assert mmi.get_price() == pytest.approx(98, rel=1e-8)

    # make test_default tests but raising errors for absent settlement_date when setting price or yield
    def test_settlement_date_required(self):
        with pytest.raises(
            ValueError, match="Settlement date must be set if price is set"
        ):
            MoneyMarketInstrument("2025-01-01", "2025-07-01", notional=100, price=98)
        with pytest.raises(
            ValueError, match="Settlement date must be set if yield to maturity is set"
        ):
            MoneyMarketInstrument(
                "2025-01-01", "2025-07-01", notional=100, yield_to_maturity=0.04
            )
        with pytest.raises(
            ValueError,
            match="Price calculated by yield to maturity does not match the current price",
        ):
            MoneyMarketInstrument(
                "2025-01-01",
                "2025-07-01",
                notional=100,
                yield_to_maturity=0.04,
                price=98,
                settlement_date="2025-01-01",
            )

    # use from_days to create an instrument
    def test_from_days(self):
        mmi = MoneyMarketInstrument.from_days(
            days=180,
            notional=100,
            settlement_date="2025-01-01",
            price=98,
            issue_dt="2025-01-01",
        )
        assert mmi.cpn == 0.0
        assert mmi.cpn_freq == 0
        assert mmi.notional == 100
        assert mmi.day_count_convention.name == "actual/365"
        assert mmi.maturity == pd.to_datetime("2025-06-30")

    # use from_days to create an instrument without setting issue date
    def test_from_days_no_issue(self):
        mmi = MoneyMarketInstrument.from_days(
            days=180,
            notional=100,
            settlement_date=pd.Timestamp.today().date(),
            price=98,
        )
        assert mmi.cpn == 0.0
        assert mmi.cpn_freq == 0
        assert mmi.notional == 100
        assert mmi.day_count_convention.name == "actual/365"
        assert mmi.maturity == pd.Timestamp(
            pd.Timestamp.today().date() + pd.Timedelta(days=180)
        )
        assert mmi.issue_dt == pd.Timestamp(pd.Timestamp.today().date())

    # test from_days with invalid issue date type
    def test_from_days_invalid_issue(self):
        with pytest.raises(
            TypeError,
            match="issue_dt must be either a string or a pd.Timestamp or datetime.",
        ):
            MoneyMarketInstrument.from_days(
                days=180,
                notional=100,
                settlement_date="2025-01-01",
                price=98,
                issue_dt=12345,
            )


class TestTreasuryBill:
    def test_invalid_inputs(self):
        # Negative notional
        with pytest.raises(
            ValueError, match=r"Notional \(face value\) cannot be negative"
        ):
            TreasuryBill("2025-01-01", "2025-07-01", notional=-1000)
        # Maturity before issue date
        with pytest.raises(
            ValueError, match="Maturity date cannot be before issue date"
        ):
            TreasuryBill("2025-07-01", "2025-01-01", notional=1000)
        # Invalid day count convention
        with pytest.raises(ValueError, match="Unknown day count convention"):
            TreasuryBill(
                "2025-01-01",
                "2025-07-01",
                notional=1000,
                day_count_convention="invalid/000",
            )
        # Invalid yield calculation convention
        with pytest.raises(
            ValueError, match="Unsupported yield calculation convention"
        ):
            TreasuryBill(
                "2025-01-01",
                "2025-07-01",
                notional=1000,
                yield_calculation_convention="invalid",
            )
        # Passing cpn or cpn_freq should raise ValueError
        with pytest.raises(
            ValueError,
            match="TreasuryBill does not allow setting coupon or coupon frequency",
        ):
            TreasuryBill("2025-01-01", "2025-07-01", notional=1000, cpn=1)
        with pytest.raises(
            ValueError,
            match="TreasuryBill does not allow setting coupon or coupon frequency",
        ):
            TreasuryBill("2025-01-01", "2025-07-01", notional=1000, cpn_freq=2)

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
        # set_price and set_yield_to_maturity
        tbill.set_price(950, settlement_date="2025-01-01")
        tbill.set_yield_to_maturity(0.05, settlement_date="2025-01-01")
        # get_settlement_date, get_yield_to_maturity, get_price
        assert tbill.get_settlement_date() is not None
        assert tbill.get_yield_to_maturity() is not None
        assert tbill.get_price() is not None
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
    def test_invalid_inputs(self):
        # Negative notional
        with pytest.raises(
            ValueError, match=r"Notional \(face value\) cannot be negative"
        ):
            CertificateOfDeposit("2025-01-01", "2025-07-01", cpn=2.5, notional=-5000)
        # Zero or negative coupon frequency with positive coupon
        with pytest.raises(
            ValueError,
            match="Coupon frequency must be greater than zero for positive coupons",
        ):
            CertificateOfDeposit(
                "2025-01-01", "2025-07-01", cpn=2.5, cpn_freq=0, notional=5000
            )
        # Maturity before issue date
        with pytest.raises(
            ValueError, match="Maturity date cannot be before issue date"
        ):
            CertificateOfDeposit("2025-07-01", "2025-01-01", cpn=2.5, notional=5000)
        # Invalid day count convention
        with pytest.raises(ValueError, match="Unknown day count convention"):
            CertificateOfDeposit(
                "2025-01-01",
                "2025-07-01",
                cpn=2.5,
                notional=5000,
                day_count_convention="invalid/000",
            )
        # Invalid yield calculation convention
        with pytest.raises(
            ValueError, match="Unsupported yield calculation convention"
        ):
            CertificateOfDeposit(
                "2025-01-01",
                "2025-07-01",
                cpn=2.5,
                notional=5000,
                yield_calculation_convention="invalid",
            )

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
            #   price=20000000,
        )
        cd.set_price(price=20000000, settlement_date=pd.Timestamp("2025-01-01"))
        cd.get_yield_to_maturity()

    def test_inherited_methods(self):
        cd = CertificateOfDeposit("2025-01-01", "2025-07-01", cpn=2.5, notional=5000)
        cd.set_price(4900, settlement_date="2025-01-01")
        cd.set_yield_to_maturity(0.03, settlement_date="2025-01-01")
        assert cd.get_settlement_date() is not None
        assert cd.get_yield_to_maturity() is not None
        assert cd.get_price() is not None
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
    def test_invalid_inputs(self):
        # Negative notional
        with pytest.raises(
            ValueError, match=r"Notional \(face value\) cannot be negative"
        ):
            CommercialPaper("2025-01-01", "2025-04-01", notional=-2000)
        # Maturity before issue date
        with pytest.raises(
            ValueError, match="Maturity date cannot be before issue date"
        ):
            CommercialPaper("2025-04-01", "2025-01-01", notional=2000)
        # Invalid day count convention
        with pytest.raises(ValueError, match="Unknown day count convention"):
            CommercialPaper(
                "2025-01-01",
                "2025-04-01",
                notional=2000,
                day_count_convention="invalid/000",
            )
        # Invalid yield calculation convention
        with pytest.raises(
            ValueError, match="Unsupported yield calculation convention"
        ):
            CommercialPaper(
                "2025-01-01",
                "2025-04-01",
                notional=2000,
                yield_calculation_convention="invalid",
            )
        # Passing cpn or cpn_freq should raise ValueError
        with pytest.raises(
            ValueError,
            match="CommercialPaper does not allow setting coupon or coupon frequency",
        ):
            CommercialPaper("2025-01-01", "2025-04-01", notional=2000, cpn=1)
        with pytest.raises(
            ValueError,
            match="CommercialPaper does not allow setting coupon or coupon frequency",
        ):
            CommercialPaper("2025-01-01", "2025-04-01", notional=2000, cpn_freq=2)

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
        cp.set_price(1950, settlement_date="2025-01-01")
        cp.set_yield_to_maturity(0.04, settlement_date="2025-01-01")
        assert cp.get_settlement_date() is not None
        assert cp.get_yield_to_maturity() is not None
        assert cp.get_price() is not None
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
    def test_invalid_inputs(self):
        # Negative notional
        with pytest.raises(
            ValueError, match=r"Notional \(face value\) cannot be negative"
        ):
            BankersAcceptance("2025-01-01", "2025-03-01", notional=-1500)
        # Maturity before issue date
        with pytest.raises(
            ValueError, match="Maturity date cannot be before issue date"
        ):
            BankersAcceptance("2025-03-01", "2025-01-01", notional=1500)
        # Invalid day count convention
        with pytest.raises(ValueError, match="Unknown day count convention"):
            BankersAcceptance(
                "2025-01-01",
                "2025-03-01",
                notional=1500,
                day_count_convention="invalid/000",
            )
        # Invalid yield calculation convention
        with pytest.raises(
            ValueError, match="Unsupported yield calculation convention"
        ):
            BankersAcceptance(
                "2025-01-01",
                "2025-03-01",
                notional=1500,
                yield_calculation_convention="invalid",
            )
        # Passing cpn or cpn_freq should raise ValueError
        with pytest.raises(
            ValueError,
            match="BankersAcceptance does not allow setting coupon or coupon frequency",
        ):
            BankersAcceptance("2025-01-01", "2025-03-01", notional=1500, cpn=1)
        with pytest.raises(
            ValueError,
            match="BankersAcceptance does not allow setting coupon or coupon frequency",
        ):
            BankersAcceptance("2025-01-01", "2025-03-01", notional=1500, cpn_freq=2)

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
        ba.set_price(1450, settlement_date="2025-01-01")
        ba.set_yield_to_maturity(0.03, settlement_date="2025-01-01")
        assert ba.get_settlement_date() is not None
        assert ba.get_yield_to_maturity() is not None
        assert ba.get_price() is not None
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
