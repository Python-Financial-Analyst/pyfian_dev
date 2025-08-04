"""
interest_income.py

Interest Income Calculation Module
==================================

This module provides functions to calculate expected interest income for a given period using different types of interest rates:

- Continuous compounding
- Effective annual rate
- Nominal rate (periodic compounding)
- Nominal rate (custom day count)
- Money Market Rate (add-on and discount)
- Bond Equivalent Yield (BEY)

All calculations are per dollar by default, but the principal (notional) can be customized.

Formulas
--------

- Continuous compounding: :math:`I = N \\times (e^{rt} - 1)`
- Effective annual: :math:`I = N \\times ((1 + r)^{t} - 1)`
- Nominal (periodic): :math:`I = N \\times \\frac{r}{n} p`
- Nominal (days): :math:`I = N \\times r \\times \\frac{d}{y}`
- Money Market Rate (discount): :math:`I = N \\times r \\times \\frac{d}{b}`
- Money Market Rate (add-on, notional): :math:`I = \\frac{N}{1 + r d / b} \\times r \\times \\frac{d}{b}`
- Money Market Rate (add-on, investment): :math:`I = N \\times r \\times \\frac{d}{b}`
- BEY: :math:`I = N \\times \\frac{r}{2} \\times p`

Where:
    - :math:`N` = notional
    - :math:`r` = rate (as decimal)
    - :math:`t` = time in years
    - :math:`n` = periods per year
    - :math:`p` = number of periods
    - :math:`d` = days in period
    - :math:`y` = days in year
    - :math:`b` = base days for year (e.g., 360)

Examples
--------
>>> interest_income_continuous(0.05, 1)
0.05127109637602412
>>> interest_income_effective(0.05, 1)
0.05
>>> interest_income_nominal_periods(0.06, 12, 6)
0.03
>>> interest_income_nominal_days(0.06, 30, 360)
0.005
>>> interest_income_money_market_discount(0.06, 180)
0.03
>>> interest_income_money_market_addon_notional(0.06, 180)
0.02912621359223301
>>> interest_income_money_market_addon_investment(0.06, 180)
0.03
>>> interest_income_bey(0.06, 2)
0.06
"""

import numpy as np


def interest_income_continuous(
    rate: float, time: float, notional: float = 1.0
) -> float:
    """
    Calculate interest income using a continuously compounded rate for a given period.

    The formula used is:

    .. math::
        Interest = N \\times (e^{rt} - 1)
    where

    - :math:`N` is the notional amount.
    - :math:`r` is the continuously compounded rate (as decimal).
    - :math:`t` is the time period in years.

    Parameters
    ----------
    rate : float
        Continuously compounded rate (as decimal).
    time : float
        Time period (in years).
    notional : float, optional
        Notional amount (default 1.0).

    Returns
    -------
    float
        Interest income for the given period.

    Examples
    --------
    >>> interest_income_continuous(0.05, 1)
    0.05127109637602412
    """
    return notional * (np.exp(rate * time) - 1)


def interest_income_effective(
    effective_rate: float, time: float, notional: float = 1.0
) -> float:
    """
    Calculate interest income using an effective annual rate for a given period of time.

    The formula used is:

    .. math::
        Interest = N \\times ((1 + r)^{t} - 1)

    where

    - :math:`N` is the notional amount.
    - :math:`r` is the effective annual rate (as decimal).
    - :math:`t` is the time period in years (can be fractional).

    Parameters
    ----------
    effective_rate : float
        Effective annual rate (as decimal).
    time : float
        Time period in years (can be fractional).
    notional : float, optional
        Notional amount (default 1.0).

    Returns
    -------
    float
        Interest income for the given period.

    Examples
    --------
    >>> interest_income_effective(0.05, 1)
    0.05
    """
    return notional * ((1 + effective_rate) ** time - 1)


def interest_income_nominal_periods(
    nominal_rate: float,
    periods_per_year: int,
    periods: float = 1.0,
    notional: float = 1.0,
) -> float:
    """
    Calculate interest income using a nominal rate (periodic compounding) for a given number of periods.

    The formula used is:

    .. math::
        Interest = N \\times \\frac{r}{n} \\times p

    where

    - :math:`N` is the notional amount.
    - :math:`r` is the nominal rate (as decimal).
    - :math:`n` is the number of periods per year.
    - :math:`p` is the number of periods.

    Parameters
    ----------
    nominal_rate : float
        Nominal annual rate (as decimal).
    periods_per_year : int
        Number of periods per year (e.g., 12 for monthly).
    periods : float, optional
        Number of periods (can be fractional for partial periods, default 1.0).
    notional : float, optional
        Notional amount (default 1.0).

    Returns
    -------
    float
        Interest income for the given number of periods.

    Examples
    --------
    >>> interest_income_nominal_periods(0.06, 12, 6)
    0.03
    """
    n = periods_per_year
    return notional * ((nominal_rate / n) * periods)


