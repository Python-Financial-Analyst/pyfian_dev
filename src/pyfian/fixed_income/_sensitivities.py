"""Shared cash-flow-based sensitivity formulas (Phase 4.20 mixin extraction).

This module centralises the closed-form sensitivity computations that were
previously duplicated across :class:`pyfian.fixed_income.fixed_rate_bond.FixedRateBullet`,
:class:`pyfian.fixed_income.floating_rate_note.FloatingRateNote` and
:class:`pyfian.fixed_income.money_market_instruments.MoneyMarketInstrument`.

All helpers operate on a ``{time_in_years: cash_flow}`` mapping plus the
discount-rate convention parameters; callers are responsible for resolving
yield-to-maturity, price and time-to-payment maps. Returns are unweighted
(i.e. not divided by price); callers normalise as appropriate.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np


def macaulay_duration_numerator(
    times_cashflows: Mapping[float, float],
    ytm: float,
    time_adjustment: float,
    yield_calculation_convention: str,
) -> float:
    """Sum of ``t * cf * DF(t)`` (Macaulay-duration numerator).

    Divide by price (sum of ``cf * DF(t)``) to obtain Macaulay duration.
    """
    if yield_calculation_convention == "Continuous":
        return sum(t * cf * np.exp(-ytm * t) for t, cf in times_cashflows.items())
    return sum(
        t * cf / (1 + ytm / time_adjustment) ** (t * time_adjustment)
        for t, cf in times_cashflows.items()
    )


def modified_duration_numerator(
    times_cashflows: Mapping[float, float],
    ytm: float,
    time_adjustment: float,
    yield_calculation_convention: str,
) -> float:
    """Sum of ``t * cf * DF(t) / (1 + ytm/m)`` (Modified-duration numerator).

    For continuous compounding this equals :func:`macaulay_duration_numerator`.
    Divide by price to obtain modified duration.
    """
    if yield_calculation_convention == "Continuous":
        return sum(t * cf * np.exp(-ytm * t) for t, cf in times_cashflows.items())
    return sum(
        t * cf / (1 + ytm / time_adjustment) ** (t * time_adjustment + 1)
        for t, cf in times_cashflows.items()
    )


def convexity_numerator(
    times_cashflows: Mapping[float, float],
    ytm: float,
    time_adjustment: float,
    yield_calculation_convention: str,
) -> float:
    """Sum of ``cf * t * (t*m + 1) * m / (1 + ytm/m)^(t*m+2)`` (convexity numerator).

    For continuous compounding the formula reduces to
    ``sum(cf * t**2 * exp(-ytm*t))``. Divide by ``price * time_adjustment**2``
    to obtain (annualised) convexity.
    """
    if yield_calculation_convention == "Continuous":
        return sum(cf * t**2 * np.exp(-ytm * t) for t, cf in times_cashflows.items())
    return sum(
        cf
        * t
        * time_adjustment
        * (t * time_adjustment + 1)
        / (1 + ytm / time_adjustment) ** (t * time_adjustment + 2)
        for t, cf in times_cashflows.items()
    )
