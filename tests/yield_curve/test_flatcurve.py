import numpy as np
import pandas as pd
import pytest

from pyfian.yield_curves.flat_curve import FlatCurveAER, FlatCurveLog, FlatCurveBEY


class TestFlatCurveLog:
    def setup_method(self):
        self.curve = FlatCurveLog(0.05, "2020-01-01")

    def test_discount_t(self):
        assert self.curve.discount_t(1) == pytest.approx(np.exp(-0.05))

    def test_discount_date(self):
        # Calculate days from the start date to '2021-01-01'
        days = (pd.to_datetime("2021-01-01") - pd.to_datetime("2020-01-01")).days
        assert self.curve.discount_date("2021-01-01") == pytest.approx(
            np.exp(-0.05 * days / 365)
        )

    def test_call_default(self):
        assert self.curve(1) == 0.05

    def test_call_annual(self):
        assert self.curve(1, yield_calculation_convention="Annual") == pytest.approx(
            np.expm1(0.05)
        )

    def test_call_bey(self):
        eff = np.expm1(0.05)
        bey = 2 * ((1 + eff) ** 0.5 - 1)
        assert self.curve(1, yield_calculation_convention="BEY") == pytest.approx(bey)

    def test_call_continuous(self):
        assert self.curve(1, yield_calculation_convention="Continuous") == 0.05

    def test_call_invalid(self):
        with pytest.raises(
            ValueError, match="Unknown yield calculation convention: Unknown"
        ):
            self.curve(1, yield_calculation_convention="Unknown")

    def test_date_rate_default(self):
        assert self.curve.date_rate("2022-01-01") == 0.05

    def test_date_rate_annual(self):
        assert self.curve.date_rate(
            "2022-01-01", yield_calculation_convention="Annual"
        ) == pytest.approx(np.expm1(0.05))

    def test_date_rate_bey(self):
        eff = np.expm1(0.05)
        bey = 2 * ((1 + eff) ** 0.5 - 1)
        assert self.curve.date_rate(
            "2022-01-01", yield_calculation_convention="BEY"
        ) == pytest.approx(bey)

    def test_date_rate_continuous(self):
        assert (
            self.curve.date_rate(
                "2022-01-01", yield_calculation_convention="Continuous"
            )
            == 0.05
        )

    def test_date_rate_invalid(self):
        with pytest.raises(
            ValueError, match="Unknown yield calculation convention: Unknown"
        ):
            self.curve.date_rate("2022-01-01", yield_calculation_convention="Unknown")

    def test_repr(self):
        result = repr(self.curve)
        expected = "FlatCurveLog(log_rate=0.0500, curve_date=2020-01-01)"
        assert result == expected, f"__repr__ output mismatch: {result}"

    def test_as_dict(self):
        d = self.curve.as_dict()
        assert isinstance(d, dict)
        assert d["log_rate"] == 0.05
        assert pd.to_datetime(d["curve_date"]) == pd.to_datetime("2020-01-01")

    def test_from_dict(self):
        d = self.curve.as_dict()
        curve2 = FlatCurveLog.from_dict(d)
        assert isinstance(curve2, FlatCurveLog)
        assert curve2.log_rate == self.curve.log_rate
        assert curve2.curve_date == self.curve.curve_date

    def test_to_dataframe(self):
        df = self.curve.to_dataframe([0.5, 1, 2])
        assert isinstance(df, pd.DataFrame)
        assert list(df["Maturity"]) == [0.5, 1, 2]
        assert np.allclose(df["Rate"], [self.curve(0.5), self.curve(1), self.curve(2)])

    def test_compare_to(self):
        curve2 = FlatCurveLog(0.04, "2020-01-01")
        df = self.curve.compare_to(curve2)
        assert isinstance(df, pd.DataFrame)
        assert "Spread" in df.columns
        # Spread should be positive since self has higher rate
        assert all(df["Spread"] > 0)

    @pytest.mark.filterwarnings("ignore::UserWarning")
    def test_plot_curve(self):
        self.curve.plot_curve([0.5, 1, 2])

    def test_forward_t_start_t_end(self):
        # Forward rate between t=0.5 and t=1
        fwd = self.curve.forward_t_start_t_end(0.5, 1)
        # For log curve, should match discount_to_rate of D(0.5)/D(1) over dt=0.5
        d0 = self.curve.discount_t(0.5)
        d1 = self.curve.discount_t(1)
        expected = self.curve.discount_to_rate(d0 / d1, 0.5, spread=0)
        assert fwd == pytest.approx(expected)

    def test_forward_t_start_dt(self):
        # Forward rate from t=0.5 for dt=0.5
        fwd = self.curve.forward_t_start_dt(0.5, 0.5)
        d0 = self.curve.discount_t(0.5)
        d1 = self.curve.discount_t(1)
        expected = self.curve.discount_to_rate(d0 / d1, 0.5, spread=0)
        assert fwd == pytest.approx(expected)

    def test_forward_dt(self):
        # Forward rate from date '2020-07-01' for dt=0.5
        fwd = self.curve.forward_dt("2020-07-01", 0.5)
        t_start = self.curve.day_count.fraction(
            start=self.curve.curve_date, current=pd.to_datetime("2020-07-01")
        )
        d0 = self.curve.discount_t(t_start)
        d1 = self.curve.discount_t(t_start + 0.5)
        expected = self.curve.discount_to_rate(d0 / d1, 0.5, spread=0)
        assert fwd == pytest.approx(expected)

    def test_forward_dates(self):
        # Forward rate between two dates
        fwd = self.curve.forward_dates("2020-07-01", "2021-01-01")
        t_start = self.curve.day_count.fraction(
            start=self.curve.curve_date, current=pd.to_datetime("2020-07-01")
        )
        t_end = self.curve.day_count.fraction(
            start=self.curve.curve_date, current=pd.to_datetime("2021-01-01")
        )
        dt = t_end - t_start
        d0 = self.curve.discount_t(t_start)
        d1 = self.curve.discount_t(t_end)
        expected = self.curve.discount_to_rate(d0 / d1, dt, spread=0)
        assert fwd == pytest.approx(expected)


