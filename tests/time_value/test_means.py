import numpy as np
import pandas as pd
import pytest

from pyfian.time_value.means import (
    arithmetic_mean,
    geometric_mean,
    harmonic_mean,
    weighted_geometric_mean,
    weighted_harmonic_mean,
)


class TestGeometricMean:
    def test_geometric_mean_numpy_1d(self):
        data = np.array([0.05, 0.1, -0.02])
        result = geometric_mean(data)
        expected = np.exp(np.nanmean(np.log(1 + data))) - 1
        assert np.isclose(result, expected)

    def test_geometric_mean_pandas_series(self):
        series = pd.Series([0.03, 0.04, np.nan, 0.02])
        result = geometric_mean(series)
        expected = np.exp(np.nanmean(np.log(1 + series))) - 1
        assert np.isclose(result, expected)

    def test_geometric_mean_pandas_dataframe_axis0(self):
        df = pd.DataFrame({"A": [0.01, 0.02, 0.03], "B": [0.04, -0.01, 0.00]})
        result = geometric_mean(df)
        expected = pd.Series(
            {
                "A": np.exp(np.mean(np.log(1 + df["A"]))) - 1,
                "B": np.exp(np.mean(np.log(1 + df["B"]))) - 1,
            }
        )
        pd.testing.assert_series_equal(result, expected)

    def test_geometric_mean_with_nan(self):
        data = np.array([0.02, np.nan, 0.03])
        result = geometric_mean(data)
        expected = np.exp(np.nanmean(np.log(1 + data))) - 1
        assert np.isclose(result, expected)

    def test_geometric_mean_invalid_input(self):
        with pytest.raises(ValueError):
            geometric_mean([0.05, -1.0, 0.02])

    def test_geometric_mean_invalid_input_df(self):
        with pytest.raises(ValueError):
            geometric_mean(pd.DataFrame([0.05, -1.0, 0.02]))


class TestArithmeticMean:
    def test_arithmetic_mean_basic(self):
        data = [0.05, 0.10, -0.02]
        expected = np.mean(data)
        result = arithmetic_mean(data)
        assert pytest.approx(result, rel=1e-9) == expected

    def test_arithmetic_mean_with_nan(self):
        data = [0.05, np.nan, -0.02]
        expected = np.nanmean(data)
        result = arithmetic_mean(data)
        assert pytest.approx(result, rel=1e-9) == expected

    def test_arithmetic_mean_with_nan_in_series(self):
        data = pd.Series([0.05, np.nan, 0.10])
        expected = np.nanmean(data)
        result = arithmetic_mean(data)
        assert pytest.approx(result, rel=1e-9) == expected

    def test_arithmetic_mean_dataframe(self):
        df = pd.DataFrame({"A": [0.05, 0.02, np.nan], "B": [0.01, -0.03, 0.04]})
        expected = df.mean(skipna=True)
        result = arithmetic_mean(df)
        pd.testing.assert_series_equal(result, expected)


class TestWeightedGeometricMean:
    def test_weighted_geometric_mean_basic(self):
        returns = np.array([0.05, 0.10, 0.02])
        weights = np.array([1, 2, 1])
        expected = np.exp(np.sum((weights / weights.sum()) * np.log(1 + returns))) - 1
        result = weighted_geometric_mean(returns, weights)
        assert np.isclose(result, expected)

    def test_weighted_geometric_mean_with_nan(self):
        returns = np.array([0.05, np.nan, 0.02])
        weights = np.array([1, 2, 1])
        mask = ~np.isnan(returns) & ~np.isnan(weights)
        expected = (
            np.exp(
                np.sum(
                    (weights[mask] / weights[mask].sum()) * np.log(1 + returns[mask])
                )
            )
            - 1
        )
        result = weighted_geometric_mean(returns, weights)
        assert np.isclose(result, expected)

    def test_weighted_geometric_mean_invalid(self):
        returns = np.array([0.05, -1.0, 0.02])
        weights = np.array([1, 2, 1])
        with pytest.raises(ValueError):
            weighted_geometric_mean(returns, weights)


class TestWeightedHarmonicMean:
    def test_weighted_harmonic_mean_basic(self):
        values = np.array([15, 20, 25])
        weights = np.array([100, 200, 700])
        expected = weights.sum() / np.sum(weights / values)
        result = weighted_harmonic_mean(values, weights)
        assert np.isclose(result, expected)

    def test_weighted_harmonic_mean_with_nan(self):
        values = np.array([15, np.nan, 25])
        weights = np.array([100, 200, 700])
        mask = ~np.isnan(values)
        expected = weights[mask].sum() / np.sum(weights[mask] / values[mask])
        result = weighted_harmonic_mean(values, weights)
        assert np.isclose(result, expected)

    def test_weighted_harmonic_mean_with_zero(self):
        values = np.array([15, 0, 25])
        weights = np.array([100, 200, 700])
        with pytest.raises(ValueError):
            weighted_harmonic_mean(values, weights)


class TestHarmonicMean:
    def test_harmonic_mean_basic(self):
        data = np.array([15, 20, 25])
        expected = len(data) / np.sum(1 / data)
        result = harmonic_mean(data)
        assert np.isclose(result, expected)

    def test_harmonic_mean_with_nan(self):
        data = np.array([15, np.nan, 25])
        mask = ~np.isnan(data)
        expected = mask.sum() / np.sum(1 / data[mask])
        result = harmonic_mean(data)
        assert np.isclose(result, expected)

    def test_harmonic_mean_invalid(self):
        data = np.array([15, 0, 25])
        with pytest.raises(ValueError):
            harmonic_mean(data)

    def test_harmonic_mean_dataframe(self):
        df = pd.DataFrame({"A": [10, 20, 30], "B": [5, 10, 15]})
        expected = pd.Series(
            {"A": 3 / np.sum(1 / df["A"]), "B": 3 / np.sum(1 / df["B"])}
        )
        result = harmonic_mean(df)
        pd.testing.assert_series_equal(result, expected)
