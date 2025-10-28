import pandas as pd
import pytest
from pyfian.utils.day_count import (
    DayCountActualActualBond,
    DayCountBase,
    get_day_count_fraction,
    get_day_count_convention,
    DayCount30360,
    DayCount30E360,
    DayCountActualActualISDA,
    DayCountActual360,
    DayCountActual365,
    DayCount30365,
)


def test_daycountbase_methods_raise_notimplemented():
    from pyfian.utils.day_count import DayCountBase

    dc = DayCountBase()
    import pytest

    start = pd.Timestamp("2024-01-01")
    current = pd.Timestamp("2024-07-01")
    with pytest.raises(NotImplementedError):
        dc.numerator(start, current)
    with pytest.raises(NotImplementedError):
        dc.denominator(start, current)


def test_get_day_count_fraction_examples():
    # Example from docstring
    start = pd.Timestamp("2024-01-31")
    end = pd.Timestamp("2024-02-28")
    result = get_day_count_fraction("30/360", start, end, end)
    assert pytest.approx(result, 0.0001) == 0.07777777777777778

    # Another example
    start = pd.Timestamp("2024-01-01")
    end = pd.Timestamp("2024-07-01")
    result = get_day_count_fraction("actual/360", start, end, end)
    assert pytest.approx(result, 0.0001) == (end - start).days / 360.0


def test_get_day_count_convention_examples():
    dc = get_day_count_convention("30/360")
    assert isinstance(dc, DayCount30360)
    dc = get_day_count_convention("actual/360")
    assert isinstance(dc, DayCountActual360)
    dc = get_day_count_convention("actual/actual-ISDA")
    assert isinstance(dc, DayCountActualActualISDA)
    dc = get_day_count_convention("30e/360")
    assert isinstance(dc, DayCount30E360)
    dc = get_day_count_convention("30/365")
    assert isinstance(dc, DayCount30365)
    dc = get_day_count_convention("actual/365")
    assert isinstance(dc, DayCountActual365)
    dc = get_day_count_convention("actual/actual-Bond")
    assert isinstance(dc, DayCountActualActualBond)
    with pytest.raises(ValueError):
        get_day_count_convention("unknown")


# Grouped tests by day count class


class TestDayCount30360:
    def test_fraction(self):
        dc = DayCount30360()
        result = dc.fraction(
            pd.Timestamp("2024-01-31"),
            pd.Timestamp("2024-02-28"),
            pd.Timestamp("2024-02-28"),
        )
        assert pytest.approx(result, 0.0001) == 0.07777777777777778

    def test_dcf_30_360(self):
        dc = DayCount30360()
        start = pd.Timestamp("2024-01-31")
        end = pd.Timestamp("2024-02-28")
        result = dc.fraction(start, end, end)
        assert pytest.approx(result, 0.0001) == 0.07777777777777778

    def test_dcf_30_360_end_of_month(self):
        dc = DayCount30360()
        start = pd.Timestamp("2024-01-31")
        end = pd.Timestamp("2024-03-31")  # Leap year
        result = dc.fraction(start, end, end)
        assert pytest.approx(result, 0.0001) == 0.08333333333333333 * 2

    def test_fraction_period_adjusted(self):
        dc = DayCount30360()
        start = pd.Timestamp("2024-01-31")
        end = pd.Timestamp("2024-02-28")
        # periods_per_year=2 (semiannual)
        result = dc.fraction_period_adjusted(start, end, periods_per_year=2)
        expected = dc.fraction(start, end) * 2
        assert pytest.approx(result, 0.0001) == expected


class TestDayCount30E360:
    def test_fraction(self):
        dc = DayCount30E360()
        result = dc.fraction(
            pd.Timestamp("2024-01-31"),
            pd.Timestamp("2024-02-28"),
            pd.Timestamp("2024-02-28"),
        )
        assert pytest.approx(result, 0.0001) == 0.07777777777777778

    def test_dcf_30e_360(self):
        dc = DayCount30E360()
        start = pd.Timestamp("2024-01-31")
        end = pd.Timestamp("2024-02-28")
        result = dc.fraction(start, end, end)
        assert pytest.approx(result, 0.0001) == 0.07777777777777778

    def test_fraction_period_adjusted(self):
        dc = DayCount30E360()
        start = pd.Timestamp("2024-01-31")
        end = pd.Timestamp("2024-02-28")
        result = dc.fraction_period_adjusted(start, end, periods_per_year=4)
        expected = dc.fraction(start, end) * 4
        assert pytest.approx(result, 0.0001) == expected