class TestFlatCurveAER:
    def setup_method(self):
        self.curve = FlatCurveAER(0.05, "2020-01-01")

    def test_discount_t(self):
        assert self.curve.discount_t(1) == pytest.approx(1 / (1 + 0.05))

    def test_discount_date(self):
        # Calculate days from the start date to '2021-01-01'
        days = (pd.to_datetime("2021-01-01") - pd.to_datetime("2020-01-01")).days
        assert self.curve.discount_date("2021-01-01") == pytest.approx(
            1 / (1 + 0.05) ** (days / 365)
        )

    def test_call_default(self):
        assert self.curve(1) == 0.05

    def test_call_bey(self):
        bey = 2 * ((1 + 0.05) ** 0.5 - 1)
        assert self.curve(1, yield_calculation_convention="BEY") == pytest.approx(bey)

    def test_call_continuous(self):
        cont = np.log(1 + 0.05)
        assert self.curve(
            1, yield_calculation_convention="Continuous"
        ) == pytest.approx(cont)

    def test_call_invalid(self):
        with pytest.raises(
            ValueError, match="Unknown yield calculation convention: Unknown"
        ):
            self.curve(1, yield_calculation_convention="Unknown")

    def test_date_rate_default(self):
        assert self.curve.date_rate("2022-01-01") == 0.05

    def test_date_rate_bey(self):
        bey = 2 * ((1 + 0.05) ** 0.5 - 1)
        assert self.curve.date_rate(
            "2022-01-01", yield_calculation_convention="BEY"
        ) == pytest.approx(bey)

    def test_date_rate_continuous(self):
        cont = np.log(1 + 0.05)
        assert self.curve.date_rate(
            "2022-01-01", yield_calculation_convention="Continuous"
        ) == pytest.approx(cont)

    def test_date_rate_invalid(self):
        with pytest.raises(
            ValueError, match="Unknown yield calculation convention: Unknown"
        ):
            self.curve.date_rate("2022-01-01", yield_calculation_convention="Unknown")

    def test_repr(self):
        result = repr(self.curve)
        expected = "FlatCurveAER(aer=0.0500, curve_date=2020-01-01)"
        assert result == expected, f"__repr__ output mismatch: {result}"

    def test_as_dict(self):
        d = self.curve.as_dict()
        assert isinstance(d, dict)
        assert d["aer"] == 0.05
        assert pd.to_datetime(d["curve_date"]) == pd.to_datetime("2020-01-01")

    def test_from_dict(self):
        d = self.curve.as_dict()
        curve2 = FlatCurveAER.from_dict(d)
        assert isinstance(curve2, FlatCurveAER)
        assert curve2.aer == self.curve.aer
        assert curve2.curve_date == self.curve.curve_date

    def test_to_dataframe(self):
        df = self.curve.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert list(df["Maturity"]) == [0.25, 0.5, 1, 2, 5, 10]
        assert np.allclose(
            df["Rate"],
            [
                self.curve(0.25),
                self.curve(0.5),
                self.curve(1),
                self.curve(2),
                self.curve(5),
                self.curve(10),
            ],
        )

    def test_compare_to(self):
        curve2 = FlatCurveAER(0.04, "2020-01-01")
        df = self.curve.compare_to(curve2, maturities=[0.5, 1])
        assert isinstance(df, pd.DataFrame)
        assert "Spread" in df.columns
        assert all(df["Spread"] > 0)

    @pytest.mark.filterwarnings("ignore::UserWarning")
    def test_plot_curve(self):
        self.curve.plot_curve([0.5, 1, 2])

    def test_forward_t_start_t_end(self):
        fwd = self.curve.forward_t_start_t_end(0.5, 1)
        d0 = self.curve.discount_t(0.5)
        d1 = self.curve.discount_t(1)
        expected = self.curve.discount_to_rate(d0 / d1, 0.5, spread=0)
        assert fwd == pytest.approx(expected)

    def test_forward_t_start_dt(self):
        fwd = self.curve.forward_t_start_dt(0.5, 0.5)
        d0 = self.curve.discount_t(0.5)
        d1 = self.curve.discount_t(1)
        expected = self.curve.discount_to_rate(d0 / d1, 0.5, spread=0)
        assert fwd == pytest.approx(expected)

    def test_forward_dt(self):
        fwd = self.curve.forward_dt("2020-07-01", 0.5)
        t_start = self.curve.day_count.fraction(
            start=self.curve.curve_date, current=pd.to_datetime("2020-07-01")
        )
        d0 = self.curve.discount_t(t_start)
        d1 = self.curve.discount_t(t_start + 0.5)
        expected = self.curve.discount_to_rate(d0 / d1, 0.5, spread=0)
        assert fwd == pytest.approx(expected)

    def test_forward_dates(self):
        fwd = self.curve.forward_dates("2020-07-01", "2021-01-01")
        t_start = self.curve.day_count.fraction(
            start=self.curve.curve_date, current=pd.to_datetime("2020-07-01")
        )
        t_end = self.curve.day_count.fraction(
            start=self.curve.curve_date, current=pd.to_datetime("2021-01-01")
        )
        dt = t_end - t_start
        d0 = self.curve.discount_t(t_start)
        d1 = self.curve.discount_t(t_end)
        expected = self.curve.discount_to_rate(d0 / d1, dt, spread=0)
        assert fwd == pytest.approx(expected)


