# PyFiAn

[![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![Status](https://img.shields.io/badge/status-pre--alpha-orange.svg)](#roadmap)

**PyFiAn** is a comprehensive Python library for financial analysis, modeling, and computation, developed as a companion to the *Python Financial Analyst* YouTube channel. It bridges financial theory and practical application: every concept is translated into code so you can run it, modify it, and pull real-world data straight from the source.

## What's inside (today)

| Subpackage              | Status      | Highlights |
|-------------------------|-------------|-----------|
| `pyfian.fixed_income`   | Stable      | Fixed-rate bullets, floating-rate notes, money-market instruments, Z/G-spread, OAS-style sensitivities, scenario shocks |
| `pyfian.yield_curves`   | Stable      | Flat (AER/BEY/Log), bootstrapped Spot, Par, Zero-Coupon, Interpolated, Credit-Spread, Combined curves |
| `pyfian.time_value`     | Stable      | PV/FV, IRR/XIRR, mortgage flows, rate conversions (BEY / BEY-Q / BEY-M / Continuous), real rates, geometric/harmonic means |
| `pyfian.statistics`     | Stable      | Distributions, hypothesis tests, parametric/historical VaR & CVaR, GBM and OU simulators, scenario sampling |
| `pyfian.utils`          | Stable      | Day-count conventions (30/360, 30E/360, ACT/ACT-ISDA, ACT/ACT-Bond, ACT/360, ACT/365, 30/365) |
| `pyfian.data`           | Stable      | Unified clients for FRED, ECB SDMX, World Bank, SEC EDGAR, Yahoo Finance with retry/back-off |
| `pyfian.visualization`  | Stable      | Yield-curve plotting mixin |
| `pyfian.corporate_finance`, `pyfian.derivatives`, `pyfian.portfolio`, `pyfian.risk_management`, `pyfian.financial_statements` | Pre-alpha | Reserved namespaces; see [roadmap](#roadmap) |

## Installation

```bash
pip install pyfian          # once published
```

Development install:

```bash
git clone https://github.com/Python-Financial-Analyst/pyfian.git
cd pyfian
pip install -e ".[dev]"
```

Python **3.11+** is required.

## Quickstart

### Fixed income — price a bullet bond

```python
from pyfian.fixed_income import FixedRateBullet

bond = FixedRateBullet(
    issue_dt="2020-01-01",
    maturity="2030-01-01",
    cpn=4.0,
    cpn_freq=2,
)
print(bond.price_from_yield(0.05, settlement_date="2024-01-01"))
print(bond.modified_duration(yield_to_maturity=0.05, settlement_date="2024-01-01"))
print(bond.convexity(yield_to_maturity=0.05, settlement_date="2024-01-01"))
```

### Yield curves — flat curve & discounting

```python
from pyfian.yield_curves import FlatCurveBEY

curve = FlatCurveBEY(bey=0.045, curve_date="2024-01-01")
print(curve.discount_factor(2.5))     # 2.5-year discount factor
print(curve.zero_rate(5.0))           # 5-year zero rate
```

### Time value of money

```python
from pyfian.time_value.mortgage import mortgage_cash_flows
from pyfian.time_value.rate_conversions import convert_yield

df = mortgage_cash_flows(
    principal_balance=200_000,
    annual_rate=0.04,
    term_months=360,
    payment_interval_months=1,
)
print(df.head())
print(convert_yield(0.05, "BEY", "Continuous"))
```

### Data clients — FRED, ECB, World Bank, Yahoo

```python
from pyfian.data import FREDClient, ECBClient, WorldBankClient, YahooFinanceClient

# FRED — public CSV endpoint, no API key needed for series download
gdp = FREDClient().get_series("GDP", start="2000-01-01")

# ECB — SDMX exchange rates
eurusd = ECBClient().get_series("EXR.D.USD.EUR.SP00.A",
                                start="2024-01-01", end="2024-12-31")

# World Bank — multi-country panel
wb = WorldBankClient()
inflation = wb.get_indicator("FP.CPI.TOTL.ZG", ["US", "DE", "JP"],
                             start_year=2010, end_year=2023)

# Yahoo Finance — equity history
prices = YahooFinanceClient().get_history("AAPL", "2024-01-01", "2024-12-31")
```

### SEC EDGAR — filings & financial statements

```python
from pyfian.data import SECClient

client = SECClient(user_agent="Your Name your.email@example.com")
filings = client.get_recent_filings("AAPL", form="10-K", limit=5)
financials = client.get_financials("AAPL")
```

### Statistics — VaR / CVaR

```python
import numpy as np
from pyfian.statistics.risk_measures import historical_var, historical_cvar

returns = np.random.default_rng(0).normal(0, 0.01, 5_000)
print(historical_var(returns, alpha=0.99))
print(historical_cvar(returns, alpha=0.99))
```

## Documentation & notebooks

- Sphinx documentation lives under `docs/`. Build locally with `cd docs && make html`.
- Hands-on tutorials live under `notebooks/` (a Colab badge is added automatically by `add_colab_badge.py`).

## Roadmap

The reserved subpackages (`corporate_finance`, `derivatives`, `portfolio`, `risk_management`, `financial_statements`) currently raise `NotImplementedError` with a pre-alpha hint. They will be filled in as the *Python Financial Analyst* video series progresses. Track progress on the [issue tracker](https://github.com/Python-Financial-Analyst/pyfian/issues).

## Project structure

```
pyfian/
    corporate_finance/      # reserved (pre-alpha)
    data/                   # FRED, ECB, World Bank, SEC EDGAR, Yahoo
    derivatives/            # reserved (pre-alpha)
    financial_statements/   # reserved (pre-alpha)
    fixed_income/           # bonds, FRNs, money-market
    portfolio/              # reserved (pre-alpha)
    risk_management/        # reserved (re-exports statistics.risk_measures)
    statistics/             # distributions, hypothesis, VaR/CVaR, simulation
    time_value/             # PV/FV/IRR/mortgage/rates
    utils/                  # day-count conventions
    yield_curves/           # flat, spot, par, interpolated, credit
    visualization/          # yield-curve plotting
```

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md), use the issue / PR templates under [.github/](.github/), and follow the [Code of Conduct](CODE_OF_CONDUCT.md). Security issues should be reported privately as described in [SECURITY.md](SECURITY.md).

## License

[GNU GPL v3](LICENSE)
