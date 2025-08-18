"""
test_irr.py

Unit tests for irr.py functions: npv, irr, and np_irr.
"""

from datetime import datetime

import pandas as pd
import pytest

from pyfian.time_value.irr import irr, np_irr, npv, xirr, xirr_dates


class TestNPV:
    def test_basic(self):
        # Example from docstring
        result = npv(0.1, [-100, 50, 60])
        assert abs(result - -4.95867768595) < 1e-8

    def test_zero_rate(self):
        # NPV at 0% rate is just the sum of cash flows
        cash_flows = [-100, 50, 60]
        assert npv(0.0, cash_flows) == sum(cash_flows)


class TestIRR:
    def test_basic(self):
        # Example from docstring
        result = irr([-1000, 300, 400, 500, 600])
        assert abs(result - 0.2488833566240709) < 1e-8

    def test_convergence_fail(self):
        # Should raise ValueError for all positive cash flows (no IRR)
        with pytest.raises(ValueError):
            irr([100, 200, 300])


class TestNumpyIRR:
    def test_basic(self):
        # Example from docstring
        result = np_irr([-1000, 300, 400, 500, 600])
        assert abs(result - 0.2488833566240709) < 1e-8

    def test_multiple_roots(self):
        # Multiple sign changes, numpy may return one root
        cash_flows = [-100, 230, -132, 150]
        result = np_irr(cash_flows)
        assert isinstance(result, float)


class TestIRRvsNumpyIRR:
    def test_compare(self):
        # Compare custom IRR and numpy IRR for typical case
        cash_flows = [-1000, 300, 400, 500, 600]
        custom = irr(cash_flows)
        numpy = np_irr(cash_flows)
        assert abs(custom - numpy) < 1e-6


class TestXIRR:
    def test_xirr_sequence_without_dates(self):
        # Should raise ValueError if cash_flows is a sequence and dates are not provided
        cf = [-1000, 300, 400, 500, 600]
        with pytest.raises(ValueError):
            xirr(cf)

    def test_xirr_base_list(self):
        cf = [-1000, 300, 400, 500, 600]
        dates = [
            datetime(2020, 1, 1),
            datetime(2020, 6, 1),
            datetime(2021, 1, 1),
            datetime(2021, 6, 1),
            datetime(2022, 1, 1),
        ]
        result = xirr_dates(cf, dates)
        assert abs(result - 0.5831820341312749) < 1e-3

    def test_xirr_dict(self):
        cf_dict = {
            datetime(2020, 1, 1): -1000,
            datetime(2020, 6, 1): 300,
            datetime(2021, 1, 1): 400,
            datetime(2021, 6, 1): 500,
            datetime(2022, 1, 1): 600,
        }
        result = xirr(cf_dict)
        assert abs(result - 0.5831820341312749) < 1e-3

    def test_xirr_series(self):
        idx = pd.to_datetime(
            ["2020-01-01", "2020-06-01", "2021-01-01", "2021-06-01", "2022-01-01"]
        )
        cf = pd.Series([-1000, 300, 400, 500, 600], index=idx)
        result = xirr(cf)
        assert abs(result - 0.5831820341312749) < 1e-3

    def test_xirr_list_and_dates(self):
        cf = [-1000, 300, 400, 500, 600]
        dates = ["2020-01-01", "2020-06-01", "2021-01-01", "2021-06-01", "2022-01-01"]
        result = xirr(cf, dates)
        assert abs(result - 0.5831820341312749) < 1e-3

    def test_xirr_invalid_inputs(self):
        with pytest.raises(ValueError):
            xirr([-1000], [datetime(2020, 1, 1)])
        with pytest.raises(ValueError):
            xirr([-1000, 100], [datetime(2020, 1, 1)])
        with pytest.raises(ValueError):
            xirr([100, 200], [datetime(2020, 1, 1), datetime(2020, 6, 1)])