class TestDayCountActualActualISDA:
    def test_numerator(self):
        dc = DayCountActualActualISDA()
        start = pd.Timestamp("2024-01-01")
        end = pd.Timestamp("2024-07-01")
        assert dc.numerator(start, end) == (end - start).days

    def test_denominator(self):
        dc = DayCountActualActualISDA()
        start = pd.Timestamp("2024-01-01")
        end = pd.Timestamp("2024-07-01")
        assert dc.denominator(start, end, end) == (end - start).days

    def test_denominator_raises_value_error(self):
        dc = DayCountActualActualISDA()
        start = pd.Timestamp("2024-01-01")
        current = pd.Timestamp("2024-07-01")
        import pytest

        with pytest.raises(ValueError):
            dc.denominator(start, current)

    def test_fraction_period_adjusted(self):
        dc = DayCountActualActualISDA()
        start = pd.Timestamp("2024-01-01")
        current = pd.Timestamp("2024-07-01")
        end = pd.Timestamp("2024-07-01")
        # periods_per_year=2, end required

        result = dc.fraction_period_adjusted(
            start, current, periods_per_year=2, end=end
        )
        expected = (current - start).days / (end - start).days / 2
        assert pytest.approx(result, 0.0001) == expected

    def test_fraction_period_adjusted_raises_value_error(self):
        dc = DayCountActualActualISDA()
        start = pd.Timestamp("2024-01-01")
        current = pd.Timestamp("2024-07-01")
        import pytest

        with pytest.raises(ValueError):
            dc.fraction_period_adjusted(start, current, periods_per_year=2)

    def test_fraction_leap(self):
        dc = DayCountActualActualISDA()
        result = dc.fraction(
            pd.Timestamp("2024-12-31"),
            pd.Timestamp("2025-01-01"),
            pd.Timestamp("2025-01-01"),
        )
        assert pytest.approx(result, 0.0001) == 1 / 366

    def test_fraction_non_leap(self):
        dc = DayCountActualActualISDA()
        result = dc.fraction(
            pd.Timestamp("2023-12-31"),
            pd.Timestamp("2024-01-01"),
            pd.Timestamp("2024-01-01"),
        )
        assert pytest.approx(result, 0.0001) == 1 / 365

    def test_single_day_non_leap(self):
        dc = DayCountActualActualISDA()
        start = pd.Timestamp("2023-12-31")
        end = pd.Timestamp("2024-01-01")
        result = dc.fraction(start, end, end)
        assert pytest.approx(result, 0.0001) == 1 / 365

    def test_single_day_leap(self):
        dc = DayCountActualActualISDA()
        start = pd.Timestamp("2024-12-31")
        end = pd.Timestamp("2025-01-01")
        result = dc.fraction(start, end, end)
        assert pytest.approx(result, 0.0001) == 1 / 366

    def test_multi_year(self):
        dc = DayCountActualActualISDA()
        start = pd.Timestamp("2023-12-31")
        end = pd.Timestamp("2025-01-01")
        expected = 1 / 365 + 366 / 366
        result = dc.fraction(start, end, end)
        assert pytest.approx(result, 0.0001) == expected

    def test_raises_value_error(self):
        dc = DayCountActualActualISDA()
        start = pd.Timestamp("2024-01-01")
        current = pd.Timestamp("2024-07-01")
        import pytest

        with pytest.raises(ValueError):
            dc.fraction(start, current)


