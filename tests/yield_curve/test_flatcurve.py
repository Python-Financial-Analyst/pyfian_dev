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
        # Default yield_calculation_convention is "Annual"
        eff = (1 + 0.05 / 2) ** 2 - 1
        assert self.curve(1) == pytest.approx(eff)

    def test_date_rate_default(self):
        # Default yield_calculation_convention is "Annual"
        eff = (1 + 0.05 / 2) ** 2 - 1
        assert self.curve.date_rate("2022-01-01") == pytest.approx(eff)

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
