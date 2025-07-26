import pytest

from pyfian.time_value.present_value import (
    present_value_annuity,
    present_value_annuity_annual,
    present_value_growing_annuity,
    present_value_two_stage_annuity,
)


class TestPresentValueAnnuityAnnual:
    def test_annuity_annual_example(self):
        # Example from the docstring: present_value_annuity_annual(100, 0.05, 10, 12)
        result = present_value_annuity_annual(100, 0.05, 10, 12)
        # The expected value is from the docstring example
        expected = 9428.135032823473
        assert pytest.approx(result, rel=1e-6) == expected


class TestPresentValueAnnuity:
    def test_annuity(self):
        payment = 100
        rate = 0.05
        periods = 10
        expected = payment * ((1 - (1 + rate) ** -periods) / rate)
        assert (
            pytest.approx(present_value_annuity(payment, rate, periods), rel=1e-9)
            == expected
        )


class TestPresentValueGrowingAnnuity:
    def test_growing_annuity(self):
        payment = 100
        rate = 0.05
        growth = 0.02
        periods = 10
        if rate == growth:
            expected = sum(
                payment * ((1 + growth) / (1 + rate)) ** k
                for k in range(1, periods + 1)
            )
        else:
            expected = (
                payment
                * (1 + growth)
                * ((1 - ((1 + growth) / (1 + rate)) ** periods) / (rate - growth))
            )
        assert (
            pytest.approx(
                present_value_growing_annuity(payment, rate, periods, growth), rel=1e-9
            )
            == expected
        )

    def test_growing_annuity_rate_eq_growth(self):
        payment = 100
        rate = 0.05
        growth = 0.05
        periods = 10
        if rate == growth:
            expected = sum(
                payment * (1 + growth) ** k / (1 + rate) ** k for k in range(periods)
            )
        else:
            expected = payment * (
                (1 - ((1 + growth) / (1 + rate)) ** periods) / (rate - growth)
            )
        assert (
            pytest.approx(
                present_value_growing_annuity(payment, rate, periods, growth), rel=1e-9
            )
            == expected
        )


class TestPresentValueTwoStageAnnuity:
    def test_two_stage_annuity(self):
        payment = 100
        rate1 = 0.05
        rate2 = 0.06
        periods1 = 5
        periods2 = 5
        pv_stage1 = present_value_annuity(payment, rate1, periods1)
        pv_stage2 = (
            present_value_annuity(payment, rate2, periods2) / (1 + rate1) ** periods1
        )
        expected = pv_stage1 + pv_stage2
        assert (
            pytest.approx(
                present_value_two_stage_annuity(
                    payment, rate1, rate2, periods1, periods2
                ),
                rel=1e-9,
            )
            == expected
        )


class TestPresentValueGrowingPerpetuity:
    def test_growing_perpetuity_growth_gt_rate(self):
        from pyfian.time_value.present_value import present_value_growing_perpetuity

        payment = 100
        rate = 0.03
        growth = 0.05
        with pytest.raises(
            ValueError, match="Interest rate must be greater than growth rate"
        ):
            present_value_growing_perpetuity(payment, rate, growth)


class TestPresentValueTwoStageAnnuityPerpetuity:
    def test_two_stage_annuity_perpetuity_level(self):
        from pyfian.time_value.present_value import (
            present_value_two_stage_annuity_perpetuity,
        )

        payment = 100
        rate1 = 0.05
        periods1 = 5
        rate2 = 0.06
        # No growth in either stage
        expected_annuity = sum(
            payment / (1 + rate1) ** k for k in range(1, periods1 + 1)
        )
        payment_perpetuity = payment  # no growth
        expected_perpetuity = payment_perpetuity / rate2 / (1 + rate1) ** periods1
        expected = expected_annuity + expected_perpetuity
        result = present_value_two_stage_annuity_perpetuity(
            payment, rate1, periods1, rate2
        )
        assert pytest.approx(result, rel=1e-9) == expected

    def test_two_stage_annuity_perpetuity_growing(self):
        from pyfian.time_value.present_value import (
            present_value_two_stage_annuity_perpetuity,
        )

        payment = 100
        rate1 = 0.05
        periods1 = 5
        rate2 = 0.06
        growth1 = 0.02
        growth2 = 0.03

        # First stage: growing annuity
        expected_annuity = sum(
            payment * (1 + growth1) ** k / (1 + rate1) ** k
            for k in range(1, periods1 + 1)
        )
        # Second stage: perpetuity, payment grown for all periods1
        payment_perpetuity = payment * (1 + growth1) ** periods1
        expected_perpetuity = (
            payment_perpetuity
            * (1 + growth2)
            / (rate2 - growth2)
            / (1 + rate1) ** periods1
        )
        expected = expected_annuity + expected_perpetuity
        result = present_value_two_stage_annuity_perpetuity(
            payment, rate1, periods1, rate2, growth1, growth2
        )
        assert pytest.approx(result, rel=1e-9) == expected

    def test_two_stage_annuity_perpetuity_growth_gt_rate(self):
        from pyfian.time_value.present_value import (
            present_value_two_stage_annuity_perpetuity,
        )

        payment = 100
        rate1 = 0.05
        periods1 = 5
        rate2 = 0.03
        growth1 = 0.01
        growth2 = 0.05
        with pytest.raises(
            ValueError, match="Interest rate must be greater than growth rate"
        ):
            present_value_two_stage_annuity_perpetuity(
                payment, rate1, periods1, rate2, growth1, growth2
            )
