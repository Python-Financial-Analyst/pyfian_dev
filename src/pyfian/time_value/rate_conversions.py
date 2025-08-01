"""
rate_conversions.py

Module for converting between all major types of interest and yield rates used in finance.

Supported conversions:
- Continuous compounding (force of interest) <-> Effective annual rate (EAR)
- Nominal rate (periodic compounding, e.g., monthly, quarterly, semiannual) <-> Effective annual rate (EAR)
- Nominal rate for custom periods (e.g., 30, 90, 180 days) <-> Effective annual rate (EAR)
- Single period rate <-> Effective annual rate (EAR)
- Money Market Rate (MMR, add-on or discount, actual/360) <-> Effective annual rate (EAR)
- Bond Equivalent Yield (BEY, semiannual-pay bond convention) <-> Effective annual rate (EAR)

These conversions are essential for comparing, quoting, and reporting interest rates and yields across different financial products, regulatory frameworks, and institutional conventions.
"""

import numpy as np


# --- Internal helpers for exponentiation logic ---
def _exp_general(base, n):
    """
    Generalized exponentiation for rate conversions:
    Returns base**n - 1
    """
    return np.power(base, n) - 1


# --- Centralized input validation ---
def _validate_numeric(x, name="value"):
    if not isinstance(x, (int, float, np.ndarray)):
        raise TypeError(f"{name} must be a number or numpy array.")


def _validate_positive_number(x, name="value"):
    if not (isinstance(x, (int, float)) and not isinstance(x, bool)):
        raise TypeError(f"{name} must be a positive integer or float.")
    if x <= 0:
        raise ValueError(f"{name} must be positive.")


def _validate_effective_rate(effective_rate):
    _validate_numeric(effective_rate, "effective_rate")
    if np.any(np.less_equal(effective_rate, -1)):
        raise ValueError("effective_rate must be greater than -1.")


# continuous_to_effective <-> effective_to_continuous conversions
def continuous_to_effective(rate: float) -> float:
    r"""
    Convert a continuously compounded rate to an effective annual rate.

    Theory & Institutional Context:
    - Continuously compounded rates (also called "force of interest") are a mathematical idealization where interest is compounded at every instant. This is common in theoretical finance, derivatives pricing, and some institutional contexts (e.g., certain bond math, Black-Scholes model).
    - Effective annual rate (EAR) is the real-world annualized return, accounting for compounding. It is the standard for comparing investments or loans with different compounding conventions.
    - Regulatory and institutional reporting (e.g., APR, APY) often require conversion to EAR for transparency and comparability.

    This function calculates the effective annual rate (EAR) from a continuously compounded rate.
    Continuously compounded interest is a theoretical concept where interest is calculated and
    added to the principal constantly, creating a smooth growth curve. The relationship is
    defined by the formula: :math:`\mathrm{EAR} = e^{r} - 1`.

    Parameters
    ----------
    rate : float
        The continuously compounded rate, expressed as a decimal.

    Returns
    -------
    float
        The corresponding effective annual rate, expressed as a decimal.

    Examples
    --------
    >>> continuous_to_effective(0.05)
    0.05127109637602411
    """
    _validate_numeric(rate, "rate")
    return np.exp(rate) - 1


def effective_to_continuous(effective_rate: float) -> float:
    r"""
    Convert an effective annual rate to a continuously compounded rate.

    Theory & Institutional Context:
    - Effective annual rate (EAR) is the standard for comparing interest rates across products and institutions, as it reflects the true annualized return or cost.
    - Continuously compounded rates are used in advanced financial mathematics, fixed income analytics, and some institutional contracts (e.g., certain swaps, derivatives, and bond pricing models).
    - Regulatory disclosures may require conversion from EAR to continuous rates for risk-neutral pricing or actuarial calculations.

    The relationship is defined by the formula: :math:`r = \ln(1 + \mathrm{EAR})`.

    Parameters
    ----------
    effective_rate : float
        Effective annual rate (as decimal).

    Returns
    -------
    float
        Continuously compounded rate (as decimal).

    Examples
    --------
    >>> effective_to_continuous(0.05127109637602411)
    0.05
    """
    _validate_effective_rate(effective_rate)
    return np.log1p(effective_rate)


