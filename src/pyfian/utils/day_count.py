"""
Day count convention utilities for fixed income calculations.

This module provides classes and functions to compute day count fractions for various conventions used in finance, such as 30/360, Actual/Actual, Actual/360, Actual/365, and others. These are essential for interest accruals, bond pricing, and related calculations.

The day count convention is the standard used to calculate the number of days between two dates in a financial context, which is crucial for determining interest payments, yield calculations, and other time-sensitive financial metrics.

The numerator implies the actual number of days between the two dates, while the denominator represents the total number of days in the period according to the specific day count convention being used.

The `DayCountBase` class provides a common interface for all day count conventions, with methods to calculate the numerator, denominator, and fraction of the year between two dates.

The 30 day count assumes that months have 30 days and years have 360 days, which is common in bond markets. Other conventions may use actual days or different assumptions about month lengths.

The actual day count conventions use the actual number of days between dates, which is more precise but can lead to different results compared to the simplified 30/360 method.

The ISDA (International Swaps and Derivatives Association) convention is widely used in derivatives markets and provides a standardized way to calculate day counts for interest rate swaps and other financial instruments. It accounts for the actual number of days in each month and year, making it suitable for complex financial products.
The difference between ActualActualISDA and other ActualActual conventions is that ISDA uses the actual number of days in each month and year, while others may use simplified assumptions or different day count rules.

The numerator methods calculate the number of days between two dates according to the specific day count convention, while the denominator methods return a fixed value (e.g., 360 for 30/360) or calculate the year length based on actual days.

Supported Day Count Conventions
------------------------------

* 30/360 (Bond Basis):
    - Assumes each month has 30 days and each year has 360 days.
    - Used for US corporate bonds and many other fixed income instruments.
    - Class: DayCount30360
    - Example: get_day_count_fraction('30/360', ...)

* 30E/360 (Eurobond Basis):
    - Similar to 30/360 but treats all end-of-month dates as the 30th.
    - Used for Eurobonds and international markets.
    - Class: DayCount30E360
    - Example: get_day_count_fraction('30e/360', ...)

* Actual/Actual (ISDA):
    - Uses the actual number of days between dates and the actual number of days in the year.
    - Used for US Treasury bonds and some swaps.
    - Class: DayCountActualActualISDA
    - Example: get_day_count_fraction('actual/actual', ...)

* Actual/360:
    - Uses the actual number of days between dates, but assumes a 360-day year.
    - Common in money market instruments and some swaps.
    - Class: DayCountActual360
    - Example: get_day_count_fraction('actual/360', ...)

* Actual/365:
    - Uses the actual number of days between dates, but assumes a 365-day year.
    - Used in UK government bonds and some other instruments.
    - Class: DayCountActual365
    - Example: get_day_count_fraction('actual/365', ...)

* 30/365:
    - Similar to 30/360 but assumes a 365-day year.
    - Less common, but used in some markets.
    - Class: DayCount30365
    - Example: get_day_count_fraction('30/365', ...)

API Overview
------------
- Use `get_day_count_convention(name)` to get a day count convention class instance.
- Use `get_day_count_fraction(convention, start, current, end)` for a unified interface.
- Each convention class (e.g., `DayCount30360`) provides `.fraction(...)` and other methods.

Examples
--------
>>> import pandas as pd
>>> from pyfian.utils.day_count import get_day_count_fraction
>>> start = pd.Timestamp('2024-01-31')
>>> end = pd.Timestamp('2024-02-28')
>>> get_day_count_fraction('30/360', start, end, end)
0.07777777777777778

>>> dc = get_day_count_convention('actual/360')
>>> dc.fraction(pd.Timestamp('2024-01-01'), pd.Timestamp('2024-07-01'), pd.Timestamp('2024-07-01'))
0.5055555555555555
"""

import pandas as pd


def is_leap_year(year: int) -> bool:
    """
    Check if a year is a leap year.
    """
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


