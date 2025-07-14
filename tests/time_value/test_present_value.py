import pytest
from pyfian.time_value.present_value import (
    present_value_annuity,
    present_value_growing_annuity,
    present_value_two_stage_annuity
)

def test_present_value_annuity():
    payment = 100
    rate = 0.05
    periods = 10
    expected = payment * ((1 - (1 + rate) ** -periods) / rate)
    assert pytest.approx(present_value_annuity(payment, rate, periods), rel=1e-9) == expected

def test_present_value_growing_annuity():
    payment = 100
    rate = 0.05
    growth = 0.02
    periods = 10
    if rate == growth:
        expected = payment * periods * (1 + rate) ** periods
    else:
        expected = payment * ((1 - ((1 + growth) / (1 + rate)) ** periods) / (rate - growth))
    assert pytest.approx(present_value_growing_annuity(payment, rate, growth, periods), rel=1e-9) == expected

def test_present_value_two_stage_annuity():
    payment = 100
    rate1 = 0.05
    rate2 = 0.06
    periods1 = 5
    periods2 = 5
    pv_stage1 = present_value_annuity(payment, rate1, periods1)
    pv_stage2 = present_value_annuity(payment, rate2, periods2) / (1 + rate1) ** periods1
    expected = pv_stage1 + pv_stage2
    assert pytest.approx(present_value_two_stage_annuity(payment, rate1, rate2, periods1, periods2), rel=1e-9) == expected