# periodic_to_effective <-> effective_to_periodic conversions
def nominal_periods_to_effective(nominal_rate: float, periods_per_year: int) -> float:
    r"""
    Convert a nominal rate that refers to periods (e.g., monthly, quarterly, semiannual) to an effective annual rate (EAR).

    Theory & Institutional Context:
    - Nominal rates ("APR" in some contexts) are often quoted by banks and financial institutions for loans, mortgages, and deposits, but do not account for intra-year compounding.
    - Effective annual rate (EAR) is required for true comparability, as it incorporates the effect of compounding within the year.
    - Regulatory frameworks (e.g., Truth in Lending Act, EU Consumer Credit Directive) often require disclosure of EAR/APY for consumer protection.
    - This conversion is essential for comparing products with different compounding conventions (e.g., monthly vs. quarterly).

    The relationship is defined by the formula:
    :math:`\mathrm{EAR} = (1 + r/n)^{n} - 1`,
    where :math:`r` is the nominal rate and :math:`n` is the number of periods per year.
    Quarterly equals 4 periods per year, monthly equals 12, Semiannual equals 2.

    Parameters
    ----------
    nominal_rate : float
        The nominal rate (as decimal).
    periods_per_year : int
        Number of periods per year (e.g., 12 for monthly, 4 for quarterly, 2 for semiannual).

    Returns
    -------
    float
        Effective annual rate (as decimal).

    Examples
    --------
    >>> nominal_periods_to_effective(0.12, 12)  # monthly 1%
    0.12682503013196977
    >>> nominal_periods_to_effective(0.12, 4)   # quarterly 3%
    0.12550881349224116
    """
    _validate_numeric(nominal_rate, "nominal_rate")
    _validate_positive_number(periods_per_year, "periods_per_year")
    return _exp_general(1 + nominal_rate / periods_per_year, periods_per_year)


def effective_to_nominal_periods(effective_rate: float, periods_per_year: int) -> float:
    """
    Convert an effective annual rate (EAR) to a nominal rate that refers to periods (e.g., monthly, quarterly, semiannual).

    Theory & Institutional Context:
    - Effective annual rate (EAR) is the true annualized return or cost, accounting for compounding, and is the regulatory standard for disclosure.
    - Nominal rates are often used in contracts, advertisements, and loan agreements, but may mislead if compounding is not considered.
    - This conversion is required for constructing payment schedules, amortization tables, and for regulatory compliance in financial product disclosures.

    The relationship is defined by the formula:
    :math:`r = ((1 + \\mathrm{EAR})^{1/n} - 1) \times n`,
    where :math:`n` is the number of periods per year.
    Quarterly equals 4 periods per year, monthly equals 12, Semiannual equals 2.

    Parameters
    ----------
    effective_rate : float
        Effective annual rate (as decimal).
    periods_per_year : int
        Number of periods per year (e.g., 12 for monthly, 4 for quarterly, 2 for semiannual).

    Returns
    -------
    float
        Periodic rate (as decimal).

    Examples
    --------
    >>> effective_to_nominal_periods(0.12682503013196977, 12)  # monthly
    0.12
    >>> effective_to_nominal_periods(0.12550881349224116, 4)   # quarterly
    0.12
    """
    _validate_effective_rate(effective_rate)
    _validate_positive_number(periods_per_year, "periods_per_year")
    return _exp_general(1 + effective_rate, 1 / periods_per_year) * periods_per_year