class DayCountBase:
    """
    Base class for day count conventions.

    Methods:
        numerator(start, current, end): Returns the numerator for the day count fraction.
        denominator(start, current, end): Returns the denominator for the day count fraction.
        fraction(start, current, end): Returns the day count fraction.
        fraction_period_adjusted(...): For custom periods (e.g., semiannual).

    Example:
        >>> dc = DayCount30360()
        >>> dc.fraction(pd.Timestamp('2024-01-31'), pd.Timestamp('2024-02-28'), pd.Timestamp('2024-02-28'))
        0.07777777777777778
    """

    name = "Base"

    def __repr__(self):
        return f"{self.__class__.__name__}()"

    def numerator(
        self, start: pd.Timestamp, current: pd.Timestamp, end: pd.Timestamp = None
    ) -> float:
        """
        Returns the numerator for the day count fraction according to the convention.
        Calculates the number of days between the date of calculation (`current`) and the start of the period (`start`).

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        end : pd.Timestamp, optional
            End of the period (relevant only for Actual denominator conventions, e.g., next coupon of a bond).

        Returns
        -------
        float
            Numerator for the day count fraction.
        """
        raise NotImplementedError()

    def denominator(
        self, start: pd.Timestamp, current: pd.Timestamp, end: pd.Timestamp = None
    ) -> float:
        """
        Returns the denominator for the day count fraction according to the convention (typically year length).

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        end : pd.Timestamp, optional
            End of the period (relevant only for Actual denominator conventions, e.g., next coupon of a bond).

        Returns
        -------
        float
            Denominator for the day count fraction.
        """
        raise NotImplementedError()

    def fraction(
        self, start: pd.Timestamp, current: pd.Timestamp, end: pd.Timestamp = None
    ) -> float:
        """
        Returns the day count fraction for the convention.

        Represents the fraction of the year between two dates.

        The start of the period is `start` (could be previous coupon date, issue date, or investment date).
        The date of calculation is `current` (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        The end of the period is `end` (could be the next coupon date or maturity date, relevant only for Actual denominator conventions).

        This method calculates the fraction of a year between two dates according to the selected day count convention.
        It is typically used to determine the proportion of a coupon period that has elapsed or will elapse, for interest accruals, bond pricing, and yield calculations.

        The formula for the fraction is:
        :math:`\\frac{\\text{numerator}}{\\text{denominator}}`
        where numerator and denominator are defined by the convention.

        For example, in the 30/360 convention, the numerator is the number of days calculated as if each month has 30 days, and the denominator is 360.

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        end : pd.Timestamp, optional
            End of the period (relevant only for Actual denominator conventions, e.g., next coupon of a bond).

        Returns
        -------
        float
            Day count fraction for the convention (proportion of a year).
        """
        return self.numerator(start, current, end) / self.denominator(
            start, current, end
        )

    def fraction_period_adjusted(
        self,
        start: pd.Timestamp,
        current: pd.Timestamp,
        periods_per_year: int = 1,
        end: pd.Timestamp = None,
    ) -> float:
        """
        Returns the day count fraction for a custom period (e.g., semiannual, quarterly).

        This method is used when the year is divided into multiple periods (such as semiannual or quarterly coupons), and you want the fraction relative to one of those periods rather than the whole year.
        It adjusts the denominator to represent the length of a single period, so the result is the fraction of a period that has elapsed or will elapse.

        The start of the period is `start` (could be previous coupon date, issue date, or investment date).
        The date of calculation is `current` (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        The end of the period is `end` (could be the next coupon date or maturity date, relevant only for Actual denominator conventions).

        The formula for the fraction is:
        :math:`\\frac{\\text{numerator}}{\\frac{\\text{denominator}}{\\text{periods_per_year}}}`

        where numerator and denominator are defined by the convention, and periods_per_year is the number of periods in a year.

        For example, for a bond with semiannual coupons (periods_per_year=2), this method gives the fraction of a half-year period.

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        periods_per_year : int, optional
            Number of periods per year (e.g., 2 for semiannual, 4 for quarterly). Default is 1.
        end : pd.Timestamp, optional
            End of the period (relevant only for Actual denominator conventions, e.g., next coupon of a bond).

        Returns
        -------
        float
            Day count fraction for the custom period (proportion of a period).
        """
        return self.fraction(start, current, end) / periods_per_year


