import pytest
import matplotlib

matplotlib.use("Agg")  # Use non-GUI backend for tests
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pyfian.visualization.mixins import YieldCurvePlotMixin


class DummyCurve(YieldCurvePlotMixin):
    def __init__(self):
        self.curve_date = pd.Timestamp("2025-01-01")

    def _get_t(self, t):
        return 0.05 + 0 * t

    def discount_t(self, t):
        return np.exp(-0.05 * t)


class TestYieldCurvePlotMixin:
    def test_plot_curve_rate(self):
        curve = DummyCurve()
        fig = plt.figure()
        curve.plot_curve(kind="rate", show=False)
        plt.close(fig)

    def test_plot_curve_discount(self):
        curve = DummyCurve()
        fig = plt.figure()
        curve.plot_curve(kind="discount", show=False)
        plt.close(fig)

    @pytest.mark.filterwarnings("ignore::UserWarning")
    def test_plot_curve_rate_show(self):
        curve = DummyCurve()
        fig = plt.figure()
        curve.plot_curve(kind="rate", show=True)
        plt.close(fig)

    def test_plot_curve_invalid_kind(self):
        curve = DummyCurve()
        with pytest.raises(ValueError):
            curve.plot_curve(kind="invalid", show=False)

    def test_plot_title_includes_class_name(self):
        curve = DummyCurve()
        fig = plt.figure()
        curve.plot_curve(kind="rate", show=False)
        ax = plt.gca()
        assert "DummyCurve" in ax.get_title()
        plt.close(fig)
