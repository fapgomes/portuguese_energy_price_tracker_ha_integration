"""Tests for composing interval prices (formula + TAR + TSE)."""
from __future__ import annotations

import pytest

from pept.pricing import TariffFlags, build_aggregates, compute_day

C = {
    "TAR_Energia_Simples": 0.06, "TAR_Energia_Bi_Vazio": 0.015, "TAR_Energia_Bi_ForaVazio": 0.08,
    "TAR_Energia_Tri_Vazio": 0.016, "TAR_Energia_Tri_Cheias": 0.04, "TAR_Energia_Tri_Ponta": 0.25,
    "TAR_Energia_Tri_27.6_Vazio": 0.0151, "TAR_Energia_Tri_27.6_Cheias": 0.0521,
    "TAR_Energia_Tri_27.6_Ponta": 0.2451, "Financiamento_TSE": 0.002,
    "EDP_H_K1": 1.0, "EDP_H_K2": 0.01, "EDP_M_Perdas": 1.0, "EDP_M_K1": 1.0, "EDP_M_K2": 0.01,
    "Endesa_A_S": 0.1, "Endesa_A_V": 0.07, "Endesa_A_FV": 0.13,
    "Luzboa_CGS": 0.0, "Luzboa_FA": 1.0, "Luzboa_Kp": 0.0,
    "Luzigas_K": 0.0, "Luzigas_CGS": 0.0,
}
NONE = TariffFlags(tse_included=False, tar_included=False)


def row(date, hora, omie, perdas=1.0, bd="V", td="V"):
    return {"Data": date, "Hora": hora, "OMIE": str(omie), "Perdas": str(perdas),
            "Simp": "S", "BD": bd, "BS": bd, "TD": td, "TS": td}


# Two days in October: day 1 cheap, day 2 expensive
DAY1 = [row("10/01/2026", "00:00", 10, bd="V", td="V"), row("10/01/2026", "12:00", 30, bd="F", td="P")]
DAY2 = [row("10/02/2026", "00:00", 50, bd="V", td="V"), row("10/02/2026", "12:00", 110, bd="F", td="C")]
YEAR = DAY1 + DAY2


def test_build_aggregates_month_to_date():
    agg = build_aggregates(DAY1 + DAY2, YEAR)
    assert agg["OMIE_S_M"] == pytest.approx((10 + 30 + 50 + 110) / 4)
    assert agg["OMIE_BD_M_V"] == pytest.approx((10 + 50) / 2)
    assert agg["OMIE_BD_M_F"] == pytest.approx((30 + 110) / 2)
    assert agg["OMIE_TD_M_P"] == pytest.approx(30)
    assert agg["Perdas_Anual_S"] == pytest.approx(1.0)
    assert agg["Perdas_Anual_TD_C"] == pytest.approx(1.0)


def test_quarter_hourly_simple_adds_tar_and_tse():
    out = compute_day("EDP | Eletricidade Indexada Horária", "SIMPLE", DAY2, DAY1 + DAY2, YEAR, C, NONE)
    first = out[0]
    assert first["period"] == "S"
    assert first["provider_price"] == pytest.approx(0.05 + 0.01)
    assert first["tar_cost"] == pytest.approx(0.06)
    assert first["price"] == pytest.approx(0.06 + 0.06 + 0.002)
    assert first["spot_price"] is None


def test_tse_included_flag_skips_tse():
    flags = TariffFlags(tse_included=True, tar_included=False)
    out = compute_day("EDP | Eletricidade Indexada Horária", "SIMPLE", DAY2, DAY1 + DAY2, YEAR, C, flags)
    assert out[0]["price"] == pytest.approx(0.06 + 0.06)


def test_tar_by_period_bihorario_and_trihorario():
    bi = compute_day("EDP | Eletricidade Indexada Horária", "BIHORARIO_DIARIO", DAY2, DAY1 + DAY2, YEAR, C, NONE)
    assert [p["period"] for p in bi] == ["V", "F"]
    assert [p["tar_cost"] for p in bi] == [0.015, 0.08]
    tri = compute_day("EDP | Eletricidade Indexada Horária", "TRIHORARIO_DIARIO", DAY2, DAY1 + DAY2, YEAR, C, NONE)
    assert [p["tar_cost"] for p in tri] == [0.016, 0.04]
    hv = compute_day("EDP | Eletricidade Indexada Horária", "TRIHORARIO_DIARIO_HV", DAY2, DAY1 + DAY2, YEAR, C, NONE)
    assert [p["tar_cost"] for p in hv] == [0.0151, 0.0521]


def test_monthly_average_uses_mean_and_exposes_spot():
    out = compute_day("EDP | Eletricidade Indexada Média", "SIMPLE", DAY2, DAY1 + DAY2, YEAR, C, NONE)
    mean = (10 + 30 + 50 + 110) / 4 / 1000
    assert [p["provider_price"] for p in out] == pytest.approx([mean + 0.01] * 2)
    assert out[0]["spot_price"] == pytest.approx(0.05 + 0.01 + 0.06 + 0.002)
    assert out[1]["spot_price"] == pytest.approx(0.11 + 0.01 + 0.06 + 0.002)


def test_monthly_average_by_period():
    out = compute_day("EDP | Eletricidade Indexada Média", "BIHORARIO_DIARIO", DAY2, DAY1 + DAY2, YEAR, C, NONE)
    assert out[0]["provider_price"] == pytest.approx((10 + 50) / 2 / 1000 + 0.01)
    assert out[1]["provider_price"] == pytest.approx((30 + 110) / 2 / 1000 + 0.01)


def test_month_to_date_excludes_future_days():
    """Day 1 must not see day 2's OMIE in its average."""
    out = compute_day("EDP | Eletricidade Indexada Média", "SIMPLE", DAY1, DAY1, YEAR, C, NONE)
    assert out[0]["provider_price"] == pytest.approx((10 + 30) / 2 / 1000 + 0.01)


def test_tar_included_is_not_added_twice():
    flags = TariffFlags(tse_included=True, tar_included=True)
    out = compute_day("Endesa | Tarifa Indexada", "BIHORARIO_DIARIO", DAY2, DAY1 + DAY2, YEAR, C, flags)
    v_formula = (10 + 50) / 2 / 1000 + 0.07
    assert out[0]["price"] == pytest.approx(v_formula)
    assert out[0]["provider_price"] == pytest.approx(v_formula - 0.015)
    assert out[0]["tar_cost"] == pytest.approx(0.015)


def test_luzboa_mean_of_intervals_per_period():
    out = compute_day("Luzboa | BTN SPOTDEF", "BIHORARIO_DIARIO", DAY2, DAY1 + DAY2, YEAR, C, NONE)
    assert out[0]["provider_price"] == pytest.approx((0.01 + 0.05) / 2)
    assert out[1]["provider_price"] == pytest.approx((0.03 + 0.11) / 2)
    assert out[1]["spot_price"] == pytest.approx(0.11 + 0.08 + 0.002)


def test_luzigas_uses_simple_mean_for_every_period():
    out = compute_day("LUZiGÁS | Super Lig Index", "BIHORARIO_DIARIO", DAY2, DAY1 + DAY2, YEAR, C, NONE)
    mean_s = (10 + 30 + 50 + 110) / 4 / 1000
    assert [p["provider_price"] for p in out] == pytest.approx([mean_s, mean_s])


def test_missing_constant_propagates():
    c = dict(C)
    del c["EDP_H_K2"]
    with pytest.raises(KeyError):
        compute_day("EDP | Eletricidade Indexada Horária", "SIMPLE", DAY2, DAY1 + DAY2, YEAR, c, NONE)