class DayCount30360(DayCountBase):
    """
    30/360 day count convention.

    Calculation:
        The fraction is calculated as:

        :math:`\\frac{360(y_2 - y_1) + 30(m_2 - m_1) + (d_2 - d_1)}{360}`

        where dates are adjusted so that if the day is 31, it is set to 30.

        The numerator is calculated as the difference in days if each month has 30 days, and the denominator is always 360.

    Example:
        >>> dc = DayCount30360()
        >>> dc.fraction(pd.Timestamp('2024-01-31'), pd.Timestamp('2024-02-28'), pd.Timestamp('2024-02-28'))
        0.07777777777777778
    """

    name = "30/360"

    def __repr__(self):
        return f"{self.__class__.__name__}()"

    def numerator(
        self, start: pd.Timestamp, current: pd.Timestamp, end: pd.Timestamp = None
    ) -> float:
        """
        Numerator for 30/360 convention: calculates days as if each month has 30 days.
        Calculates the days between the date of calculation (`current`) and the start of the period (`start`).

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        end : pd.Timestamp, optional
            End of the period (not used).

        Returns
        -------
        float
            Numerator for the day count fraction.
        """
        d1, m1, y1 = start.day, start.month, start.year
        d2, m2, y2 = current.day, current.month, current.year
        if d1 == 31:
            d1 = 30
        if d2 == 31 and d1 == 30:
            d2 = 30
        return 360 * (y2 - y1) + 30 * (m2 - m1) + (d2 - d1)

    def denominator(
        self, start: pd.Timestamp, current: pd.Timestamp, end: pd.Timestamp = None
    ) -> float:
        """
        Denominator for 30/360 convention (always 360).

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        end : pd.Timestamp, optional
            End of the period (not used).

        Returns
        -------
        float
            Denominator for the day count fraction.
        """
        return 360


class DayCount30E360(DayCountBase):
    """
    30E/360 (Eurobond) day count convention.

    Calculation:
        The fraction is calculated as:

        :math:`\\frac{360(y_2 - y_1) + 30(m_2 - m_1) + (d_2 - d_1)}{360}`

        where all days greater than 30 are set to 30.

        The numerator is calculated as the difference in days between the previous coupon date and the settlement date if each month has 30 days, and the denominator is always 360.


    Example:
        >>> dc = DayCount30E360()
        >>> dc.fraction(pd.Timestamp('2024-01-31'), pd.Timestamp('2024-02-28'), pd.Timestamp('2024-02-28'))
        0.07777777777777778
    """

    name = "30E/360"

    def __repr__(self):
        return f"{self.__class__.__name__}()"

    def numerator(
        self, start: pd.Timestamp, current: pd.Timestamp, end: pd.Timestamp = None
    ) -> float:
        """
        Numerator for 30E/360 convention: treats all end-of-month dates as the 30th.
        Calculates the days between the date of calculation (`current`) and the start of the period (`start`).

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        end : pd.Timestamp, optional
            End of the period (not used).

        Returns
        -------
        float
            Numerator for the day count fraction.
        """
        d1 = min(start.day, 30)
        d2 = min(current.day, 30)
        return (
            360 * (current.year - start.year)
            + 30 * (current.month - start.month)
            + (d2 - d1)
        )

    def denominator(
        self, start: pd.Timestamp, current: pd.Timestamp, end: pd.Timestamp = None
    ) -> float:
        """
        Denominator for 30E/360 convention (always 360).

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        end : pd.Timestamp, optional
            End of the period (not used).

        Returns
        -------
        float
            Denominator for the day count fraction.
        """
        return 360


