# Make base class for fixed income instruments
from abc import ABC, abstractmethod
from typing import Optional, Union

from matplotlib import pyplot as plt
import pandas as pd
from scipy import optimize

from pyfian.utils.day_count import (
    DayCountActual365,
    DayCountBase,
    get_day_count_convention,
)
from pyfian.yield_curves.base_curve import YieldCurveBase


class BaseFixedIncomeInstrument(ABC):
    adjust_to_business_days: bool
    day_count_convention: DayCountBase
    following_coupons_day_count: DayCountBase
    yield_calculation_convention: str
    issue_dt: pd.Timestamp
    _settlement_date: pd.Timestamp
    payment_flow: dict
    _yield_to_maturity: Optional[float]
    coupon_flow: dict
    amortization_flow: dict
    maturity: pd.Timestamp

    @abstractmethod
    def _price_from_yield(
        self,
        time_to_payments: dict,
        yield_to_maturity: float,
        yield_calculation_convention: str,
    ) -> float:  # pragma: no cover
        # Calculate the present value of the instrument's cash flows
        pass

    @abstractmethod
    def yield_to_maturity(self, *args, **kwargs) -> float:  # pragma: no cover
        pass

    @abstractmethod
    def _validate_following_coupons_day_count(
        self, following_coupons_day_count: str | DayCountBase
    ) -> DayCountBase:  # pragma: no cover
        pass

    @abstractmethod
    def _validate_yield_calculation_convention(
        self, yield_calculation_convention: str
    ) -> str:  # pragma: no cover
        pass

    def _resolve_valuation_parameters(
        self,
        adjust_to_business_days: Optional[bool],
        day_count_convention: Optional[str | DayCountBase],
        following_coupons_day_count: Optional[str | DayCountBase],
        yield_calculation_convention: Optional[str],
    ) -> tuple[bool, DayCountBase, DayCountBase, str]:
        if yield_calculation_convention is None:
            yield_calculation_convention = self.yield_calculation_convention
        else:
            yield_calculation_convention = self._validate_yield_calculation_convention(
                yield_calculation_convention
            )
        if adjust_to_business_days is None:
            adjust_to_business_days = self.adjust_to_business_days
        if yield_calculation_convention not in ["Annual", "Continuous"]:
            if day_count_convention is None:
                day_count_convention = self.day_count_convention
            elif isinstance(day_count_convention, str):
                day_count_convention = get_day_count_convention(day_count_convention)
            if following_coupons_day_count is None:
                following_coupons_day_count = self.following_coupons_day_count
            else:
                following_coupons_day_count = (
                    self._validate_following_coupons_day_count(
                        following_coupons_day_count
                    )
                )
        else:
            day_count_convention = DayCountActual365()
            following_coupons_day_count = DayCountActual365()

        return (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

    def _get_ytm_payments_price(
        self,
        yield_to_maturity: Optional[float],
        price: Optional[float],
        settlement_date: Optional[Union[str, pd.Timestamp]],
        adjust_to_business_days: bool,
        day_count_convention: DayCountBase,
        following_coupons_day_count: DayCountBase,
        yield_calculation_convention: str,
    ) -> tuple[float | None, dict[float, float], float | None]:
        """
        Helper to resolve ytm, time_to_payments, and price_calc for DRY.
        Returns (ytm, time_to_payments, price_calc)
        """

        ytm, price_calc = self._resolve_ytm_and_price(
            yield_to_maturity,
            price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        time_to_payments = self._calculate_time_to_payments(
            settlement_date,
            price=price_calc,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        return ytm, time_to_payments, price_calc

    def _resolve_settlement_date(
        self, settlement_date: Optional[Union[str, pd.Timestamp]]
    ) -> pd.Timestamp:
        """
        Helper to resolve the settlement date for the bond.
        If settlement_date is provided, converts to pd.Timestamp.
        Otherwise, uses self._settlement_date or self.issue_dt.
        """
        if settlement_date is not None:
            dt = pd.to_datetime(settlement_date)
            if dt < self.issue_dt:
                raise ValueError("Settlement date cannot be before issue date.")
            return dt
        if self._settlement_date is not None:
            return pd.Timestamp(self._settlement_date)
        return self.issue_dt

    @abstractmethod
    def _calculate_time_to_payments(
        self,
        settlement_date,
        price,
        adjust_to_business_days,
        following_coupons_day_count,
        yield_calculation_convention,
        day_count_convention,
    ) -> dict:  # pragma: no cover
        pass

    @abstractmethod
    def _price_from_yield_and_clean_parameters(
        self,
        yield_to_maturity: float,
        settlement_date: Optional[Union[str, pd.Timestamp]],
        adjust_to_business_days: bool,
        following_coupons_day_count: DayCountBase,
        yield_calculation_convention: str,
        day_count_convention: DayCountBase,
    ) -> float:  # pragma: no cover
        pass

    def _resolve_ytm_and_price(
        self,
        yield_to_maturity: Optional[float],
        price: Optional[float],
        settlement_date: Optional[Union[str, pd.Timestamp]],
        adjust_to_business_days: bool,
        day_count_convention: DayCountBase,
        following_coupons_day_count: DayCountBase,
        yield_calculation_convention: str,
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Helper to resolve yield_to_maturity and price from direct input, price, or default to notional.
        Returns a tuple (ytm, price_calc), both float or None.
        """
        # Case 1: price is provided, ytm is None
        if price is not None and yield_to_maturity is None:
            if price < 0:
                raise ValueError("Bond price cannot be negative.")
            ytm = self.yield_to_maturity(
                price=price,
                settlement_date=settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                day_count_convention=day_count_convention,
            )
            return ytm, price

        # Case 2: both price and ytm are provided
        if price is not None and yield_to_maturity is not None:
            if price < 0:
                raise ValueError("Bond price cannot be negative.")
            price_calc = self.price_from_yield(
                yield_to_maturity,
                settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                day_count_convention=day_count_convention,
            )
            if abs(price_calc - price) / price > 0.001 / 100:
                raise ValueError(
                    "Bond price calculated by yield to maturity does not match the given bond price."
                    "Given bond price: {}, calculated bond price: {}".format(
                        price, price_calc
                    )
                )
            return yield_to_maturity, price

        # Case 3: only ytm is provided
        if yield_to_maturity is not None:
            price = self._price_from_yield_and_clean_parameters(
                yield_to_maturity=yield_to_maturity,
                settlement_date=settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                day_count_convention=day_count_convention,
            )
            return yield_to_maturity, price

        # Case 4: use stored values if available and settlement date matches
        if (
            self._yield_to_maturity is not None
            and self._settlement_date == settlement_date
        ):
            if (
                day_count_convention != self.day_count_convention
                or yield_calculation_convention != self.yield_calculation_convention
            ):
                ytm = self.yield_to_maturity(
                    price=price,
                    settlement_date=settlement_date,
                    adjust_to_business_days=adjust_to_business_days,
                    following_coupons_day_count=following_coupons_day_count,
                    yield_calculation_convention=yield_calculation_convention,
                    day_count_convention=day_count_convention,
                )
            else:
                ytm = self._yield_to_maturity

            return ytm, self._price

        # Case 5: cannot determine, return None, None
        return None, None

    def _filter_payment_flow(
        self,
        settlement_date,
        price,
        payment_flow,
        adjust_to_business_days,
        day_count_convention,
        following_coupons_day_count,
        yield_calculation_convention,
    ):
        """Filter the payment flow based on the settlement date and other parameters."""
        maturity = self.maturity
        if adjust_to_business_days:

            def business_days_adjustment(x):
                return x - pd.offsets.BDay(1) + pd.offsets.BDay(1)
        else:

            def business_days_adjustment(x):
                return x

        # If settlement date would be after maturity, there are no cash flows
        if settlement_date > business_days_adjustment(maturity):
            return {}
        cash_flows = {}

        # If a price is provided, add it as a negative cash flow
        if price is not None:
            cash_flows[settlement_date] = -price

        # Include all payments after the settlement date
        cash_flows.update(
            {
                business_days_adjustment(pd.to_datetime(key)): value
                for key, value in payment_flow.items()
                if (
                    settlement_date + pd.offsets.BDay(self.record_date_t_minus)
                    <= business_days_adjustment(pd.to_datetime(key))
                )
                or (pd.to_datetime(key) == maturity and (settlement_date <= key))
            }
        )

        return cash_flows

    def plot_cash_flows(
        self,
        yield_to_maturity: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> None:
        """
        Visualize the cash flow schedule using matplotlib as stacked bars.

        Parameters
        ----------
        settlement_date : str or datetime-like, optional
            Date from which to consider future payments. Defaults to issue date.
        price : float, optional
            If provided, includes bond price as a negative cash flow.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.

        Examples
        --------
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 2)
        >>> bond.plot_cash_flows(settlement_date='2022-01-01') # doctest: +SKIP
        # Shows a plot
        """
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )
        df = self.to_dataframe(
            settlement_date=settlement_date,
            yield_to_maturity=yield_to_maturity,
            price=price,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        x_labels = df.index.strftime("%Y-%m-%d")
        cost = -df["Cost"]
        coupon = df["Coupon"]
        amortization = df["Amortization"]

        plt.figure(figsize=(10, 6))
        plt.bar(x_labels, cost, width=0.6, label="Cost")
        plt.bar(x_labels, coupon, width=0.6, bottom=cost, label="Coupon")
        plt.bar(
            x_labels,
            amortization,
            width=0.6,
            bottom=cost + coupon,
            label="Amortization",
        )
        plt.xlabel("Date")
        plt.ylabel("Cash Flow")
        plt.title("Bond Cash Flow Schedule (Stacked)")
        plt.xticks(rotation=45)
        plt.legend()
        plt.tight_layout()
        plt.show()

    def dv01(
        self,
        yield_to_maturity: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> float:
        """
        Calculate the DV01 (Dollar Value of a 1 basis point) for the bond.
        If neither yield_to_maturity nor price is provided, it is assumed that the clean price is equal to the notional.

        Parameters
        ----------
        yield_to_maturity : float, optional
            Yield to maturity as a decimal (e.g., 0.05 for 5%).
        price : float, optional
            Price of the bond. Used to estimate YTM if yield_to_maturity is not provided.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.

        Returns
        -------
        dv01 : float
            The change in price for a 1 basis point (0.0001) change in yield.

        Examples
        --------
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 2)
        >>> bond.dv01(yield_to_maturity=0.05)
        -0.0437603218
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )
        # Resolve yield to maturity and bond price
        ytm, time_to_payments, price_calc = self._get_ytm_payments_price(
            yield_to_maturity,
            price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        if ytm is None:
            raise ValueError(
                "Unable to resolve yield to maturity. You must input settlement_date and either yield_to_maturity or price. Previous information was not available."
            )

        price_up = self.price_from_yield(
            ytm + 0.0001,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        price_down = self.price_from_yield(
            ytm - 0.0001,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        return round((price_up - price_down) / 2, 10)

    def filter_payment_flow(
        self,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        price: Optional[float] = None,
        payment_flow: Optional[dict[pd.Timestamp, float]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> dict[pd.Timestamp, float]:
        """
        Filter the payment flow to include only payments after the settlement date.

        If a bond price is provided, it is added as a negative cash flow at the settlement date.

        The settlement date is resolved to a pd.Timestamp, and if it is not provided, it defaults to the issue date.

        The function returns a dictionary of payment dates and cash flows that occur after the settlement date.
        If `adjust_to_business_days` is True (default: value of self.adjust_to_business_days), payment dates are adjusted to business days.

        Parameters
        ----------
        settlement_date : str or datetime-like, optional
            Date from which to consider future payments. Defaults to issue date.
        price : float, optional
            If provided, adds the bond price as a negative cash flow at the settlement date.
        payment_flow : dict, optional
            Dictionary of payment dates and cash flows. If not provided, uses the bond's payment flow.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.

        Returns
        -------
        cash_flows : dict
            Dictionary of filtered payment dates and cash flows.

        Examples
        --------
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.filter_payment_flow('2022-01-01') # doctest: +SKIP
        {Timestamp('2023-01-01 00:00:00'): 5.0, Timestamp('2024-01-01 00:00:00'): 5.0,
        Timestamp('2025-01-01 00:00:00'): 105.0}
        """
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        if payment_flow is None:
            payment_flow = self.payment_flow

        settlement_date = self._resolve_settlement_date(settlement_date)

        self._validate_price(price)

        return self._filter_payment_flow(
            settlement_date,
            price,
            payment_flow,
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

    def calculate_time_to_payments(
        self,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        price: Optional[float] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> dict[float, float]:
        """
        Calculate the time to each payment from the settlement date.
        The time is expressed in years.

        .. math::
            T = \\frac{D - S}{365}

        for each payment :math:`D` and settlement date :math:`S`

        where:

        - :math:`T` is the time to payment (in years)
        - :math:`D` is the payment date
        - :math:`S` is the settlement date

        Parameters
        ----------
        settlement_date : str or datetime-like, optional
            Date from which to calculate time to payments. Defaults to issue date.
        price : float, optional
            If provided, adds bond price as a negative cash flow.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.

        Returns
        -------
        dict
            Dictionary with time to payment (in years) as keys and cash flow values.

        Examples
        --------
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 2)
        >>> bond.calculate_time_to_payments('2022-01-01')
        {0.5: 2.5, 1.0: 2.5, 1.5: 2.5, 2.0: 2.5, 2.5: 2.5, 3.0: 102.5}
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        return self._calculate_time_to_payments(
            settlement_date,
            price,
            adjust_to_business_days,
            following_coupons_day_count,
            yield_calculation_convention,
            day_count_convention,
        )

    def set_settlement_date(
        self,
        settlement_date: Optional[Union[str, pd.Timestamp]],
        reset_yield_to_maturity: bool = True,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> pd.Timestamp:
        """
        Set the default settlement date for the bond.
        If reset_yield_to_maturity is True, resets the yield to maturity and bond price.

        Parameters
        ----------
        settlement_date : Union[str, pd.Timestamp], optional
            The settlement date to set.
        reset_yield_to_maturity : bool, optional
            Whether to reset the yield to maturity and bond price.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.

        Returns
        -------
        pd.Timestamp
            The updated settlement date.

        Raises
        ------
        ValueError
            If the settlement date is not set when the bond price is set.
        If the settlement date is changed, resets the bond price and yield to maturity if reset_yield_to_maturity is True.
        """
        old_settlement_date = self._settlement_date
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        if settlement_date is not None:
            settlement_date = pd.to_datetime(settlement_date)
            if settlement_date < self.issue_dt:
                raise ValueError("Settlement date cannot be before issue date.")
            if (
                old_settlement_date is not None
                and settlement_date != old_settlement_date
            ):
                # If the settlement date is changed, reset related attributes
                self._price = None
                if reset_yield_to_maturity:
                    self._yield_to_maturity = None
                else:
                    # If not resetting YTM, ensure it is still valid
                    if self._yield_to_maturity is not None:
                        self._price = self.price_from_yield(
                            self._yield_to_maturity,
                            settlement_date,
                            adjust_to_business_days=adjust_to_business_days,
                            day_count_convention=day_count_convention,
                            following_coupons_day_count=following_coupons_day_count,
                            yield_calculation_convention=yield_calculation_convention,
                        )

            self._settlement_date = pd.to_datetime(settlement_date)
        else:
            self._settlement_date = None
            # If no settlement date is set, reset bond price and YTM
            self._price = None
            self._yield_to_maturity = None
        return self._settlement_date

    def set_yield_to_maturity(
        self,
        yield_to_maturity: Optional[float],
        settlement_date: Optional[Union[str, pd.Timestamp, None]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> None:
        """
        Set the default yield to maturity for the bond. Updates bond price accordingly.

        Parameters
        ----------
        yield_to_maturity : float, optional
            The yield to maturity to set.
        settlement_date : Union[str, pd.Timestamp], optional
            The settlement date to set.
        adjust_to_business_days : bool, optional
            Whether to adjust the settlement date to the next business day.
        day_count_convention : str or DayCountBase, optional
            The day count convention to use.
        following_coupons_day_count : str or DayCountBase, optional
            The following coupons day count convention to use.
        yield_calculation_convention : str, optional
            The yield calculation convention to use.

        Raises
        ------
        ValueError
            If the settlement date is not set when the yield to maturity is set.

        If the yield to maturity is set, it will also update the bond price based on the yield.
        """
        self._yield_to_maturity = yield_to_maturity
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        if settlement_date is not None:
            settlement_date = self.set_settlement_date(
                settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                day_count_convention=day_count_convention,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
            )
        # Since yield_to_maturity is set, update bond price
        if yield_to_maturity is not None:
            settlement_date = self._settlement_date
            if settlement_date is None:
                raise ValueError(
                    "Settlement date must be set since there is no default settlement_date for the bond."
                )
            self._price = self._price_from_yield_and_clean_parameters(
                yield_to_maturity=yield_to_maturity,
                settlement_date=settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                day_count_convention=day_count_convention,
            )
        else:
            # If no yield to maturity is set, reset bond price and yield to maturity
            self._price = None
            self._yield_to_maturity = None

    def _validate_price(self, price: Optional[float]) -> None:
        """
        Validate the bond price.
        Raises ValueError if the bond price is negative.
        """
        if price is not None and price < 0:
            raise ValueError("Bond price cannot be negative.")

    def set_price(
        self,
        price: Optional[float],
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> None:
        """
        Set the default bond price for the bond. Updates yield to maturity accordingly.

        Parameters
        ----------
        price : float, optional
            The bond price to set.
        settlement_date : Union[str, pd.Timestamp], optional
            The settlement date to set.
        adjust_to_business_days : bool, optional
            Whether to adjust the settlement date to the next business day.
        day_count_convention : str or DayCountBase, optional
            The day count convention to use.
        following_coupons_day_count : str or DayCountBase, optional
            The following coupons day count convention to use.
        yield_calculation_convention : str, optional
            The yield calculation convention to use.

        Raises
        ------
        ValueError
            If the settlement date is not set when the bond price is set.

        If the bond price is set, it will also update the yield to maturity based on the bond price.
        """
        self._validate_price(price=price)
        self._price = price
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        if settlement_date is not None:
            settlement_date = self.set_settlement_date(
                settlement_date,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                day_count_convention=day_count_convention,
            )

        # Since bond price is set, update yield to maturity
        if price is not None:
            vdate = self._settlement_date
            if vdate is None:
                raise ValueError(
                    "Settlement date must be set since there is no default settlement_date for the bond."
                )
            self._yield_to_maturity = self.yield_to_maturity(
                price,
                vdate,
                adjust_to_business_days=adjust_to_business_days,
                following_coupons_day_count=following_coupons_day_count,
                yield_calculation_convention=yield_calculation_convention,
                day_count_convention=day_count_convention,
            )
        else:
            # If no bond price is set, reset yield to maturity and bond price
            self._price = None
            self._yield_to_maturity = None

    def get_settlement_date(self) -> Optional[pd.Timestamp]:
        """
        Get the current settlement date for the bond.
        Returns
        -------
        Optional[pd.Timestamp]
            The current settlement date, or None if not set.
        """
        return self._settlement_date

    def get_yield_to_maturity(self) -> Optional[float]:
        """
        Get the current yield to maturity for the bond.
        Returns
        -------
        Optional[float]
            The current yield to maturity, or None if not set.
        """
        return self._yield_to_maturity

    def get_price(self) -> Optional[float]:
        """
        Get the current bond price for the bond.
        Returns
        -------
        Optional[float]
            The current bond price, or None if not set.
        """
        return self._price

    def to_dataframe(
        self,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        yield_to_maturity: Optional[float] = None,
        price: Optional[float] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Export the bond’s cash flow schedule as a pandas DataFrame.

        The DataFrame will contain the dates of cash flows and their corresponding amounts.

        The cash flows include:
        - Principal repayment at maturity
        - Coupon payments
        - Amortization payments (if applicable)
        - Bond price as a negative cash flow if provided

        The Dataframe will have the following columns:
        - 'date': The date of the cash flow.
        - 'Flows': The amount of the total cash flow.
        - 'Coupon': The coupon payment amount.
        - 'Amortization': The amortization payment amount.
        - 'Cost': The net cash flow after subtracting coupon and amortization payments.

        Parameters
        ----------
        settlement_date : str or datetime-like, optional
            Date from which to consider future payments. Defaults to issue date.
        yield_to_maturity : float, optional
            Yield to maturity as a decimal. If provided, it will be used to calculate the cash flows.
        price : float, optional
            If provided, includes bond price as a negative cash flow.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.

        Returns
        -------
        df : pd.DataFrame
            DataFrame with columns ['date', 'cash_flow']

        Examples
        --------
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.to_dataframe('2022-01-01') # doctest: +SKIP
        date        Flows  Coupon  Amortization  Cost
        2023-01-01  5.0    5.0          0.0           0.0
        2024-01-01  5.0    5.0          0.0           0.0
        2025-01-01  105.0  5.0        100.0           0.0
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        ytm, time_to_payments, price_calc = self._get_ytm_payments_price(
            yield_to_maturity,
            price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        # If neither yield_to_maturity nor price is provided, make price calculation None
        if yield_to_maturity is None and price is None:
            valid_price_calc = False
        else:
            valid_price_calc = True

        flows = self.filter_payment_flow(
            settlement_date,
            price_calc if valid_price_calc else None,
            adjust_to_business_days=adjust_to_business_days,
            day_count_convention=day_count_convention,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
        )

        coupon_flows = self.filter_payment_flow(
            settlement_date,
            None,
            self.coupon_flow,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        amortization_flows = self.filter_payment_flow(
            settlement_date,
            None,
            self.amortization_flow,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        # Concat coupon_flows and amortization_flows in a single dataframe
        df = (
            pd.concat(
                [
                    pd.Series(flows, name="Flows"),
                    pd.Series(coupon_flows, name="Coupon"),
                    pd.Series(amortization_flows, name="Amortization"),
                ],
                axis=1,
            )
            .astype(float)
            .fillna(0)
        )
        df["Cost"] = df["Coupon"] + df["Amortization"] - df["Flows"]
        df.index = pd.DatetimeIndex(df.index)

        return df.sort_index()

    def cash_flows(
        self,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> list[float]:
        """
        Return a list of all future cash flows (coupons + principal at maturity).

        Parameters
        ----------
        settlement_date : str or datetime-like, optional
            Date from which to consider future payments. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.

        Returns
        -------
        flows : list of float
            List of cash flows for each period.

        Examples
        --------
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.cash_flows('2022-01-01')
        [5.0, 5.0, 105.0]
        """
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        flows = self.filter_payment_flow(
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        return list(flows.values())

    def price_from_yield(
        self,
        yield_to_maturity: float,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> float:
        """
        Calculate the price of the bond given a yield to maturity (YTM).

        .. math::
            Price = \\sum_{t=1}^{T} \\frac{C_t}{(1 + YTM)^{t}}

        where:
            - :math:`C_t` is the cash flow at time `t`
            - :math:`YTM` is the yield to maturity
            - :math:`T` is the total number of periods

        Parameters
        ----------
        yield_to_maturity : float
            Yield to maturity as a decimal.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.

        Returns
        -------
        price : float
            Price of the bond.

        Examples
        --------
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 2)
        >>> bond.price_from_yield(0.05) # doctest: +ELLIPSIS
        100.0...
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        price = self._price_from_yield_and_clean_parameters(
            yield_to_maturity=yield_to_maturity,
            settlement_date=settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        return price

    def clean_price(
        self,
        dirty_price: float,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
    ) -> float:
        """
        Convert dirty price to clean price.

        The clean price is the price of the bond excluding any accrued interest.

        The formula is as follows:

        .. math::
            CleanPrice = DirtyPrice - AccruedInterest

        Parameters
        ----------
        dirty_price : float
            Dirty price of the bond.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to today.

        Returns
        -------
        clean_price : float
            Clean price of the bond.

        Examples
        --------
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.clean_price(102.5, '2024-07-02')
        100.0
        """
        return dirty_price - self.accrued_interest(settlement_date)

    def dirty_price(
        self,
        clean_price: float,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
    ) -> float:
        """
        Convert clean price to dirty price.

        The dirty price is the price of the bond including accrued interest.

        The formula is as follows:

        .. math::
            DirtyPrice = CleanPrice + AccruedInterest

        Parameters
        ----------
        clean_price : float
            Clean price of the bond.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to today.

        Returns
        -------
        dirty_price : float
            Dirty price of the bond.

        Examples
        --------
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.dirty_price(100.0, '2024-07-02')
        102.5
        """
        return clean_price + self.accrued_interest(settlement_date)

    @abstractmethod
    def accrued_interest(
        self, settlement_date: Optional[Union[str, pd.Timestamp]] = None
    ) -> float:  # pragma: no cover
        pass

    def effective_duration(
        self,
        yield_to_maturity: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> float:
        """
        Calculate effective duration of the bond.

        .. math::
            \\text{Effective Duration} = -\\frac{(P_{+} - P_{-})}{2 \\cdot \\epsilon \\cdot P}

        where:

        - :math:`P` is the price of the bond
        - :math:`P_{+}` is the price if yield increases by :math:`\\epsilon`
        - :math:`P_{-}` is the price if yield decreases by :math:`\\epsilon`
        - :math:`\\epsilon` is a small change in yield

        The times to payments are calculated from the settlement date to each payment date and need not be integer values.

        Parameters
        ----------
        yield_to_maturity : float, optional
            Yield to maturity as a decimal. If not provided, will be calculated from price if given.
        price : float, optional
            Price of the bond. Used to estimate YTM if yield_to_maturity is not provided.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.

        Returns
        -------
        duration : float
            Effective duration in years.

        Examples
        --------
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 2)
        >>> bond.effective_duration(yield_to_maturity=0.05, settlement_date='2020-01-01')
        4.3760319684
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        ytm, price_calc = self._resolve_ytm_and_price(
            yield_to_maturity,
            price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        if ytm is None or price_calc is None:
            raise ValueError("Unable to determine yield to maturity.")

        time_to_payments = self._calculate_time_to_payments(
            settlement_date,
            price=None,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        # Calculate effective duration using a small epsilon
        epsilon = 0.0000001
        price_plus_epsilon = self._price_from_yield(
            yield_to_maturity=ytm + epsilon,
            time_to_payments=time_to_payments,
            yield_calculation_convention=yield_calculation_convention,
        )
        price_minus_epsilon = self._price_from_yield(
            yield_to_maturity=ytm - epsilon,
            time_to_payments=time_to_payments,
            yield_calculation_convention=yield_calculation_convention,
        )

        effective_duration = (
            -1 * (price_plus_epsilon - price_minus_epsilon) / (2 * epsilon * price_calc)
        )
        return round(effective_duration, 10)

    def spread_effective_duration(
        self,
        yield_to_maturity: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> float:
        """
        Calculate spread effective duration of the bond.

        .. math::
            \\text{Spread Effective Duration} = -\\frac{(P_{+} - P_{-})}{2 \\cdot \\epsilon \\cdot P}

        where:

        - :math:`P` is the price of the bond
        - :math:`P_{+}` is the price if yield increases by :math:`\\epsilon`
        - :math:`P_{-}` is the price if yield decreases by :math:`\\epsilon`
        - :math:`\\epsilon` is a small change in yield

        The times to payments are calculated from the settlement date to each payment date and need not be integer values.

        Parameters
        ----------
        yield_to_maturity : float, optional
            Yield to maturity as a decimal. If not provided, will be calculated from price if given.
        price : float, optional
            Price of the bond. Used to estimate YTM if yield_to_maturity is not provided.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.

        Returns
        -------
        duration : float
            Effective duration in years.

        Examples
        --------
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 2)
        >>> bond.spread_effective_duration(yield_to_maturity=0.05, settlement_date='2020-01-01')
        4.3760319684
        """
        return self.effective_duration(
            yield_to_maturity=yield_to_maturity,
            price=price,
            settlement_date=settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            day_count_convention=day_count_convention,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
        )

    def effective_convexity(
        self,
        yield_to_maturity: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> float:
        """
        Calculate the effective convexity of the bond.

        .. math::
            \text{Effective Convexity} = \frac{P_{+} + P_{-} - 2P}{\\epsilon^2 P}

        where:

        - :math:`P` is the price of the bond
        - :math:`P_{+}` is the price if yield increases by :math:`\\epsilon`
        - :math:`P_{-}` is the price if yield decreases by :math:`\\epsilon`
        - :math:`\\epsilon` is a small change in yield

        The times to payments are calculated from the settlement date to each payment date and need not be integer values.

        Parameters
        ----------
        yield_to_maturity : float, optional
            Yield to maturity as a decimal. If not provided, will be calculated from price if given.
        price : float, optional
            Price of the bond. Used to estimate YTM if yield_to_maturity is not provided.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.

        Returns
        -------
        convexity : float
            Bond effective convexity.

        Examples
        --------
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 2)
        >>> bond.effective_convexity(yield_to_maturity=0.05) # doctest: +ELLIPSIS
        22.61232265...
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        ytm, price_calc = self._resolve_ytm_and_price(
            yield_to_maturity,
            price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        if ytm is None or price_calc is None:
            raise ValueError("Unable to determine yield to maturity.")

        time_to_payments = self._calculate_time_to_payments(
            settlement_date,
            price=None,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        # Calculate effective convexity using a small epsilon
        epsilon = 0.001
        price_plus_epsilon = self._price_from_yield(
            yield_to_maturity=ytm + epsilon,
            time_to_payments=time_to_payments,
            yield_calculation_convention=yield_calculation_convention,
        )
        price_minus_epsilon = self._price_from_yield(
            yield_to_maturity=ytm - epsilon,
            time_to_payments=time_to_payments,
            yield_calculation_convention=yield_calculation_convention,
        )
        expected_convexity = (
            price_plus_epsilon + price_minus_epsilon - 2 * price_calc
        ) / (epsilon**2 * price_calc)
        return expected_convexity

    def g_spread(
        self,
        benchmark_ytm: Optional[float] = None,
        benchmark_curve: Optional[YieldCurveBase] = None,
        yield_to_maturity: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> float:
        """
        Calculate the G-spread of the bond relative to a benchmark yield.

        The benchmark yield is the yield of a government bond that matches the maturity of the bond.

        If a benchmark curve is provided, the benchmark yield will be derived from the curve.

        G-spread = Bond YTM - Benchmark YTM

        Parameters
        ----------
        benchmark_ytm : float
            Yield to maturity of the government benchmark bond (in decimal, e.g., 0.03 for 3%).
        benchmark_curve : YieldCurveBase
            The benchmark yield curve to use for the G-spread calculation.
        yield_to_maturity : float, optional
            Yield to maturity of the bond. Used to estimate YTM if not set.
        price : float, optional
            Price of the bond. Used to estimate YTM if not set.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.

        Returns
        -------
        g_spread : float
            The G-spread in decimal (e.g., 0.0125 for 1.25%).

        Examples
        --------
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 2)
        >>> bond.g_spread(benchmark_ytm=0.03, price=100)
        np.float64(0.02)
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        if benchmark_ytm is None:
            if benchmark_curve is not None:
                benchmark_ytm = benchmark_curve.date_rate(
                    date=self.maturity,
                    yield_calculation_convention=yield_calculation_convention,
                )
            else:
                raise ValueError(
                    "Either benchmark_ytm or benchmark_curve must be provided."
                )

        ytm, price = self._resolve_ytm_and_price(
            yield_to_maturity,
            price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        if ytm is None:
            raise ValueError(
                "Unable to resolve yield to maturity. You must input settlement_date and either yield_to_maturity or price. Previous information was not available."
            )

        return round((ytm - benchmark_ytm), 10)

    def i_spread(
        self,
        benchmark_curve: YieldCurveBase,
        yield_to_maturity: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> float:
        """
        Calculate the I-spread of the bond relative to a benchmark yield curve.

        The I-spread is the difference between the bond's yield and the swap rate for the same maturity.

        The benchmark swap curve must be provided.

        I-spread = Bond YTM - Benchmark Swap Rate

        Parameters
        ----------
        benchmark_curve : YieldCurveBase, optional
            The benchmark yield curve to use for the I-spread calculation.
        yield_to_maturity : float, optional
            Yield to maturity of the bond. Used to estimate YTM if not set.
        price : float, optional
            Price of the bond. Used to estimate YTM if not set.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.

        Returns
        -------
        i_spread : float
            The I-spread in decimal (e.g., 0.0125 for 1.25%).

        Examples
        --------
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 1)
        >>> bond.i_spread(benchmark_curve=swap_curve) # doctest: +SKIP
        0.0185
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        benchmark_ytm = benchmark_curve.date_rate(
            date=self.maturity,
            yield_calculation_convention=yield_calculation_convention,
        )

        ytm, price = self._resolve_ytm_and_price(
            yield_to_maturity,
            price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )
        if ytm is None:
            raise ValueError(
                "Unable to resolve yield to maturity. You must input settlement_date and either yield_to_maturity or price. Previous information was not available."
            )

        return ytm - benchmark_ytm

    def z_spread(
        self,
        benchmark_curve: YieldCurveBase,
        yield_to_maturity: Optional[float] = None,
        price: Optional[float] = None,
        settlement_date: Optional[Union[str, pd.Timestamp]] = None,
        adjust_to_business_days: Optional[bool] = None,
        day_count_convention: Optional[str | DayCountBase] = None,
        following_coupons_day_count: Optional[str | DayCountBase] = None,
        yield_calculation_convention: Optional[str] = None,
    ) -> float:
        """
        Calculate the Z-spread of the bond relative to a benchmark yield curve.

        The Z-spread is the constant spread that, when added to the benchmark yield curve, makes the present value of the bond's cash flows equal to its market price.

        The benchmark curve must be provided.

        The Z-spread is calculated by solving the equation:

        .. math::
            P = \\sum_{t=1}^{T} \\frac{C_t}{(1 + YTM + Z)^{(t+1)}}

        where:

        - :math:`P` is the price of the bond
        - :math:`C_t` is the cash flow at time :math:`t`, where :math:`t` is the time in years from the settlement date
        - :math:`YTM` is the yield to maturity
        - :math:`T` is the total number of periods
        - :math:`Z` is the Z-spread

        The times to payments are calculated from the settlement date to each payment date and need not be integer values.

        Parameters
        ----------
        benchmark_curve : YieldCurveBase, optional
            The benchmark yield curve to use for the Z-spread calculation.
        yield_to_maturity : float, optional
            Yield to maturity of the bond. Used to estimate YTM if not set.
        price : float, optional
            Price of the bond. Used to estimate YTM if not set.
        settlement_date : str or datetime-like, optional
            Settlement date. Defaults to issue date.
        adjust_to_business_days : bool, optional
            Whether to adjust payment dates to business days. Defaults to value of self.adjust_to_business_days.
        day_count_convention : str or DayCountBase, optional
            Day count convention. Defaults to value of self.day_count_convention.
        following_coupons_day_count : str or DayCountBase, optional
            Day count convention for following coupons. Defaults to value of self.following_coupons_day_count.
        yield_calculation_convention : str, optional
            Yield calculation convention. Defaults to value of self.yield_calculation_convention.

        Returns
        -------
        z_spread : float
            The Z-spread in decimal (e.g., 0.0125 for 1.25%).

        Examples
        --------
        >>> from pyfian.yield_curves.flat_curve import FlatCurveBEY
        >>> bond = FixedRateBullet('2020-01-01', '2025-01-01', 5, 2, price=100, settlement_date="2020-01-01")
        >>> bond.z_spread(benchmark_curve=FlatCurveBEY(0.05, '2020-01-01'))
        np.float64(1.9484576898804107e-16)
        """
        settlement_date = self._resolve_settlement_date(settlement_date)
        (
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        ) = self._resolve_valuation_parameters(
            adjust_to_business_days,
            day_count_convention,
            following_coupons_day_count,
            yield_calculation_convention,
        )

        # benchmark_ytm = benchmark_curve.date_rate(date=self.maturity, yield_calculation_convention=yield_calculation_convention)
        ytm, price_calc = self._resolve_ytm_and_price(
            yield_to_maturity,
            price,
            settlement_date,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        date_of_payments = self._filter_payment_flow(
            settlement_date,
            price,
            payment_flow=self.payment_flow,
            adjust_to_business_days=adjust_to_business_days,
            following_coupons_day_count=following_coupons_day_count,
            yield_calculation_convention=yield_calculation_convention,
            day_count_convention=day_count_convention,
        )

        if price_calc is None:
            raise ValueError(
                "Unable to resolve yield to maturity. You must input settlement_date and either yield_to_maturity or price. Previous information was not available."
            )

        def _price_difference(z_spread):
            return (
                sum(
                    benchmark_curve.discount_date(d, z_spread) * value
                    for d, value in date_of_payments.items()
                )
                - price_calc
            )

        # use scipy to target _price_difference equal to 0
        z_spread = optimize.root_scalar(_price_difference, x0=0, method="newton").root

        return z_spread
