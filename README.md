# PyFiAn

PyFiAn is a Python library for financial analysis, modeling, and computations. It provides modules for corporate finance, derivatives, financial statements, portfolio management, risk management, statistics, time value of money, yield curves, and utility functions.

## Features
- Corporate finance calculations
- Derivatives pricing and analytics
- Financial statement analysis
- Portfolio management tools
- Risk management metrics
- Statistical analysis
- Time value of money functions
- Yield curve modeling
- Utility functions for financial data

## Project Structure
```
pyfian/
    corporate_finance/
    data/
    derivatives/
    financial_statements/
    portfolio/
    risk_management/
    statistics/
    time_value/
    utils/
    yield_curves/
```

## Installation
You can install the package (once published) using pip:

```bash
pip install pyfian
```

Or, for development, clone the repository and install locally:

```bash
git clone <repo-url>
cd pyfian_dev
pip install -e .
```

## Usage Example
```python
from pyfian.time_value.mortgage import mortgage_cash_flows

# Example usage
df = mortgage_cash_flows(
        principal_balance=200000,
        annual_rate=0.04,
        term_months=10,
        payment_interval_months=1,
    )
print(df.to_string(index=False))
```

## Notebooks
Example notebooks are available in the `notebooks/` directory for interactive exploration.

## License
[GNU License](https://github.com/Python-Financial-Analyst/pyfian/blob/main/LICENSE)

## Contributing
Contributions are welcome! Please open issues or submit pull requests.
