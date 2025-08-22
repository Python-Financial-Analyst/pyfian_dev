from abc import ABC, abstractmethod
from typing import Optional, Union
import pandas as pd


# Abstract base class for yield curves


class YieldCurveBase(ABC):
    """
    Abstract base class for yield curves.
    """

    @abstractmethod
    def discount_t(self, t: float, spread: float = 0) -> float:  # pragma: no cover
        """
        Discount a cash flow by time t (in years).
        """
        pass

    @abstractmethod
    def discount_date(
        self, date: Union[str, pd.Timestamp], spread: float = 0
    ) -> float:  # pragma: no cover
        """
        Discount a cash flow by a target date.
        """
        pass

    @abstractmethod
    def __call__(
        self,
        t: float,
        yield_calculation_convention: Optional[str] = None,
        spread: float = 0,
    ) -> float:  # pragma: no cover
        """
        Return the rate at time horizon t (in years).
        """
        pass

    @abstractmethod
    def date_rate(
        self,
        date: Union[str, pd.Timestamp],
        yield_calculation_convention: Optional[str] = None,
        spread: float = 0,
    ) -> float:  # pragma: no cover
        """
        Return the rate at a specified date.
        """
        pass
