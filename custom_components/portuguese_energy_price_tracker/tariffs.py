"""Energy formulas for each supported indexed tariff.

Each formula returns the provider component of the energy price (€/kWh),
without TAR, TSE financing or VAT. They are ported from the upstream
simulator (calculos.py in Tiago Felícia's HuggingFace space):

- Quarter-hourly tariffs: calcular_custo_completo_diagrama_carga
- Monthly average tariffs: calcular_detalhes_custo_tarifario_indexado

Constants are read with c[name] so that a constant missing from
Constantes.csv raises KeyError instead of silently becoming 0.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

# Price follows the OMIE of each 15-min interval
QUARTER_HOURLY = "quarter_hourly"
# Price uses the month-to-date mean OMIE of the interval's period
MONTHLY_AVERAGE = "monthly_average"
# Price is the month-to-date mean of the per-interval formula (Luzboa)
MONTHLY_MEAN_OF_INTERVALS = "monthly_mean_of_intervals"

# Goldenergy monthly losses factors (hard-coded upstream)
GE_PERDAS_MENSAIS = {
    1: 1.29, 2: 1.18, 3: 1.18, 4: 1.15, 5: 1.11, 6: 1.10,
    7: 1.15, 8: 1.13, 9: 1.10, 10: 1.10, 11: 1.16, 12: 1.25,
}

# Endesa constant suffix for each period
ENDESA_PERIOD = {"S": "S", "V": "V", "F": "FV"}


@dataclass(frozen=True)
class Inputs:
    """Values available to a formula for one interval."""

    omie: float  # €/kWh: interval OMIE, or the period mean for MONTHLY_AVERAGE
    perdas: float  # interval losses factor
    period: str  # S, V, F, C or P
    cycle: str  # S, BD, BS, TD or TS
    month: int
    agg: Mapping[str, float]  # aggregates from pricing.build_aggregates
    c: Mapping[str, float]  # constants from Constantes.csv


@dataclass(frozen=True)
class Tariff:
    """An indexed tariff and how its energy price is computed."""

    kind: str
    energy: Callable[[Inputs], float]
    # MONTHLY_AVERAGE only: use the Simples OMIE mean for every period
    simple_average: bool = False


def _annual_losses(i: Inputs) -> float:
    key = "Perdas_Anual_S" if i.cycle == "S" else f"Perdas_Anual_{i.cycle}_{i.period}"
    return i.agg[key]


TARIFFS: dict[str, Tariff] = {
    # Quarter-hourly
    "Alfa Energia | ALFA POWER INDEX BTN": Tariff(
        QUARTER_HOURLY,
        lambda i: (i.omie + i.c["Alfa_CGS"]) * i.perdas + i.c["Alfa_K"],
    ),
    "Coopérnico | Único": Tariff(
        QUARTER_HOURLY,
        lambda i: (i.omie + i.c["Coop_CS"]) * i.perdas + i.c["Coop_K"],
    ),
    "EDP | Eletricidade Indexada Horária": Tariff(
        QUARTER_HOURLY,
        lambda i: i.omie * i.perdas * i.c["EDP_H_K1"] + i.c["EDP_H_K2"],
    ),
    "EZU | Indexada": Tariff(
        QUARTER_HOURLY,
        lambda i: (i.omie + i.c["EZU_K"] + i.c["EZU_CGS"]) * i.perdas,
    ),
    "G9 | Smart Dynamic SPOT 8!": Tariff(
        QUARTER_HOURLY,
        lambda i: i.omie * i.c["G9_K1"] * i.perdas + i.c["G9_K2"] + i.c["G9_K3"],
    ),
    "Galp | Plano Flexível / Dinâmico": Tariff(
        QUARTER_HOURLY,
        lambda i: (i.omie + i.c["Galp_Ci"]) * i.perdas,
    ),
    "Iberdrola | Simples Indexado Dinâmico": Tariff(
        QUARTER_HOURLY,
        lambda i: i.omie * i.perdas + i.c["Iberdrola_Dinamico_Q"] + i.c["Iberdrola_mFRR"],
    ),
    "Meo Energia | Tarifa Dinâmica": Tariff(
        QUARTER_HOURLY,
        lambda i: (i.omie + i.c["Meo_K"]) * i.perdas,
    ),
    "Plenitude | Tendência": Tariff(
        QUARTER_HOURLY,
        lambda i: (i.omie + i.c["Plenitude_CGS"] + i.c["Plenitude_GDOs"]) * i.perdas
        + i.c["Plenitude_Fee"],
    ),
    "Repsol | Leve PRO Sem Mais": Tariff(
        QUARTER_HOURLY,
        lambda i: i.omie * i.perdas * i.c["Repsol_FA"] + i.c["Repsol_Q_Tarifa_Pro"],
    ),
    "Repsol | Leve Sem Mais": Tariff(
        QUARTER_HOURLY,
        lambda i: i.omie * i.perdas * i.c["Repsol_FA"] + i.c["Repsol_Q_Tarifa"],
    ),
    # Monthly mean of the per-interval formula
    "Luzboa | BTN SPOTDEF": Tariff(
        MONTHLY_MEAN_OF_INTERVALS,
        lambda i: (i.omie + i.c["Luzboa_CGS"]) * i.perdas * i.c["Luzboa_FA"] + i.c["Luzboa_Kp"],
    ),
    # Monthly average OMIE
    "EDP | Eletricidade Indexada Média": Tariff(
        MONTHLY_AVERAGE,
        lambda i: i.omie * i.c["EDP_M_Perdas"] * i.c["EDP_M_K1"] + i.c["EDP_M_K2"],
    ),
    "Endesa | Tarifa Indexada": Tariff(
        MONTHLY_AVERAGE,
        lambda i: i.omie + i.c[f"Endesa_A_{ENDESA_PERIOD[i.period]}"],
    ),
    "Goldenergy | Tarifário Indexado 100%": Tariff(
        MONTHLY_AVERAGE,
        lambda i: i.omie * GE_PERDAS_MENSAIS[i.month] + i.c["GE_Q_Tarifa"] + i.c["GE_CG"],
    ),
    "Ibelectra | Solução Amigo": Tariff(
        MONTHLY_AVERAGE,
        lambda i: (i.omie + i.c["Ibelectra_CS"]) * i.c["Ibelectra_Perdas"] + i.c["Ibelectra_K_a"],
    ),
    "Ibelectra | Solução Família": Tariff(
        MONTHLY_AVERAGE,
        lambda i: (i.omie + i.c["Ibelectra_CS"]) * i.c["Ibelectra_Perdas"] + i.c["Ibelectra_K"],
    ),
    "Iberdrola | Simples Indexado": Tariff(
        MONTHLY_AVERAGE,
        lambda i: i.omie * i.c["Iberdrola_Perdas"] + i.c["Iberdrola_Media_Q"] + i.c["Iberdrola_mFRR"],
    ),
    "LUZiGÁS | Super Lig Index": Tariff(
        MONTHLY_AVERAGE,
        lambda i: (i.omie + i.c["Luzigas_K"] + i.c["Luzigas_CGS"]) * _annual_losses(i),
        simple_average=True,
    ),
}
