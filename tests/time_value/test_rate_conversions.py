import pytest
import numpy as np

from pyfian.time_value import rate_conversions as rc


class TestRateConversions:
    def test_continuous_to_effective_and_inverse(self):
        r = 0.05
        ear = rc.continuous_to_effective(r)
        assert np.isclose(ear, 0.05127109637602411)
        assert np.isclose(rc.effective_to_continuous(ear), r)

    def test_single_period_to_effective_and_inverse(self):
        period_rate = 0.01
        periods = 12
        ear = rc.single_period_to_effective(period_rate, periods)
        assert np.isclose(ear, 0.12682503013196977)
        assert np.isclose(rc.effective_to_single_period(ear, periods), period_rate)

    def test_nominal_days_to_effective_and_inverse(self):
        nominal = 0.12
        days = 30
        base = 360
        ear = rc.nominal_days_to_effective(nominal, days, base)
        assert np.isclose(ear, 0.12682503013196977)
        assert np.isclose(rc.effective_to_nominal_days(ear, days, base), nominal)

    def test_money_market_rate_to_effective_and_inverse(self):
        mmr = 0.05
        days = 360
        ear = rc.money_market_rate_to_effective(mmr, days)
        assert np.isclose(ear, 0.05)
        assert np.isclose(rc.effective_to_money_market_rate(ear, days), mmr)
        # Discount basis
        ear_disc = rc.money_market_rate_to_effective(mmr, days, discount=True)
        assert np.isclose(ear_disc, 1 / (1 - 0.05) - 1)
        assert np.isclose(
            rc.effective_to_money_market_rate(ear_disc, days, discount=True), mmr
        )

    def test_bey_to_effective_annual_and_inverse(self):
        bey = 0.06
        ear = rc.bey_to_effective_annual(bey)
        assert np.isclose(ear, 0.0609, atol=1e-4)
        assert np.isclose(rc.effective_annual_to_bey(ear), bey, atol=1e-4)

    def test_input_validation(self):
        with pytest.raises(TypeError):
            rc.continuous_to_effective("bad")
        with pytest.raises(TypeError):
            rc.single_period_to_effective(0.01, "bad")
        with pytest.raises(ValueError):
            rc.single_period_to_effective(0.01, 0)
        with pytest.raises(ValueError):
            rc.effective_to_continuous(-2)
        with pytest.raises(TypeError):
            rc.nominal_days_to_effective(0.01, "bad")
        with pytest.raises(ValueError):
            rc.nominal_days_to_effective(0.01, -1)
