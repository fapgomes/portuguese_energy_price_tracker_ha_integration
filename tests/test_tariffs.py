"""Tests for the per-provider energy formulas."""
from __future__ import annotations

import pytest

from conftest import load_providers
from pept.tariffs import (
    MONTHLY_AVERAGE,
    MONTHLY_MEAN_OF_INTERVALS,
    QUARTER_HOURLY,
    TARIFFS,
    Inputs,
)

PROVIDERS = load_providers()["PROVIDERS"]

# Periods each tariff code can produce, and the cycle column it reads
CODE_PERIODS = {
    "SIMPLE": ("S", ["S"]),
    "BIHORARIO_DIARIO": ("BD", ["V", "F"]),
    "BIHORARIO_SEMANAL": ("BS", ["V", "F"]),
    "TRIHORARIO_DIARIO": ("TD", ["V", "C", "P"]),
    "TRIHORARIO_SEMANAL": ("TS", ["V", "C", "P"]),
    "TRIHORARIO_DIARIO_HV": ("TD", ["V", "C", "P"]),
    "TRIHORARIO_SEMANAL_HV": ("TS", ["V", "C", "P"]),
}

AGG = {"OMIE_S_M": 80.0, "Perdas_Anual_S": 1.15}
for _cycle, _periods in (("BD", "VF"), ("BS", "VF"), ("TD", "VCP"), ("TS", "VCP")):
    for _p in _periods:
        AGG[f"Perdas_Anual_{_cycle}_{_p}"] = 1.1


def inputs(c, omie=0.1, perdas=1.2, period="S", cycle="S", month=10, agg=AGG):
    return Inputs(omie=omie, perdas=perdas, period=period, cycle=cycle, month=month, agg=agg, c=c)


def test_every_provider_has_a_tariff():
    assert set(PROVIDERS) == set(TARIFFS)


def test_kinds_are_known():
    for name, tariff in TARIFFS.items():
        assert tariff.kind in (QUARTER_HOURLY, MONTHLY_AVERAGE, MONTHLY_MEAN_OF_INTERVALS), name


@pytest.mark.parametrize(
    "provider,code",
    [(p, code) for p, info in PROVIDERS.items() for code in info["tariffs"]],
)
def test_every_option_evaluates_with_published_constants(constants, provider, code):
    """Every constant a formula reads must exist in Constantes.csv."""
    cycle, periods = CODE_PERIODS[code]
    for period in periods:
        value = TARIFFS[provider].energy(inputs(constants, period=period, cycle=cycle))
        assert isinstance(value, float)
        assert 0 < value < 1, (provider, code, period, value)


def test_missing_constant_raises(constants):
    c = dict(constants)
    del c["Iberdrola_mFRR"]
    with pytest.raises(KeyError):
        TARIFFS["Iberdrola | Simples Indexado"].energy(inputs(c))


# Hand-computed values from the calculos.py formulas, with fixed constants
C = {
    "Iberdrola_Perdas": 1.2, "Iberdrola_Media_Q": 0.025, "Iberdrola_Dinamico_Q": 0.03,
    "Iberdrola_mFRR": 0.002, "EDP_H_K1": 1.08, "EDP_H_K2": 0.0185, "EDP_M_Perdas": 1.164,
    "EDP_M_K1": 1.1, "EDP_M_K2": 0.0185, "Endesa_A_S": 0.11, "Endesa_A_V": 0.07,
    "Endesa_A_FV": 0.13, "GE_Q_Tarifa": 0.024, "GE_CG": 0.005, "Coop_CS": 0.0138,
    "Coop_K": 0.009, "G9_K1": 1.02, "G9_K2": 0.016, "G9_K3": 0.008, "Luzigas_K": 0.005,
    "Luzigas_CGS": 0.0138, "Ibelectra_CS": 0.009, "Ibelectra_Perdas": 1.1639,
    "Ibelectra_K": 0.0035, "Ibelectra_K_a": 0.0055, "Luzboa_CGS": 0.0138,
    "Luzboa_FA": 1.02, "Luzboa_Kp": 0.005,
}


@pytest.mark.parametrize(
    "provider,kwargs,expected",
    [
        ("Iberdrola | Simples Indexado", {}, 0.1 * 1.2 + 0.025 + 0.002),
        ("Iberdrola | Simples Indexado Dinâmico", {}, 0.1 * 1.2 + 0.03 + 0.002),
        ("EDP | Eletricidade Indexada Horária", {}, 0.1 * 1.2 * 1.08 + 0.0185),
        ("EDP | Eletricidade Indexada Média", {}, 0.1 * 1.164 * 1.1 + 0.0185),
        ("Endesa | Tarifa Indexada", {}, 0.1 + 0.11),
        ("Endesa | Tarifa Indexada", {"period": "V", "cycle": "BD"}, 0.1 + 0.07),
        ("Endesa | Tarifa Indexada", {"period": "F", "cycle": "BD"}, 0.1 + 0.13),
        ("Goldenergy | Tarifário Indexado 100%", {"month": 10}, 0.1 * 1.10 + 0.024 + 0.005),
        ("Goldenergy | Tarifário Indexado 100%", {"month": 1}, 0.1 * 1.29 + 0.024 + 0.005),
        ("Coopérnico | Único", {}, (0.1 + 0.0138) * 1.2 + 0.009),
        ("G9 | Smart Dynamic SPOT 8!", {}, 0.1 * 1.02 * 1.2 + 0.016 + 0.008),
        ("LUZiGÁS | Super Lig Index", {}, (0.1 + 0.005 + 0.0138) * 1.15),
        ("LUZiGÁS | Super Lig Index", {"period": "V", "cycle": "BD"}, (0.1 + 0.005 + 0.0138) * 1.1),
        ("Ibelectra | Solução Família", {}, (0.1 + 0.009) * 1.1639 + 0.0035),
        ("Ibelectra | Solução Amigo", {}, (0.1 + 0.009) * 1.1639 + 0.0055),
        ("Luzboa | BTN SPOTDEF", {}, (0.1 + 0.0138) * 1.2 * 1.02 + 0.005),
    ],
)
def test_formula_values(provider, kwargs, expected):
    assert TARIFFS[provider].energy(inputs(C, **kwargs)) == pytest.approx(expected)


def test_luzigas_uses_simple_average():
    assert TARIFFS["LUZiGÁS | Super Lig Index"].simple_average is True
    assert TARIFFS["EDP | Eletricidade Indexada Média"].simple_average is False