class DayCountActualActualISDA(DayCountBase):
    """
    Actual/Actual ISDA day count convention.

    Calculation:
        The fraction (used for accrued interest in derivatives) is calculated as:

        :math:`\\sum_{i} \\frac{\\text{days}_i}{\\text{days_between}_i}`

        where each year in the period is considered separately. The `days_i` are the actual days between the dates, and `days_between_i` is the total number of days between the two dates.

        The fraction_period_adjusted method can be used for custom periods (e.g., semiannual).
        This is useful for calculating time to next coupon (for YTM).

    Example:
        >>> dc = DayCountActualActualISDA()
        >>> dc.fraction(pd.Timestamp('2024-12-31'), pd.Timestamp('2025-01-01'), pd.Timestamp('2025-01-01'))
        0.00273224043715847
    """

    name = "actual/actual-ISDA"

    def __repr__(self):
        return f"{self.__class__.__name__}()"

    def numerator(
        self, start: pd.Timestamp, current: pd.Timestamp, end: pd.Timestamp = None
    ) -> float:
        """
        Numerator for Actual/Actual ISDA: actual days between the date of calculation (`current`) and the start of the period (`start`).

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        end : pd.Timestamp, optional
            End of the period (not used).

        Returns
        -------
        float
            Numerator for the day count fraction.
        """
        return (current - start).days

    def denominator(
        self, start: pd.Timestamp, current: pd.Timestamp, end: pd.Timestamp = None
    ) -> float:
        """
        Denominator for Actual/Actual ISDA: actual days in the period (from start to end).

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        end : pd.Timestamp, optional
            End of the period (required for Actual denominator conventions, e.g., next coupon of a bond).

        Returns
        -------
        float
            Denominator for the day count fraction.
        """
        if end is None:
            raise ValueError("end is required for Actual/Actual ISDA denominator.")
        return (end - start).days

    def fraction(
        self, start: pd.Timestamp, current: pd.Timestamp, end: pd.Timestamp = None
    ) -> float:
        """
        Returns the day count fraction for Actual/Actual ISDA convention, summing days/year_length for each year in the period.

        The start of the period is `start` (could be previous coupon date, issue date, or investment date).
        The date of calculation is `current` (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        The end of the period is `end` (required for Actual denominator conventions, e.g., next coupon of a bond).

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        end : pd.Timestamp, required
            End of the period (required for Actual denominator conventions, e.g., next coupon of a bond).

        Returns
        -------
        float
            Day count fraction for the convention.
        """
        if end is None:
            raise ValueError("end is required for Actual/Actual ISDA fraction.")
        total = 0.0
        date = start
        while date < end:
            year_length = 366 if is_leap_year(date.year) else 365
            next_year = pd.Timestamp(date.year + 1, 1, 1)
            period_end = min(end, next_year)
            total += (period_end - date).days / year_length
            date = period_end
        return total

    def fraction_period_adjusted(
        self,
        start: pd.Timestamp,
        current: pd.Timestamp,
        periods_per_year: int = 1,
        end: pd.Timestamp = None,
    ) -> float:
        """
        Returns the day count fraction for a custom period for Actual/Actual ISDA.

        The start of the period is `start` (could be previous coupon date, issue date, or investment date).
        The date of calculation is `current` (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        The end of the period is `end` (required for Actual denominator conventions, e.g., next coupon of a bond).

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        periods_per_year : int, optional
            Number of periods per year (e.g., 2 for semiannual). Default is 1.
        end : pd.Timestamp, required
            End of the period (required for Actual denominator conventions, e.g., next coupon of a bond).

        Returns
        -------
        float
            Day count fraction for the custom period.
        """
        if end is None:
            raise ValueError(
                "end is required for Actual/Actual ISDA fraction_period_adjusted."
            )
        return (current - start).days / (end - start).days / periods_per_year


