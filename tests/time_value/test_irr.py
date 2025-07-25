"""
test_irr.py

Unit tests for irr.py functions: npv, irr, and np_irr.
"""

import pytest

from pyfian.time_value.irr import irr, np_irr, npv


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