# nominal_days_to_effective <-> effective_to_nominal_days conversions
def nominal_days_to_effective(
    nominal_rate: float, days: int, base_year: int = 365
) -> float:
    r"""
    Convert a nominal rate for a period of given days to an effective annual rate.

    Theory & Institutional Context:
    - Nominal rates for non-standard periods (e.g., 30, 90, 180 days) are common in money markets,
      commercial paper, and short-term lending.
    - Effective annual rate (EAR) is needed for comparing instruments with different day-count conventions
      or maturities.
    - Institutional conventions (e.g., actual/360, actual/365, 30/360) affect the calculation and regulatory reporting.
    - This conversion is essential for yield curve construction, risk management, and regulatory disclosures.

    The relationship is defined by the formula:
    :math:`\mathrm{EAR} = (1 + r)^{N} - 1`,
    where :math:`N = \frac{\text{base\_year}}{\text{days}}`.

    Parameters
    ----------
    nominal_rate : float
        Nominal rate for the period (as decimal).
    days : int
        Number of days in the period.
    base_year : int, optional
        Number of days in the year (default 365).

    Returns
    -------
    float
        Effective annual rate (as decimal).

    Examples
    --------
    >>> nominal_days_to_effective(0.12, 30, 360)
    0.12682503013196977
    """
    _validate_numeric(nominal_rate, "nominal_rate")
    _validate_positive_number(days, "days")
    _validate_positive_number(base_year, "base_year")
    periods = base_year / days
    return _exp_general(1 + nominal_rate / periods, periods)


def effective_to_nominal_days(
    effective_rate: float, days: int, base_year: int = 365
) -> float:
    r"""
    Convert an effective annual rate to a nominal rate for a period of given days.

    Theory & Institutional Context:
    - Effective annual rate (EAR) is the standard for comparability, but many money market and short-term
      instruments are quoted on a non-annual basis (e.g., 30, 90, 180 days).
    - This conversion is required for pricing, quoting, and regulatory reporting of short-term debt, repos,
      and commercial paper.
    - Day-count conventions (actual/360, actual/365, 30/360) are institutionally defined and affect the calculation.

    The relationship is defined by the formula:
    :math:`r = (1 + \mathrm{EAR})^{1/N} - 1`,
    where :math:`N = \frac{\text{base\_year}}{\text{days}}`.

    Parameters
    ----------
    effective_rate : float
        Effective annual rate (as decimal).
    days : int
        Number of days in the period.
    base_year : int, optional
        Number of days in the year (default 365).

    Returns
    -------
    float
        Nominal rate for the period (as decimal).

    Examples
    --------
    >>> effective_to_nominal_days(0.12682503013196977, 30, 360)
    0.12
    """
    _validate_effective_rate(effective_rate)
    _validate_positive_number(days, "days")
    _validate_positive_number(base_year, "base_year")
    periods = base_year / days
    return _exp_general(1 + effective_rate, 1 / periods) * periods


# single_period_to_effective <-> effective_to_period conversions
def single_period_to_effective(period_rate: float, periods: int) -> float:
    r"""
    Convert a periodic rate to an effective annual rate.

    Theory & Institutional Context:
    - Periodic rates (e.g., monthly, quarterly) are used in most consumer and institutional loan and
      deposit products.
    - Effective annual rate (EAR) is the standard for comparing products with different compounding intervals.
    - This conversion is required for regulatory disclosures, product comparison, and financial modeling.

    This function computes the effective annual rate (EAR) from a rate that compounds at a specified
    frequency. The formula is: :math:`\mathrm{EAR} = (1 + r)^{n} - 1`.
    For example, a monthly rate is a periodic rate with 12 periods per year. This is a fundamental calculation
    for comparing different investment opportunities with varying compounding frequencies.

    Parameters
    ----------
    period_rate : float
        The rate for the compounding period, expressed as a decimal.
    periods : int
        The number of compounding periods in one year.

    Returns
    -------
    float
        The effective annual rate, expressed as a decimal.

    Examples
    --------
    >>> single_period_to_effective(0.01, 12)
    0.12682503013196977
    """
    _validate_numeric(period_rate, "period_rate")
    if not isinstance(periods, (int, float)):
        raise TypeError("periods must be a number.")
    if periods <= 0:
        raise ValueError("periods must be positive.")
    return _exp_general(1 + period_rate, periods)