class TestFlatCurveBEY:
    def setup_method(self):
        self.curve = FlatCurveBEY(0.05, "2020-01-01")

    def test_discount_t(self):
        assert self.curve.discount_t(1) == pytest.approx(1 / (1 + 0.05 / 2) ** (1 * 2))

    def test_discount_date(self):
        # Calculate days from the start date to '2021-01-01'
        days = (pd.to_datetime("2021-01-01") - pd.to_datetime("2020-01-01")).days
        t = days / 365
        assert self.curve.discount_date("2021-01-01") == pytest.approx(
            1 / (1 + 0.05 / 2) ** (t * 2)
        )

    def test_call_default(self):
        # Default yield_calculation_convention is "BEY"
        eff = (1 + 0.05 / 2) ** 2 - 1
        assert self.curve(1, yield_calculation_convention="Annual") == pytest.approx(
            eff
        )

    def test_date_rate_default(self):
        # Default yield_calculation_convention is "BEY"
        eff = (1 + 0.05 / 2) ** 2 - 1
        assert self.curve.date_rate(
            "2022-01-01", yield_calculation_convention="Annual"
        ) == pytest.approx(eff)

    def test_call_annual(self):
        eff = (1 + 0.05 / 2) ** 2 - 1
        assert self.curve(1, yield_calculation_convention="Annual") == pytest.approx(
            eff
        )

    def test_call_bey(self):
        assert self.curve(1, yield_calculation_convention="BEY") == 0.05

    def test_call_continuous(self):
        eff = (1 + 0.05 / 2) ** 2 - 1
        cont = np.log(1 + eff)
        assert self.curve(
            1, yield_calculation_convention="Continuous"
        ) == pytest.approx(cont)

    def test_call_invalid(self):
        with pytest.raises(
            ValueError, match="Unknown yield calculation convention: Unknown"
        ):
            self.curve(1, yield_calculation_convention="Unknown")

    def test_date_rate_annual(self):
        eff = (1 + 0.05 / 2) ** 2 - 1
        assert self.curve.date_rate(
            "2022-01-01", yield_calculation_convention="Annual"
        ) == pytest.approx(eff)

    def test_date_rate_bey(self):
        assert (
            self.curve.date_rate("2022-01-01", yield_calculation_convention="BEY")
            == 0.05
        )

    def test_date_rate_continuous(self):
        eff = (1 + 0.05 / 2) ** 2 - 1
        cont = np.log(1 + eff)
        assert self.curve.date_rate(
            "2022-01-01", yield_calculation_convention="Continuous"
        ) == pytest.approx(cont)

    def test_date_rate_invalid(self):
        with pytest.raises(
            ValueError, match="Unknown yield calculation convention: Unknown"
        ):
            self.curve.date_rate("2022-01-01", yield_calculation_convention="Unknown")

    def test_repr(self):
        result = repr(self.curve)
        expected = "FlatCurveBEY(bey=0.0500, curve_date=2020-01-01)"
        assert result == expected, f"__repr__ output mismatch: {result}"

    def test_as_dict(self):
        d = self.curve.as_dict()
        assert isinstance(d, dict)
        assert d["bey"] == 0.05
        assert pd.to_datetime(d["curve_date"]) == pd.to_datetime("2020-01-01")

    def test_from_dict(self):
        d = self.curve.as_dict()
        curve2 = FlatCurveBEY.from_dict(d)
        assert isinstance(curve2, FlatCurveBEY)
        assert curve2.bey == self.curve.bey
        assert curve2.curve_date == self.curve.curve_date

    def test_to_dataframe(self):
        df = self.curve.to_dataframe([0.5, 1, 2])
        assert isinstance(df, pd.DataFrame)
        assert list(df["Maturity"]) == [0.5, 1, 2]
        assert np.allclose(df["Rate"], [self.curve(0.5), self.curve(1), self.curve(2)])

    def test_compare_to(self):
        curve2 = FlatCurveBEY(0.04, "2020-01-01")
        df = self.curve.compare_to(curve2, maturities=[0.5, 1])
        assert isinstance(df, pd.DataFrame)
        assert "Spread" in df.columns
        assert all(df["Spread"] > 0)

    @pytest.mark.filterwarnings("ignore::UserWarning")
    def test_plot_curve(self):
        self.curve.plot_curve([0.5, 1, 2])

    def test_forward_t_start_t_end(self):
        fwd = self.curve.forward_t_start_t_end(0.5, 1)
        d0 = self.curve.discount_t(0.5)
        d1 = self.curve.discount_t(1)
        expected = self.curve.discount_to_rate(d0 / d1, 0.5, spread=0)
        assert fwd == pytest.approx(expected)

    def test_forward_t_start_dt(self):
        fwd = self.curve.forward_t_start_dt(0.5, 0.5)
        d0 = self.curve.discount_t(0.5)
        d1 = self.curve.discount_t(1)
        expected = self.curve.discount_to_rate(d0 / d1, 0.5, spread=0)
        assert fwd == pytest.approx(expected)

    def test_forward_dt(self):
        fwd = self.curve.forward_dt("2020-07-01", 0.5)
        t_start = self.curve.day_count.fraction(
            start=self.curve.curve_date, current=pd.to_datetime("2020-07-01")
        )
        d0 = self.curve.discount_t(t_start)
        d1 = self.curve.discount_t(t_start + 0.5)
        expected = self.curve.discount_to_rate(d0 / d1, 0.5, spread=0)
        assert fwd == pytest.approx(expected)

    def test_forward_dates(self):
        fwd = self.curve.forward_dates("2020-07-01", "2021-01-01")
        t_start = self.curve.day_count.fraction(
            start=self.curve.curve_date, current=pd.to_datetime("2020-07-01")
        )
        t_end = self.curve.day_count.fraction(
            start=self.curve.curve_date, current=pd.to_datetime("2021-01-01")
        )
        dt = t_end - t_start
        d0 = self.curve.discount_t(t_start)
        d1 = self.curve.discount_t(t_end)
        expected = self.curve.discount_to_rate(d0 / d1, dt, spread=0)
        assert fwd == pytest.approx(expected)
