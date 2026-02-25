"""Templated section implementation using Jinja2."""

from dataclasses import dataclass
from pathlib import Path

import jinja2

from ..protocols import Section
from ..collection import AtomCollection
from ..atoms.single_mast.monthly_wind import SingleMastMonthlyWindAtom
from ..atoms.single_mast.monthly_wind_power import SingleMastMonthlyWindPowerAtom
from ..atoms.single_mast.wind_rose import (
    SingleMastMonthlyWindFrequencyRoseAtom,
    SingleMastWindPowerRoseAtom,
)

WIND_SPEED_POWER_TEMPLATE = """
== {{ title }}

{% set summaries = [] %}
{% for mast in atoms.masts %}
{% set atom = atoms.get(mast, SingleMastMonthlyWindAtom) %}
{% if atom %}
{% set _ = summaries.append(atom.renderSummary()) %}
{% endif %}
{% endfor %}

{{ summaries | join(' ') }}

{% for mast in atoms.masts %}
{% set wind = atoms.get(mast, SingleMastMonthlyWindAtom) %}
{% set power = atoms.get(mast, SingleMastMonthlyWindPowerAtom) %}
{% if wind %}
{{ wind.renderImageTypst(images_dir) }}
{% endif %}
{% if power %}
{{ power.renderImageTypst(images_dir) }}
{% endif %}
{% endfor %}

{% for mast in atoms.masts %}
{% set wind = atoms.get(mast, SingleMastMonthlyWindAtom) %}
{% set power = atoms.get(mast, SingleMastMonthlyWindPowerAtom) %}
{% if wind %}
{{ wind.renderTable() }}
{% endif %}
{% if power %}
{{ power.renderTable() }}
{% endif %}
{% endfor %}
"""


@dataclass(frozen=True)
class TemplatedSection:
    """Section using Jinja2 template for rendering."""

    title: str
    level: int
    template: str
    atoms: AtomCollection

    def render(self, images_dir: Path) -> str:
        env = jinja2.Environment()
        template = env.from_string(self.template)

        context = {
            "title": self.title,
            "level": self.level,
            "atoms": self.atoms,
            "images_dir": images_dir,
            "SingleMastMonthlyWindAtom": SingleMastMonthlyWindAtom,
            "SingleMastMonthlyWindPowerAtom": SingleMastMonthlyWindPowerAtom,
            "SingleMastMonthlyWindFrequencyRoseAtom": SingleMastMonthlyWindFrequencyRoseAtom,
            "SingleMastWindPowerRoseAtom": SingleMastWindPowerRoseAtom,
        }

        return template.render(context)