def effective_to_single_period(effective_rate: float, periods: int) -> float:
    r"""
    Convert an effective annual rate to a periodic rate.

    Theory & Institutional Context:
    - Effective annual rate (EAR) is the regulatory and economic standard for comparability.
    - Periodic rates are used for payment calculations, amortization, and contract terms in loans,
      mortgages, and deposits.
    - This conversion is necessary for constructing payment schedules and for regulatory compliance.

    The relationship is defined by the formula:
    :math:`r = (1 + \mathrm{EAR})^{1/n} - 1`,
    where :math:`n` is the number of periods per year.

    Parameters
    ----------
    effective_rate : float
        Effective annual rate (as decimal).
    periods : int
        Number of periods per year.

    Returns
    -------
    float
        Rate for the period (as decimal).

    Examples
    --------
    >>> effective_to_single_period(0.12682503013196977, 12)
    0.01
    """
    _validate_effective_rate(effective_rate)
    _validate_positive_number(periods, "periods")
    return _exp_general(1 + effective_rate, 1 / periods)


# money_market_rate_to_effective <-> effective_to_money_market_rate conversions
def money_market_rate_to_effective(
    mmr: float, days: int = 360, base: float = 360, discount: bool = False
) -> float:
    """
    Convert a Money Market Rate (MMR, actual/360) to effective annual rate (EAR).

    Theory & Institutional Context:
    - Money Market Rates (MMR) are quoted on a 360-day basis and may be add-on (interest-bearing) or discount rates. These conventions are standard in interbank markets, T-bills, and commercial paper.
    - Effective annual rate (EAR) is required for comparability across instruments and regulatory reporting.
    - Discount rates are used for zero-coupon instruments (e.g., T-bills), while add-on rates are used for interest-bearing notes.
    - Regulatory and accounting standards may require conversion to EAR for disclosure and risk management.

    If discount is False (add-on):
    :math:`\\mathrm{EAR} = (1 + \\mathrm{MMR})^{\text{base}/\text{days}} - 1`

    If discount is True:
    :math:`\\mathrm{EAR} = (1 / (1 - \\mathrm{MMR}))^{\text{base}/\text{days}} - 1`

    Parameters
    ----------
    mmr : float
        Money Market Rate (as decimal).
    days : int, optional
        Number of days in the year (default 360).
    base : float, optional
        Base for the calculation (default 360).
    discount : bool, optional
        If True, interpret mmr as a discount rate. If False (default), as an add-on (interest-bearing) rate.

    Returns
    -------
    float
        Effective annual rate (as decimal).

    Examples
    --------
    >>> money_market_rate_to_effective(0.05, 360)
    0.05126749646744716
    >>> money_market_rate_to_effective(0.05, 360, discount=True)
    0.05263157894736836
    """
    _validate_numeric(mmr, "mmr")
    _validate_positive_number(days, "days")
    _validate_positive_number(base, "base")
    if discount:
        return _exp_general(1 / (1 - mmr), base / days)
    else:
        return _exp_general(1 + mmr, base / days)


