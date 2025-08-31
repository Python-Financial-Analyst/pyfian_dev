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

    @pytest.mark.parametrize(
        "nominal,days,base,expected_ear",
        [
            (0.12, 30, 365, 0.1268341704586875),
            (0.12, 30, 360, 0.12682503013196977),
        ],
    )
    def test_nominal_days_to_effective_and_inverse(
        self, nominal, days, base, expected_ear
    ):
        ear = rc.nominal_days_to_effective(nominal, days, base)
        assert np.isclose(ear, expected_ear)
        assert np.isclose(rc.effective_to_nominal_days(ear, days, base), nominal)

    @pytest.mark.parametrize(
        "mmr,days,base,expected_ear",
        [
            (0.05, 180, 360, 0.050625),
            (0.12, 30, 360, 0.12682503013196977),
        ],
    )
    def test_money_market_rate_to_effective_and_inverse(
        self, mmr, days, base, expected_ear
    ):
        ear = rc.money_market_rate_to_effective(mmr, days, base)
        assert np.isclose(ear, expected_ear)
        assert np.isclose(rc.effective_to_money_market_rate(ear, days, base), mmr)
        # Discount basis
        ear_disc = rc.money_market_rate_to_effective(mmr, days, base, discount=True)
        # Calculate expected discount EAR for assertion
        expected_ear_disc = (1 / (1 - mmr * days / base)) ** (base / days) - 1
        assert np.isclose(ear_disc, expected_ear_disc)
        assert np.isclose(
            rc.effective_to_money_market_rate(ear_disc, days, base, discount=True), mmr
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


# Separate class for convert_yield tests
class TestConvertYield:
    @pytest.mark.parametrize(
        "rate,from_conv,to_conv,expected",
        [
            (0.05, "BEY", "Annual", 0.050625),
            (0.05, "BEY", "Continuous", 0.04938523625299368),
            (0.05, "Continuous", "Annual", 0.05127109637602411),
            (0.05, "Annual", "Continuous", 0.04879016416943205),
            (0.05, "Annual", "BEY", 0.0493901532),
            (0.05, "Continuous", "BEY", 0.05063),
            (0.05, "BEY", "BEY", 0.05),
            (0.05, "Annual", "Annual", 0.05),
            (0.05, "Continuous", "Continuous", 0.05),
        ],
    )
    def test_convert_yield_conventions(self, rate, from_conv, to_conv, expected):
        result = rc.convert_yield(rate, from_conv, to_conv)
        assert np.isclose(result, expected, atol=1e-7), (
            f"Failed: {rate}, {from_conv} -> {to_conv}, Expected: {expected}, Got: {result}"
        )

    def test_convert_yield_invalid_convention(self):
        with pytest.raises(ValueError):
            rc.convert_yield(0.05, "BAD", "Annual")
        with pytest.raises(ValueError):
            rc.convert_yield(0.05, "Annual", "BAD")
