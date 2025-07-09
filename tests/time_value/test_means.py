import numpy as np
import pandas as pd
import pytest
from pyfian.time_value.means import geometric_mean


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
        df = pd.DataFrame({
            'A': [0.01, 0.02, 0.03],
            'B': [0.04, -0.01, 0.00]
        })
        result = geometric_mean(df)
        expected = pd.Series({
            'A': np.exp(np.mean(np.log(1 + df['A']))) - 1,
            'B': np.exp(np.mean(np.log(1 + df['B']))) - 1
        })
        pd.testing.assert_series_equal(result, expected)


    def test_geometric_mean_with_nan(self):
        data = np.array([0.02, np.nan, 0.03])
        result = geometric_mean(data)
        expected = np.exp(np.nanmean(np.log(1 + data))) - 1
        assert np.isclose(result, expected)


    def test_geometric_mean_invalid_input():
        with pytest.raises(ValueError):
            geometric_mean([0.05, -1.0, 0.02])  # 1 + return == 0