class DayCountActualActualBond(DayCountBase):
    """
    Actual/Actual (Bond) day count convention.

    Calculation:
        The fraction is calculated as:

        :math:`\\frac{\\text{actual days}}{\\text{days in coupon period}}`

        where actual days are the number of days between the previous coupon date and the settlement date,
        and days in coupon period is the number of days between the previous and next coupon dates.

    Example:
        >>> dc = DayCountActualActualBond()
        >>> dc.fraction(pd.Timestamp('2024-01-01'), pd.Timestamp('2024-07-01'), pd.Timestamp('2024-07-01'))
        1.0
    """

    name = "actual/actual-Bond"

    def __repr__(self):
        return f"{self.__class__.__name__}()"

    def numerator(
        self, start: pd.Timestamp, current: pd.Timestamp, end: pd.Timestamp = None
    ) -> float:
        """
        Numerator for Actual/Actual (Bond): actual days between the date of calculation (`current`) and the start of the period (`start`).

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        end : pd.Timestamp, optional
            End of the period (not used).

        Returns
        -------
        float
            Numerator for the day count fraction.
        """
        return (current - start).days

    def denominator(
        self, start: pd.Timestamp, current: pd.Timestamp, end: pd.Timestamp = None
    ) -> float:
        """
        Denominator for Actual/Actual (Bond): days in the period (from start to end).

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        end : pd.Timestamp, required
            End of the period (required for Actual denominator conventions, e.g., next coupon of a bond).

        Returns
        -------
        float
            Denominator for the day count fraction.
        """
        if end is None:
            raise ValueError("end is required for Actual/Actual (Bond) denominator.")
        return (end - start).days

    def fraction(
        self, start: pd.Timestamp, current: pd.Timestamp, end: pd.Timestamp = None
    ) -> float:
        """
        Returns the day count fraction for Actual/Actual (Bond) convention.

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        end : pd.Timestamp, required
            End of the period (required for Actual denominator conventions, e.g., next coupon of a bond).

        Returns
        -------
        float
            Day count fraction for the convention.
        """
        if end is None:
            raise ValueError("end is required for Actual/Actual (Bond) fraction.")
        return self.numerator(start, current, end) / self.denominator(
            start, current, end
        )

    def fraction_period_adjusted(
        self,
        start: pd.Timestamp,
        current: pd.Timestamp,
        periods_per_year: int = 1,
        end: pd.Timestamp = None,
    ) -> float:
        """
        Returns the day count fraction for a custom period for Actual/Actual (Bond).

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        periods_per_year : int, optional
            Number of periods per year (e.g., 2 for semiannual). Default is 1.
        end : pd.Timestamp, required
            End of the period (required for Actual denominator conventions, e.g., next coupon of a bond).

        Returns
        -------
        float
            Day count fraction for the custom period.
        """
        return self.fraction(start, current, end)


class DayCountActual360(DayCountBase):
    """
    Actual/360 day count convention.

    Calculation:
        The fraction is calculated as:

        :math:`\\frac{\\text{actual days}}{360}`

        where actual days are the number of days between the previous coupon date and the settlement date.

    Example:
        >>> dc = DayCountActual360()
        >>> dc.fraction(pd.Timestamp('2024-01-01'), pd.Timestamp('2024-07-01'), pd.Timestamp('2024-07-01'))
        0.5055555555555555
    """

    name = "actual/360"

    def __repr__(self):
        return f"{self.__class__.__name__}()"

    def numerator(
        self, start: pd.Timestamp, current: pd.Timestamp, end: pd.Timestamp = None
    ) -> float:
        """
        Numerator for Actual/360: actual days between the date of calculation (`current`) and the start of the period (`start`).

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        end : pd.Timestamp, optional
            End of the period (not used).

        Returns
        -------
        float
            Numerator for the day count fraction.
        """
        return (current - start).days

    def denominator(
        self, start: pd.Timestamp, current: pd.Timestamp, end: pd.Timestamp = None
    ) -> float:
        """
        Denominator for Actual/360 (always 360).

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        end : pd.Timestamp, optional
            End of the period (not used).

        Returns
        -------
        float
            Denominator for the day count fraction.
        """
        return 360


class DayCountActual365(DayCountBase):
    """
    Actual/365 day count convention.

    Calculation:
        The fraction is calculated as:

        :math:`\\frac{\\text{actual days}}{365}`

        where actual days are the number of days between the previous coupon date and the settlement date.

    Example:
        >>> dc = DayCountActual365()
        >>> dc.fraction(pd.Timestamp('2024-01-01'), pd.Timestamp('2024-07-01'), pd.Timestamp('2024-07-01'))
        0.4986301369863014
    """

    name = "actual/365"

    def __repr__(self):
        return f"{self.__class__.__name__}()"

    def numerator(
        self, start: pd.Timestamp, current: pd.Timestamp, end: pd.Timestamp = None
    ) -> float:
        """
        Numerator for Actual/365: actual days between the date of calculation (`current`) and the start of the period (`start`).

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        end : pd.Timestamp, optional
            End of the period (not used).

        Returns
        -------
        float
            Numerator for the day count fraction.
        """
        return (current - start).days

    def denominator(
        self, start: pd.Timestamp, current: pd.Timestamp, end: pd.Timestamp = None
    ) -> float:
        """
        Denominator for Actual/365 (always 365).

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        end : pd.Timestamp, optional
            End of the period (not used).

        Returns
        -------
        float
            Denominator for the day count fraction.
        """
        return 365