class TestDayCountActual360:
    def test_fraction(self):
        dc = DayCountActual360()
        start = pd.Timestamp("2024-01-01")
        end = pd.Timestamp("2024-07-01")
        result = dc.fraction(start, end, end)
        assert pytest.approx(result, 0.0001) == (end - start).days / 360.0

    def test_dcf_actual_360(self):
        dc = DayCountActual360()
        start = pd.Timestamp("2024-01-01")
        end = pd.Timestamp("2024-07-01")
        result = dc.fraction(start, end, end)
        assert pytest.approx(result, 0.0001) == 0.505555555555556

    def test_fraction_period_adjusted(self):
        dc = DayCountActual360()
        start = pd.Timestamp("2024-01-01")
        end = pd.Timestamp("2024-07-01")
        result = dc.fraction_period_adjusted(start, end, periods_per_year=12)
        expected = dc.fraction(start, end, end) * 12
        assert pytest.approx(result, 0.0001) == expected


class TestDayCountActualActualBond:
    def test_denominator_raises_value_error(self):
        dc = DayCountActualActualBond()
        start = pd.Timestamp("2024-01-01")
        current = pd.Timestamp("2024-07-01")
        import pytest

        with pytest.raises(ValueError):
            dc.denominator(start, current)

    def test_fraction_raises_value_error(self):
        dc = DayCountActualActualBond()
        start = pd.Timestamp("2024-01-01")
        current = pd.Timestamp("2024-07-01")
        import pytest

        with pytest.raises(ValueError):
            dc.fraction(start, current)


class TestDayCountActual365:
    def test_fraction(self):
        dc = DayCountActual365()
        start = pd.Timestamp("2024-01-01")
        end = pd.Timestamp("2024-07-01")
        result = dc.fraction(start, end, end)
        assert pytest.approx(result, 0.0001) == (end - start).days / 365.0

    def test_dcf_actual_365(self):
        dc = DayCountActual365()
        start = pd.Timestamp("2024-01-01")
        end = pd.Timestamp("2024-07-01")
        result = dc.fraction(start, end, end)
        assert pytest.approx(result, 0.0001) == 0.4986301369863014

    def test_fraction_period_adjusted(self):
        dc = DayCountActual365()
        start = pd.Timestamp("2024-01-01")
        end = pd.Timestamp("2024-07-01")
        result = dc.fraction_period_adjusted(start, end, periods_per_year=4)
        expected = dc.fraction(start, end, end) * 4
        assert pytest.approx(result, 0.0001) == expected


class TestDayCount30365:
    def test_fraction(self):
        dc = DayCount30365()
        result = dc.fraction(
            pd.Timestamp("2024-01-31"),
            pd.Timestamp("2024-02-28"),
            pd.Timestamp("2024-02-28"),
        )
        assert pytest.approx(result, 0.0001) == 28 / 365

    def test_fraction_30_30(self):
        dc = DayCount30365()
        result = dc.fraction(
            pd.Timestamp("2024-01-30"),
            pd.Timestamp("2024-02-28"),
            pd.Timestamp("2024-02-28"),
        )
        assert pytest.approx(result, 0.0001) == 28 / 365

    def test_dcf_30_365(self):
        dc = DayCount30365()
        start = pd.Timestamp("2024-01-31")
        end = pd.Timestamp("2024-02-28")
        result = dc.fraction(start, end, end)
        assert pytest.approx(result, 0.0001) == 0.07671232876712329

    def test_dcf_30_365_end_of_month(self):
        dc = DayCount30365()
        start = pd.Timestamp("2024-01-31")
        end = pd.Timestamp("2024-03-31")  # Leap year
        result = dc.fraction(start, end, end)
        assert pytest.approx(result, 0.0001) == 0.1643835616438356

    def test_fraction_period_adjusted(self):
        dc = DayCount30365()
        start = pd.Timestamp("2024-01-31")
        end = pd.Timestamp("2024-02-28")
        result = dc.fraction_period_adjusted(start, end, periods_per_year=2)
        expected = dc.fraction(start, end, end) * 2
        assert pytest.approx(result, 0.0001) == expected


def test_dcf_30_360():
    dc = DayCount30360()
    start = pd.Timestamp("2024-01-31")
    end = pd.Timestamp("2024-02-28")
    result = dc.fraction(start, end, end)
    assert pytest.approx(result, 0.0001) == 0.07777777777777778


