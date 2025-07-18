import numpy as np
import pandas as pd
import pytest
from pyfian.time_value.means import geometric_mean, arithmetic_mean, harmonic_mean


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

class TestHarmonicMean:
    def test_harmonic_mean_basic(self):
        data = [0.05, 0.10, 0.02]
        growth_factors = np.array(data) + 1
        expected = len(growth_factors) / np.sum(1 / growth_factors) - 1
        result = harmonic_mean(data)
        assert pytest.approx(result, rel=1e-9) == expected


    def test_harmonic_mean_with_nan(self):
        df = pd.DataFrame({"Fund A": [0.05, 0.02, np.nan], "Fund B": [0.01, 0.03, 0.04]})
        growth_factors = df + 1
        n = growth_factors.count()
        denom = (1 / growth_factors).sum()
        expected = n / denom - 1
        result = harmonic_mean(df)
        pd.testing.assert_series_equal(result, expected)


    def test_harmonic_mean_invalid_input(self):
        invalid_data = [0.05, -1.0, 0.02]
        with pytest.raises(ValueError):
            harmonic_mean(invalid_data)


    def test_harmonic_mean_zero_growth_factor(self):
        invalid_data = [-1.0, 0.0, 0.02]
        with pytest.raises(ValueError):
            harmonic_mean(invalid_data)