def effective_to_money_market_rate(
    effective_rate: float, days: int = 360, base: float = 360, discount: bool = False
) -> float:
    """
    Convert an effective annual rate (EAR) to a Money Market Rate (actual/360).

    Theory & Institutional Context:
    - Effective annual rate (EAR) is the standard for comparability, but money market instruments are quoted using market conventions (actual/360, add-on or discount).
    - This conversion is required for quoting, pricing, and regulatory reporting of T-bills, commercial paper, and interbank loans.
    - Discount and add-on conventions are institutionally defined and affect the calculation and comparability.

    If discount is False (add-on):
    :math:`\\mathrm{MMR} = (1 + \\mathrm{EAR})^{\text{days}/\text{base}} - 1`

    If discount is True:
    :math:`\\mathrm{MMR} = 1 - 1 / (1 + \\mathrm{EAR})^{\text{days}/\text{base}}`

    Parameters
    ----------
    effective_rate : float
        Effective annual rate (as decimal).
    days : int, optional
        Number of days in the year (default 360).
    base : float, optional
        Base for the calculation (default 360).
    discount : bool, optional
        If True, return the discount rate. If False (default), return the add-on (interest-bearing) rate.

    Returns
    -------
    float
        Money Market Rate (as decimal).

    Examples
    --------
    >>> effective_to_money_market_rate(0.05126749646744716, 360)
    0.05
    >>> effective_to_money_market_rate(0.05263157894736836, 360, discount=True)
    0.05
    """
    _validate_effective_rate(effective_rate)
    _validate_positive_number(days, "days")
    _validate_positive_number(base, "base")
    if discount:
        # Discount basis: mmr = 1 - 1 / (1 + EAR) ** (days/base)
        return 1 - 1 / np.power(1 + effective_rate, days / base)
    else:
        return _exp_general(1 + effective_rate, days / base)


# Bond Equivalent Yield (BEY) <-> Effective Annual Rate conversions
def bey_to_effective_annual(bey: float) -> float:
    r"""
    Convert Bond Equivalent Yield (BEY) to effective annual rate (EAR).

    Theory & Institutional Context:
    - Bond Equivalent Yield (BEY) is a convention used in US bond markets to annualize yields on semiannual-pay bonds, making them comparable to other investments.
    - BEY is not compounded; it simply doubles the semiannual rate. Effective annual rate (EAR) compounds the semiannual rate, providing a true annualized return.
    - Regulatory and institutional reporting (e.g., SEC, FINRA) may require both BEY and EAR for disclosure and comparability.
    - This conversion is essential for comparing bonds to other fixed income or investment products.

    BEY is defined as 2 * semiannual rate (not compounded). EAR compounds the semiannual rate:
    :math:`\mathrm{EAR} = (1 + \mathrm{BEY}/2)^2 - 1`

    Parameters
    ----------
    bey : float
        Bond Equivalent Yield (as decimal).

    Returns
    -------
    float
        Effective annual rate (as decimal).

    Examples
    --------
    >>> bey_to_effective_annual(0.06)
    0.0609
    """
    semiannual = bey / 2
    return _exp_general(1 + semiannual, 2)


def effective_annual_to_bey(effective_rate: float) -> float:
    """
    Convert effective annual rate (EAR) to Bond Equivalent Yield (BEY).

    Theory & Institutional Context:
    - Effective annual rate (EAR) is the true annualized return, accounting for compounding, and is the standard for comparability.
    - Bond Equivalent Yield (BEY) is a market convention for quoting yields on semiannual-pay bonds, used for comparability in US fixed income markets.
    - Regulatory disclosures and institutional reporting may require both BEY and EAR for transparency and comparability.
    - This conversion is necessary for comparing bonds to other investments and for regulatory filings.

    Inverse of bey_to_effective_annual. :math:`\\mathrm{BEY} = 2 \times \text{semiannual rate}`, where
    :math:`\text{semiannual} = (1 + \\mathrm{EAR})^{0.5} - 1`

    Parameters
    ----------
    effective_rate : float
        Effective annual rate (as decimal).

    Returns
    -------
    float
        Bond Equivalent Yield (as decimal).

    Examples
    --------
    >>> effective_annual_to_bey(0.0609)
    0.06
    """
    semiannual = _exp_general(1 + effective_rate, 1 / 2)
    return 2 * semiannual
