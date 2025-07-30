import numpy as np
import pandas as pd
import pytest

from pyfian.yield_curves.flat_curve import FlatCurveAER, FlatCurveLog


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

    def test_call(self):
        assert self.curve(2) == 0.05

    def test_date_rate(self):
        assert self.curve.date_rate("2022-01-01") == 0.05

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

    def test_call(self):
        assert self.curve(2) == 0.05

    def test_date_rate(self):
        assert self.curve.date_rate("2022-01-01") == 0.05

    def test_repr(self):
        result = repr(self.curve)
        expected = "FlatCurveAER(aer=0.0500, curve_date=2020-01-01)"
        assert result == expected, f"__repr__ output mismatch: {result}"
