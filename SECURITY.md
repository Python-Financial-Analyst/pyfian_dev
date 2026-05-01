# Security Policy

## Supported Versions

| Version  | Supported |
|----------|-----------|
| 0.1.x    | Yes       |
| < 0.1    | No        |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report security issues by e-mailing the maintainer directly at the address listed on the
[PyPI project page](https://pypi.org/project/pyfian/). Include:

1. A description of the vulnerability and the component affected.
2. Steps to reproduce or a proof-of-concept (if applicable).
3. The impact you believe the vulnerability has.

You will receive an acknowledgement within **72 hours** and a resolution timeline within
**7 days** of triage. We follow responsible disclosure: once a fix is released you are
welcome to publish your findings.

## Scope

PyFiAn is a library, not a service. The main attack surfaces are:

- **Data clients** (`pyfian.data`): network requests to third-party APIs (FRED, ECB,
  World Bank, SEC EDGAR, Yahoo Finance). Credentials (e.g. `FRED_API_KEY`) are read
  from environment variables and are never logged or serialised.
- **User-supplied input**: functions accept dates, rates, and identifiers from callers.
  Maliciously crafted inputs could trigger unexpected behaviour; please report any
  crash / unexpected output.

Out of scope: vulnerabilities in optional dependencies (numpy, pandas, scipy, yfinance)
should be reported directly to those projects.
