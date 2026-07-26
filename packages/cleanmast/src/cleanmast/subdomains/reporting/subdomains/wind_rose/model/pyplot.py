"""Matplotlib pyplot configured for headless CJK rendering.

Forces the Agg backend before pyplot is imported — matplotlib locks its
backend on the first pyplot import, so ``matplotlib.use("Agg")`` must run
first. Sets Chinese-capable fonts once here instead of in every atom.

All wind_rose model atoms import pyplot from this module:
``from cleanmast.subdomains.reporting.subdomains.wind_rose.model.pyplot import plt``
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

__all__ = ["plt"]
