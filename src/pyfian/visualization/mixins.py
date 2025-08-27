import matplotlib.pyplot as plt
import numpy as np


class YieldCurvePlotMixin:
    def plot_curve(self, t_max=30, n=100, kind="rate", show=True, **kwargs):
        """
        Plot the yield curve.

        Parameters
        ----------
        t_max : float
            Maximum time horizon in years.
        n : int
            Number of points.
        kind : str
            "rate" to plot rates, "discount" to plot discount factors, "spread" to plot spreads.
        kwargs : dict
            Additional arguments passed to plt.plot.
        """
        ts = np.linspace(0, t_max, n)
        if kind == "rate":
            ys = [self.get_rate(t) for t in ts]
            ylabel = "Rate"
        elif kind == "discount":
            if not hasattr(self, "discount_t"):
                raise ValueError("The curve does not have a discount_t method.")
            ys = [self.discount_t(t) for t in ts]
            ylabel = "Discount Factor"
        elif kind == "spread":
            if not hasattr(self, "get_spread"):
                raise ValueError("The curve does not have a get_spread method.")
            ys = [self.get_spread(t) for t in ts]
            ylabel = "Spread"
        else:
            raise ValueError("kind must be 'rate' or 'discount' or 'spread'")
        plt.plot(ts, ys, **kwargs)
        plt.xlabel("Time (years)")
        plt.ylabel(ylabel)
        plt.title(
            f"{self.__class__.__name__} Yield Curve ({self.curve_date.strftime('%Y-%m-%d')})"
        )
        plt.grid(True)
        if show:
            plt.show()
