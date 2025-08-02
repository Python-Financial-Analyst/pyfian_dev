import pytest
import numpy as np
from pyfian.time_value import rate_conversions as rc


class TestNominalPeriodsEffective:
    def test_nominal_periods_to_effective_monthly(self):
        # 12% nominal annual, monthly compounding
        nominal = 0.12
        periods = 12
        ear = rc.nominal_periods_to_effective(nominal, periods)
        assert np.isclose(ear, 0.12682503013196977)

    def test_nominal_periods_to_effective_quarterly(self):
        # 12% nominal annual, quarterly compounding
        nominal = 0.12
        periods = 4
        ear = rc.nominal_periods_to_effective(nominal, periods)
        assert np.isclose(ear, 0.12550881349224116)

    def test_effective_to_nominal_periods_monthly(self):
        # Inverse of above
        ear = 0.12682503013196977
        periods = 12
        nominal = rc.effective_to_nominal_periods(ear, periods)
        assert np.isclose(nominal, 0.12)

    def test_effective_to_nominal_periods_quarterly(self):
        ear = 0.12550881349224116
        periods = 4
        nominal = rc.effective_to_nominal_periods(ear, periods)
        assert np.isclose(nominal, 0.12)

    def test_input_validation(self):
        with pytest.raises(TypeError):
            rc.nominal_periods_to_effective("bad", 12)
        with pytest.raises(TypeError):
            rc.nominal_periods_to_effective(0.12, "bad")
        with pytest.raises(ValueError):
            rc.nominal_periods_to_effective(0.12, 0)
        with pytest.raises(TypeError):
            rc.effective_to_nominal_periods("bad", 12)
        with pytest.raises(TypeError):
            rc.effective_to_nominal_periods(0.12, "bad")
        with pytest.raises(ValueError):
            rc.effective_to_nominal_periods(0.12, 0)
        with pytest.raises(ValueError):
            rc.effective_to_nominal_periods(-2, 12)
