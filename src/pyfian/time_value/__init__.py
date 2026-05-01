"""Time value of money: present/future value, IRR, rate conversions, means, mortgage."""

from pyfian.time_value.future_value import (
    future_value_annuity,
    future_value_annuity_annual,
    future_value_growing_annuity,
)
from pyfian.time_value.interest_income import (
    interest_income_bey,
    interest_income_continuous,
    interest_income_effective,
    interest_income_money_market_addon_investment,
    interest_income_money_market_addon_notional,
    interest_income_money_market_discount,
    interest_income_nominal_days,
    interest_income_nominal_periods,
)
from pyfian.time_value.irr import (
    irr,
    np_irr,
    npv,
    xirr,
    xirr_base,
    xirr_dates,
)
from pyfian.time_value.means import (
    arithmetic_mean,
    geometric_mean,
    harmonic_mean,
    weighted_geometric_mean,
    weighted_harmonic_mean,
)
from pyfian.time_value.mortgage import (
    calculate_payment,
    generate_amortization_schedule,
    mortgage_cash_flows,
)
from pyfian.time_value.present_value import (
    present_value_annuity,
    present_value_annuity_annual,
    present_value_growing_annuity,
    present_value_growing_perpetuity,
    present_value_two_stage_annuity,
    present_value_two_stage_annuity_perpetuity,
)
from pyfian.time_value.rate_conversions import (
    VALID_YIELD_CALCULATION_CONVENTIONS,
    YIELD_CALCULATION_ADJUSTMENTS,
    bey_to_effective_annual,
    continuous_to_effective,
    convert_effective_to_mmr,
    convert_yield,
    effective_annual_to_bey,
    effective_to_continuous,
    effective_to_money_market_rate,
    effective_to_nominal_days,
    effective_to_nominal_periods,
    effective_to_single_period,
    get_time_adjustment,
    money_market_rate_to_effective,
    nominal_days_to_effective,
    nominal_periods_to_effective,
    single_period_to_effective,
)
from pyfian.time_value.real_rates import (
    fisher_exact_real_rate,
    fisher_real_rate,
)

__all__ = [
    # future_value
    "future_value_annuity",
    "future_value_annuity_annual",
    "future_value_growing_annuity",
    # interest_income
    "interest_income_bey",
    "interest_income_continuous",
    "interest_income_effective",
    "interest_income_money_market_addon_investment",
    "interest_income_money_market_addon_notional",
    "interest_income_money_market_discount",
    "interest_income_nominal_days",
    "interest_income_nominal_periods",
    # irr
    "irr",
    "np_irr",
    "npv",
    "xirr",
    "xirr_base",
    "xirr_dates",
    # means
    "arithmetic_mean",
    "geometric_mean",
    "harmonic_mean",
    "weighted_geometric_mean",
    "weighted_harmonic_mean",
    # mortgage
    "calculate_payment",
    "generate_amortization_schedule",
    "mortgage_cash_flows",
    # present_value
    "present_value_annuity",
    "present_value_annuity_annual",
    "present_value_growing_annuity",
    "present_value_growing_perpetuity",
    "present_value_two_stage_annuity",
    "present_value_two_stage_annuity_perpetuity",
    # rate_conversions
    "VALID_YIELD_CALCULATION_CONVENTIONS",
    "YIELD_CALCULATION_ADJUSTMENTS",
    "bey_to_effective_annual",
    "continuous_to_effective",
    "convert_effective_to_mmr",
    "convert_yield",
    "effective_annual_to_bey",
    "effective_to_continuous",
    "effective_to_money_market_rate",
    "effective_to_nominal_days",
    "effective_to_nominal_periods",
    "effective_to_single_period",
    "get_time_adjustment",
    "money_market_rate_to_effective",
    "nominal_days_to_effective",
    "nominal_periods_to_effective",
    "single_period_to_effective",
    # real_rates
    "fisher_exact_real_rate",
    "fisher_real_rate",
]