def test_dcf_30_360_end_of_month():
    dc = DayCount30360()
    start = pd.Timestamp("2024-01-31")
    end = pd.Timestamp("2024-03-31")  # Leap year
    result = dc.fraction(start, end, end)
    assert pytest.approx(result, 0.0001) == 0.08333333333333333 * 2


def test_dcf_30e_360():
    dc = DayCount30E360()
    start = pd.Timestamp("2024-01-31")
    end = pd.Timestamp("2024-02-28")
    result = dc.fraction(start, end, end)
    assert pytest.approx(result, 0.0001) == 0.07777777777777778


def test_is_leap_year():
    from pyfian.utils.day_count import is_leap_year

    assert is_leap_year(2024) is True
    assert is_leap_year(2023) is False
    assert is_leap_year(2000) is True
    assert is_leap_year(1900) is False


def test_dcf_actual_actual_isda():
    dc = DayCountActualActualISDA()
    start = pd.Timestamp("2024-12-31")
    end = pd.Timestamp("2025-01-01")
    result = dc.fraction(start, end, end)
    assert pytest.approx(result, 0.0001) == 1 / 366


def test_dcf_actual_360():
    dc = DayCountActual360()
    start = pd.Timestamp("2024-01-01")
    end = pd.Timestamp("2024-07-01")
    result = dc.fraction(start, end, end)
    assert pytest.approx(result, 0.0001) == 0.505555555555556


def test_dcf_actual_365():
    dc = DayCountActual365()
    start = pd.Timestamp("2024-01-01")
    end = pd.Timestamp("2024-07-01")
    result = dc.fraction(start, end, end)
    assert pytest.approx(result, 0.0001) == 0.4986301369863014


def test_dcf_30_365():
    dc = DayCount30365()
    start = pd.Timestamp("2024-01-31")
    end = pd.Timestamp("2024-02-28")
    result = dc.fraction(start, end, end)
    assert pytest.approx(result, 0.0001) == 0.07671232876712329


def test_dcf_30_365_end_of_month():
    dc = DayCount30365()
    start = pd.Timestamp("2024-01-31")
    end = pd.Timestamp("2024-03-31")  # Leap year
    result = dc.fraction(start, end, end)
    assert pytest.approx(result, 0.0001) == 0.1643835616438356


def test_actual_actual_isda_single_day_non_leap():
    dc = DayCountActualActualISDA()
    start = pd.Timestamp("2023-12-31")
    end = pd.Timestamp("2024-01-01")
    # 2023 is not a leap year, so denominator is 365
    result = dc.fraction(start, end, end)
    assert pytest.approx(result, 0.0001) == 1 / 365


def test_actual_actual_isda_single_day_leap():
    dc = DayCountActualActualISDA()
    start = pd.Timestamp("2024-12-31")
    end = pd.Timestamp("2025-01-01")
    # 2024 is a leap year, so denominator is 366
    result = dc.fraction(start, end, end)
    assert pytest.approx(result, 0.0001) == 1 / 366


def test_actual_actual_isda_multi_year():
    dc = DayCountActualActualISDA()
    start = pd.Timestamp("2023-12-31")
    end = pd.Timestamp("2025-01-01")
    # 2023-12-31 to 2024-01-01: 1/365
    # 2024-01-01 to 2025-01-01: 366/366 (leap year)
    expected = 1 / 365 + 366 / 366
    result = dc.fraction(start, end, end)
    assert pytest.approx(result, 0.0001) == expected


def test_actual_actual_isda_raises_value_error():
    dc = DayCountActualActualISDA()
    start = pd.Timestamp("2024-01-01")
    current = pd.Timestamp("2024-07-01")
    # Should raise ValueError if end is None
    import pytest

    with pytest.raises(ValueError):
        dc.fraction(start, current)


# Tests for __repr__ of day count classes
def test_day_count_repr():
    classes = [
        DayCount30360,
        DayCount30E360,
        DayCountActualActualISDA,
        DayCountActualActualBond,
        DayCountActual360,
        DayCountActual365,
        DayCount30365,
        DayCountBase,
    ]
    for cls in classes:
        instance = cls()
        rep = repr(instance)
        # Should be ClassName()
        assert rep == f"{cls.__name__}()"