class DayCount30365(DayCountBase):
    """
    30/365 day count convention.

    Calculation:
        The fraction is calculated as:

        :math:`\\frac{360(y_2 - y_1) + 30(m_2 - m_1) + (d_2 - d_1)}{365}`

        where dates are adjusted so that if the day is 31, it is set to 30.

        The numerator is calculated as the difference in days if each month has 30 days, and the denominator is always 365.

    Example:
        >>> dc = DayCount30365()
        >>> dc.fraction(pd.Timestamp('2024-01-31'), pd.Timestamp('2024-02-28'), pd.Timestamp('2024-02-28'))
        0.07671232876712329
    """

    name = "30/365"

    def __repr__(self):
        return f"{self.__class__.__name__}()"

    def numerator(
        self, start: pd.Timestamp, current: pd.Timestamp, end: pd.Timestamp = None
    ) -> float:
        """
        Numerator for 30/365 convention: calculates days as if each month has 30 days.
        Calculates the days between the date of calculation (`current`) and the start of the period (`start`).

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        end : pd.Timestamp, optional
            End of the period (not used).

        Returns
        -------
        float
            Numerator for the day count fraction.
        """
        d1, m1, y1 = start.day, start.month, start.year
        d2, m2, y2 = current.day, current.month, current.year
        if d1 == 31:
            d1 = 30
        if d2 == 31:
            d2 = 30
        return 360 * (y2 - y1) + 30 * (m2 - m1) + (d2 - d1)

    def denominator(
        self, start: pd.Timestamp, current: pd.Timestamp, end: pd.Timestamp = None
    ) -> float:
        """
        Denominator for 30/365 convention (always 365).

        Parameters
        ----------
        start : pd.Timestamp
            Start of the period.
        current : pd.Timestamp
            Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
        end : pd.Timestamp, optional
            End of the period (not used).

        Returns
        -------
        float
            Denominator for the day count fraction.
        """
        return 365


def get_day_count_fraction(
    convention: str,
    start: pd.Timestamp,
    current: pd.Timestamp,
    end: pd.Timestamp = None,
) -> float:
    """
    Unified interface to get day count fraction for any convention.

    Parameters
    ----------
    convention : str
        Name of the day count convention (e.g., '30/360', 'actual/360').
    start : pd.Timestamp
        Start of the period.
    current : pd.Timestamp
        Date of calculation (could be the current date, the maturity date for the full period, or the settlement date of an operation).
    end : pd.Timestamp, optional
        End of the period (relevant only for Actual denominator conventions, e.g., next coupon of a bond).

    Returns
    -------
    float
        Day count fraction for the specified convention.

    Example
    -------
    >>> get_day_count_fraction('30/360', pd.Timestamp('2024-01-31'), pd.Timestamp('2024-02-28'))
    0.07777777777777778
    """
    dc = get_day_count_convention(convention)
    return dc.fraction(start, current, end)


DAY_COUNT_CLASSES = {
    "30/360": DayCount30360,
    "30e/360": DayCount30E360,
    "actual/actual-ISDA": DayCountActualActualISDA,
    "actual/360": DayCountActual360,
    "actual/365": DayCountActual365,
    "30/365": DayCount30365,
    "actual/actual-Bond": DayCountActualActualBond,
}


def get_day_count_convention(name: str) -> DayCountBase:
    """
    Get the day count convention class instance by name.

    Parameters
    ----------
    name : str
        Name of the day count convention (case-insensitive).

    Returns
    -------
    DayCountBase
        Instance of the corresponding day count convention class.

    Example
    -------
    >>> dc = get_day_count_convention('30/360')
    >>> isinstance(dc, DayCount30360)
    True
    """

    if name not in DAY_COUNT_CLASSES:
        raise ValueError(
            f"Unknown day count convention: {name}"
            "\n Day convention must be one of: "
            f"{list(DAY_COUNT_CLASSES.keys())}"
        )
    return DAY_COUNT_CLASSES[name]()
