# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `pyfian.data` unified clients: **FRED**, **ECB SDMX**, **World Bank**, **SEC EDGAR**, **Yahoo Finance**.
- Automatic HTTP retry with exponential back-off (`requests.Session` + `urllib3.Retry`) in FRED, ECB, and World Bank clients; configurable via `pyfian.data.base.make_session`.
- Mocked unit tests for all five data clients (`tests/data/test_fred.py`, `test_ecb.py`, `test_world_bank.py`, `test_yahoo_finance.py`).
- `src/pyfian/fixed_income/_sensitivities.py` — shared helpers `modified_duration_numerator`, `macaulay_duration_numerator`, `convexity_numerator` used by `FixedRateBullet`, `FloatingRateNote`.
- Curated re-export `__init__.py` files for `fixed_income`, `yield_curves`, `time_value`, `utils`, `visualization`.
- `MATURITIES` constant in `yield_curves.base_curve` (replaces ad-hoc default list).
- `CHANGELOG.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, and GitHub issue/PR templates.

### Changed
- **BEY-Q / BEY-M** — convention names now consistently use a hyphen in docstrings and `VALID_YIELD_CALCULATION_CONVENTIONS`.
- **Typing** — all modules under `fixed_income/`, `yield_curves/`, `time_value/`, and `utils/day_count.py` now use PEP 604 (`X | None`) union syntax and include `from __future__ import annotations`.
- **Numerical precision** — removed pervasive `round(x, 10)` calls from all financial kernels; doctests updated to use `# doctest: +ELLIPSIS`.
- `pytest.ini_options` — added `doctest_optionflags = "ELLIPSIS NORMALIZE_WHITESPACE"` globally.

### Fixed
- `FlatCurve.to_dataframe` default maturity list (`MATURITIES`) was inconsistent across two call sites.

## [0.1.0] — 2024-01-01

### Added
- Initial public pre-alpha release.
- `fixed_income`: `FixedRateBullet`, `FloatingRateNote`, `MoneyMarketInstrument`, `TreasuryBill`, `CertificateOfDeposit`, `CommercialPaper`, `BankersAcceptance`.
- `yield_curves`: flat, spot, par, zero-coupon, interpolated, credit-spread, combined curves.
- `statistics`: distributions, hypothesis tests, VaR/CVaR, Monte-Carlo simulators.
- `time_value`: PV/FV, IRR, mortgage, rate conversions.
- `utils`: day-count conventions.
- `visualization`: yield-curve plotting mixin.

[Unreleased]: https://github.com/Python-Financial-Analyst/pyfian/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Python-Financial-Analyst/pyfian/releases/tag/v0.1.0
