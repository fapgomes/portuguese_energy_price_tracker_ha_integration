"""Compose interval prices: provider formula + TAR energy + TSE financing.

Mirrors how the upstream simulator builds the energy price of an indexed
tariff (calculos.py): the provider component comes from the tariff formula,
TAR energy for the interval's period is added on top, and TSE financing is
added unless the provider already includes it.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .tariffs import MONTHLY_AVERAGE, MONTHLY_MEAN_OF_INTERVALS, QUARTER_HOURLY, TARIFFS, Inputs

# Tariff code -> (cycle, OMIE CSV column holding the period of each interval)
CYCLES = {
    "SIMPLE": ("S", "Simp"),
    "BIHORARIO_DIARIO": ("BD", "BD"),
    "BIHORARIO_SEMANAL": ("BS", "BS"),
    "TRIHORARIO_DIARIO": ("TD", "TD"),
    "TRIHORARIO_SEMANAL": ("TS", "TS"),
    "TRIHORARIO_DIARIO_HV": ("TD", "TD"),
    "TRIHORARIO_SEMANAL_HV": ("TS", "TS"),
}

CYCLE_PERIODS = {"BD": "VF", "BS": "VF", "TD": "VCP", "TS": "VCP"}

TAR_BI = {"V": "TAR_Energia_Bi_Vazio", "F": "TAR_Energia_Bi_ForaVazio"}
TAR_TRI = {"V": "Vazio", "C": "Cheias", "P": "Ponta"}


@dataclass(frozen=True)
class TariffFlags:
    """Per-provider flags from Indexados.csv."""

    tse_included: bool = False  # financiamento_tse_incluido
    tar_included: bool = False  # tar_incluida_energia


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def build_aggregates(month_rows: list[dict], year_rows: list[dict]) -> dict[str, float]:
    """Mean OMIE (€/MWh) over month_rows and mean losses over year_rows, overall and per cycle period.

    Keys: OMIE_S_M, OMIE_{cycle}_M_{period}, Perdas_Anual_S, Perdas_Anual_{cycle}_{period}.
    """
    agg: dict[str, float] = {}
    for prefix, rows, field in (("OMIE", month_rows, "OMIE"), ("Perdas_Anual", year_rows, "Perdas")):
        overall: list[float] = []
        by_period: dict[str, list[float]] = defaultdict(list)
        for r in rows:
            try:
                value = float(r[field])
            except (KeyError, TypeError, ValueError):
                continue
            overall.append(value)
            for cycle in CYCLE_PERIODS:
                by_period[f"{cycle}_{(r.get(cycle) or '').strip()}"].append(value)

        simple_key = "OMIE_S_M" if prefix == "OMIE" else "Perdas_Anual_S"
        if (m := _mean(overall)) is not None:
            agg[simple_key] = m
        for cycle, periods in CYCLE_PERIODS.items():
            for p in periods:
                key = f"OMIE_{cycle}_M_{p}" if prefix == "OMIE" else f"Perdas_Anual_{cycle}_{p}"
                if (m := _mean(by_period[f"{cycle}_{p}"])) is not None:
                    agg[key] = m
    return agg


def tar_energy(tariff_code: str, period: str, constants: dict[str, float]) -> float:
    """TAR energy (€/kWh) for the period, as obter_tar_energia_periodo upstream."""
    if tariff_code == "SIMPLE":
        return constants["TAR_Energia_Simples"]
    if tariff_code.startswith("BIHORARIO"):
        return constants[TAR_BI[period]]
    infix = "Tri_27.6" if tariff_code.endswith("_HV") else "Tri"
    return constants[f"TAR_Energia_{infix}_{TAR_TRI[period]}"]


def _period(row: dict, column: str) -> str:
    return (row.get(column) or "S").strip()


def compute_day(
    tariff_name: str,
    tariff_code: str,
    day_rows: list[dict],
    month_rows: list[dict],
    year_rows: list[dict],
    constants: dict[str, float],
    flags: TariffFlags,
) -> list[dict[str, Any]]:
    """Price every interval in day_rows.

    month_rows must hold the month-to-date rows (1st of the month up to and
    including the day being priced); year_rows the whole calendar year.
    Raises KeyError when a required constant is missing.
    """
    tariff = TARIFFS[tariff_name]
    cycle, column = CYCLES[tariff_code]
    agg = build_aggregates(month_rows, year_rows)
    tse = 0.0 if flags.tse_included else constants["Financiamento_TSE"]

    def energy(row: dict, omie_kwh: float, month: int) -> float:
        return tariff.energy(Inputs(
            omie=omie_kwh,
            perdas=float(row["Perdas"]),
            period=_period(row, column),
            cycle=cycle,
            month=month,
            agg=agg,
            c=constants,
        ))

    def month_of(row: dict) -> int:
        return int((row.get("﻿Data") or row.get("Data", "")).strip().split("/")[0])

    # Luzboa: unweighted month-to-date mean of the per-interval formula, per period
    interval_means: dict[str, float] = {}
    if tariff.kind == MONTHLY_MEAN_OF_INTERVALS:
        by_period: dict[str, list[float]] = defaultdict(list)
        for r in month_rows:
            by_period[_period(r, column)].append(energy(r, float(r["OMIE"]) / 1000, month_of(r)))
        interval_means = {p: sum(v) / len(v) for p, v in by_period.items()}

    def compose(provider: float, tar: float) -> tuple[float, float]:
        """Return (provider component, full price) without VAT."""
        if flags.tar_included:
            return provider - tar, provider + tse
        return provider, provider + tar + tse

    results = []
    for row in day_rows:
        period = _period(row, column)
        month = month_of(row)
        omie_kwh = float(row["OMIE"]) / 1000
        tar = tar_energy(tariff_code, period, constants)

        if tariff.kind == MONTHLY_AVERAGE:
            key = "OMIE_S_M" if cycle == "S" or tariff.simple_average else f"OMIE_{cycle}_M_{period}"
            raw = energy(row, agg[key] / 1000, month)
        elif tariff.kind == MONTHLY_MEAN_OF_INTERVALS:
            raw = interval_means[period]
        else:
            raw = energy(row, omie_kwh, month)

        provider_price, price = compose(raw, tar)
        spot_price = None
        if tariff.kind != QUARTER_HOURLY:
            spot_price = compose(energy(row, omie_kwh, month), tar)[1]

        results.append({
            "period": period,
            "provider_price": provider_price,
            "tar_cost": tar,
            "price": price,
            "spot_price": spot_price,
        })
    return results
