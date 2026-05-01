"""pyfian: Tools for financial analysis and data processing.

The public API is organised into the following sub-packages:

* :mod:`pyfian.time_value` - present/future value, IRR, rate conversions,
  means and amortization schedules.
* :mod:`pyfian.fixed_income` - fixed-rate bonds, floating-rate notes,
  custom-flow bonds and money-market instruments.
* :mod:`pyfian.yield_curves` - flat, interpolated, par and spot curves,
  combined curves and credit-spread curves.
* :mod:`pyfian.statistics` - distributions, simulation, regression,
  descriptive statistics, hypothesis tests and risk measures.
* :mod:`pyfian.utils` - day-count conventions and shared utilities.
* :mod:`pyfian.data` - clients for FRED, ECB, World Bank, Yahoo Finance
  and SEC EDGAR.
* :mod:`pyfian.visualization` - mix-in plotting helpers.

Sub-packages are not imported eagerly to keep ``import pyfian`` cheap.
Import what you need, e.g.::

    from pyfian.fixed_income import FixedRateBullet
    from pyfian.yield_curves import FlatCurveAER
    from pyfian.time_value import irr, present_value_annuity
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
