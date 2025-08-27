pyfian.visualization.mixins
===========================

.. py:module:: pyfian.visualization.mixins


Classes
-------

.. autoapisummary::

   pyfian.visualization.mixins.YieldCurvePlotMixin


Module Contents
---------------

.. py:class:: YieldCurvePlotMixin

   .. py:method:: plot_curve(t_max=30, n=100, kind='rate', show=True, **kwargs)

      Plot the yield curve.

      :param t_max: Maximum time horizon in years.
      :type t_max: float
      :param n: Number of points.
      :type n: int
      :param kind: "rate" to plot rates, "discount" to plot discount factors, "spread" to plot spreads.
      :type kind: str
      :param kwargs: Additional arguments passed to plt.plot.
      :type kwargs: dict