def interest_income_nominal_days(
    nominal_rate: float,
    days: int,
    base_year: int = 365,
    notional: float = 1.0,
) -> float:
    """
    Calculate interest income using a nominal rate for a custom period (e.g., 30, 90 days) for a given period.

    The formula used is:

    .. math::
        Interest = N \\times r \\times \\frac{d}{base\\_year}

    where

    - :math:`N` is the notional amount.
    - :math:`r` is the nominal rate (as decimal).
    - :math:`d` is the number of days in the period.
    - :math:`base_year` is the convention of days in the year (default 365).

    Parameters
    ----------
    nominal_rate : float
        Nominal annual rate (as decimal).
    days : int
        Number of days in the period.
    base_year : int, optional
        Number of days in a year (default 365).
    notional : float, optional
        Notional amount (default 1.0).

    Returns
    -------
    float
        Interest income for the given period.

    Examples
    --------
    >>> interest_income_nominal_days(0.06, 30, 360)
    0.005
    """
    # Calculate interest income directly from nominal rate and compounding for custom period
    return notional * nominal_rate * (days / base_year)


def interest_income_money_market_discount(
    mmr: float, mmr_days: int = 360, base: float = 360, notional: float = 1.0
) -> float:
    """
    Calculate interest income using a Money Market Rate (discount) for a given period.

    The formula used is:

    .. math::
        Interest = N \\times r \\times \\frac{d}{base\\_year}
    where

    - :math:`N` is the notional amount.
    - :math:`r` is the Money Market Rate (as decimal).
    - :math:`d` is the number of days in the period.
    - :math:`base\\_year` is the convention of days in the year (default 360).

    Parameters
    ----------
    mmr : float
        Money Market Rate (discount, as decimal).
    mmr_days : int, optional
        Number of days in the period (default 360).
    base : float, optional
        Base days for the year (default 360).
    notional : float, optional
        Notional amount (default 1.0).

    Returns
    -------
    float
        Interest income for the given period.

    Examples
    --------
    >>> interest_income_money_market_discount(0.06, 180)
    0.03
    """
    return notional * mmr * (mmr_days / base)


# Calculate interest income using Money Market Rate (add-on). The input can be the notional or the investment amount.
def interest_income_money_market_addon_notional(
    mmr: float, mmr_days: int, base: float = 360, notional: float = 1.0
) -> float:
    """
    Calculate interest income using a Money Market Rate (add-on) for a given period.
    This function assumes the notional is the total amount to be paid (face value).

    The formula used is:

    .. math::
        Interest = \\frac{Notional}{1 + r d / base\\_year} \\times r \\times \\frac{d}{base\\_year}

    where

    - :math:`Notional` is the notional amount (face value).
    - :math:`r` is the Money Market Rate (as decimal).
    - :math:`d` is the number of days in the period.
    - :math:`base\\_year` is the convention of days in the year (default 360).

    Parameters
    ----------
    mmr : float
        Money Market Rate (add-on, as decimal).
    mmr_days : int
        Number of days in the period.
    base : float, optional
        Base days for the year (default 360).
    notional : float, optional
        Notional (face value) amount (default 1.0).

    Returns
    -------
    float
        Interest income for the given period.

    Examples
    --------
    >>> interest_income_money_market_addon_notional(0.06, 180)
    0.02912621359223301
    """
    investment = notional / (1 + mmr * (mmr_days / base))
    return investment * mmr * (mmr_days / base)


def interest_income_money_market_addon_investment(
    mmr: float, mmr_days: int, base: float = 360, notional: float = 1.0
) -> float:
    """
    Calculate interest income using a Money Market Rate (add-on) for a given period.
    This function assumes the notional is the amount that will earn interest (investment amount).

    The formula used is:

    .. math::
        Interest = N \\times r \\times \\frac{d}{base\\_year}

    where

    - :math:`N` is the notional amount (investment).
    - :math:`r` is the Money Market Rate (as decimal).
    - :math:`d` is the number of days in the period.
    - :math:`base\\_year` is the convention of days in the year (default 360).

    Parameters
    ----------
    mmr : float
        Money Market Rate (add-on, as decimal).
    mmr_days : int
        Number of days in the period.
    base : float, optional
        Base days for the year (default 360).
    notional : float, optional
        Notional (investment) amount (default 1.0).

    Returns
    -------
    float
        Interest income for the given period.

    Examples
    --------
    >>> interest_income_money_market_addon_investment(0.06, 180)
    0.03
    """
    return notional * mmr * (mmr_days / base)


def interest_income_bey(bey: float, periods: int = 1, notional: float = 1.0) -> float:
    """
    Calculate interest income using Bond Equivalent Yield (BEY) for a given period.

    The formula used is:

    .. math::
        Interest = N \\times \\frac{r}{2} \\times p

    where

    - :math:`N` is the notional amount.
    - :math:`r` is the Bond Equivalent Yield (as decimal).
    - :math:`p` is the number of semiannual periods.

    Parameters
    ----------
    bey : float
        Bond Equivalent Yield (as decimal, annualized, semiannual compounding).
    periods : int, optional
        Number of semiannual periods (default 1).
    notional : float, optional
        Notional amount (default 1.0).

    Returns
    -------
    float
        Interest income for the given period.

    Examples
    --------
    >>> interest_income_bey(0.06, 2)
    0.06
    """
    return notional * bey / 2 * periods
