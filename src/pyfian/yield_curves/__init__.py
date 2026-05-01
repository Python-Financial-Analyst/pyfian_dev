"""Yield curves: flat, zero-coupon, spot, par, interpolated, credit-spread, combined.

The base classes :class:`CurveBase` and :class:`YieldCurveBase` define the
abstract interface for all curve types. Concrete curves include flat curves
(:class:`FlatCurveAER`, :class:`FlatCurveBEY`, :class:`FlatCurveLog`),
zero-coupon curves (:class:`ZeroCouponCurve`, :class:`ZeroCouponCurveByDate`),
bootstrap-style curves (:class:`SpotCurve`, :class:`ParCurve`,
:class:`InterpolatedCurve`, :class:`CombinedCurve`), and credit-spread
overlays (:class:`CreditSpreadCurve`, :class:`FlatCreditSpreadCurve`).

The bond-dependent curves (``SpotCurve``, ``ParCurve``, ``CombinedCurve``,
``CreditSpreadCurve``, ``FlatCreditSpreadCurve``, ``InterpolatedCurve``,
``ZeroCouponCurve``) are imported lazily through PEP 562 ``__getattr__``
to avoid a circular import with :mod:`pyfian.fixed_income`. They are still
listed in ``__all__`` and importable as attributes
(``from pyfian.yield_curves import ParCurve``) and as submodules
(``from pyfian.yield_curves.par_curve import ParCurve``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Eager imports: leaves with no dependency on pyfian.fixed_income.
from pyfian.yield_curves.base_curve import MATURITIES, CurveBase, YieldCurveBase
from pyfian.yield_curves.flat_curve import FlatCurveAER, FlatCurveBEY, FlatCurveLog

# Lazy imports: these submodules transitively depend on
# pyfian.fixed_income.fixed_rate_bond, which depends on
# pyfian.yield_curves.base_curve. Loading them eagerly during package
# init would deadlock the import graph.
_LAZY_IMPORTS = {
    "ZeroCouponCurve": "pyfian.yield_curves.zero_coupon_curve",
    "ZeroCouponCurveByDate": "pyfian.yield_curves.zero_coupon_curve",
    "InterpolatedCurve": "pyfian.yield_curves.interpolated_curve",
    "SpotCurve": "pyfian.yield_curves.spot_curve",
    "ParCurve": "pyfian.yield_curves.par_curve",
    "CreditSpreadCurve": "pyfian.yield_curves.credit_spread",
    "CreditSpreadCurveBase": "pyfian.yield_curves.credit_spread",
    "FlatCreditSpreadCurve": "pyfian.yield_curves.credit_spread",
    "CombinedCurve": "pyfian.yield_curves.curve_combination",
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name])
        attr = getattr(module, name)
        globals()[name] = attr
        return attr
    raise AttributeError(f"module 'pyfian.yield_curves' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__))


if TYPE_CHECKING:  # pragma: no cover - for static analysers and IDEs
    from pyfian.yield_curves.credit_spread import (
        CreditSpreadCurve,
        CreditSpreadCurveBase,
        FlatCreditSpreadCurve,
    )
    from pyfian.yield_curves.curve_combination import CombinedCurve
    from pyfian.yield_curves.interpolated_curve import InterpolatedCurve
    from pyfian.yield_curves.par_curve import ParCurve
    from pyfian.yield_curves.spot_curve import SpotCurve
    from pyfian.yield_curves.zero_coupon_curve import (
        ZeroCouponCurve,
        ZeroCouponCurveByDate,
    )

__all__ = [
    "MATURITIES",
    "CombinedCurve",
    "CreditSpreadCurve",
    "CreditSpreadCurveBase",
    "CurveBase",
    "FlatCreditSpreadCurve",
    "FlatCurveAER",
    "FlatCurveBEY",
    "FlatCurveLog",
    "InterpolatedCurve",
    "ParCurve",
    "SpotCurve",
    "YieldCurveBase",
    "ZeroCouponCurve",
    "ZeroCouponCurveByDate",
]
