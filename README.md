
# PyFiAn

PyFiAn is a comprehensive Python library designed for financial analysis, modeling, and computation. Developed as a companion to our Python Financial Analyst YouTube channel, PyFiAn bridges the gap between financial theory and practical application. The library offers a wide range of modules covering corporate finance, derivatives, financial statements, fixed income, portfolio management, risk management, statistics, time value of money, yield curves, and utility functions and visualization. Our mission is to help you learn finance by translating concepts into code, enabling hands-on application and access to real-world data.

## Features
- Corporate finance calculations
- Derivatives pricing and analytics
- Financial statement analysis
- Fixed Income Tools
- Portfolio management tools
- Risk management metrics
- Statistical analysis
- Time value of money functions
- Yield curve modeling
- Utility functions for financial data
- Visualization tools

## Project Structure
```
pyfian/
    corporate_finance/
    data/
    derivatives/
    financial_statements/
    fixed_income/
    portfolio/
    risk_management/
    statistics/
    time_value/
    utils/
    yield_curves/
    visualization/
```

## Installation
You can install the package (once published) using pip:

```bash
pip install pyfian
```

Or, for development, clone the repository and install locally:

```bash
git clone <repo-url>
cd pyfian
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
