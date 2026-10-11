"""Tests for HuggingFace fetching and the end-to-end price calculation."""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import pytest

from conftest import FIXTURES, TZ
from pept.csv_fetcher import CSVDataFetcher
from pept.hf_fetcher import HF_CONSTANTS_CSV, HF_INDEXADOS_CSV, HF_OMIE_CSV, HFDataFetcher
from pept.pricing import TariffFlags

INDEXADOS = (
    "﻿comercializador,nome,tipo,opcao_horaria_e_ciclo,potencia_kva,"
    "tar_incluida_energia,financiamento_tse_incluido\n"
    "EDP,EDP | Eletricidade Indexada Horária,Indexado quarto-horário,Simples,6.9,False,True\n"
    "EDP,EDP | Eletricidade Indexada Horária,Indexado quarto-horário,"
    "\"Bi-horário - Ciclo Diário, Bi-horário - Ciclo Semanal\",6.9,False,True\n"
    "Endesa,Endesa | Tarifa Indexada,Indexado Média,Simples,6.9,True,True\n"
    "Iberdrola,Iberdrola | Simples Indexado,Indexado Média,Simples,6.9,False,False\n"
)

OMIE_HEADER = "﻿Data,Hora,Simp,BD,BS,TD,TS,BTN_A,BTN_B,BTN_C,OMIE,Perdas,ERC\n"


def omie_csv() -> str:
    lines = [OMIE_HEADER]
    for day, omie in ((1, 40.0), (2, 80.0), (3, 500.0)):
        for hh in range(24):
            for mm in (0, 15, 30, 45):
                period = "V" if hh < 8 else "F"
                lines.append(
                    f"10/{day:02d}/2026,{hh:02d}:{mm:02d},S,{period},{period},{period},{period},"
                    f"0.03,0.03,0.03,{omie},1.1,1\n"
                )
    return "".join(lines)


class FakeResponse:
    def __init__(self, body: str):
        self.status = 200
        self._body = body

    async def text(self):
        return self._body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None


class FakeSession:
    def __init__(self):
        self.bodies = {
            HF_INDEXADOS_CSV: INDEXADOS,
            HF_CONSTANTS_CSV: (FIXTURES / "Constantes.csv").read_text(encoding="utf-8"),
            HF_OMIE_CSV: omie_csv(),
        }
        self.urls: list[str] = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        return FakeResponse(self.bodies[url])


def run(coro):
    return asyncio.run(coro)


def test_fetch_tariff_flags(tmp_path: Path):
    flags = run(HFDataFetcher(FakeSession(), tmp_path).fetch_tariff_flags())
    assert flags["EDP | Eletricidade Indexada Horária"] == TariffFlags(tse_included=True, tar_included=False)
    assert flags["Endesa | Tarifa Indexada"] == TariffFlags(tse_included=True, tar_included=True)
    assert flags["Iberdrola | Simples Indexado"] == TariffFlags()


def test_month_to_date_and_year_rows(tmp_path: Path):
    hf = HFDataFetcher(FakeSession(), tmp_path)
    run(hf.load_omie_data())
    rows = hf.get_month_to_date_rows(datetime(2026, 10, 2))
    assert len(rows) == 2 * 96
    assert len(hf.get_year_rows(2026)) == 3 * 96


def test_get_prices_end_to_end(tmp_path: Path):
    fetcher = CSVDataFetcher(FakeSession(), tmp_path)
    prices = run(fetcher.get_prices(
        "Iberdrola | Simples Indexado", "SIMPLE", 23, target_date=datetime(2026, 10, 2, tzinfo=TZ)
    ))
    assert len(prices) == 96
    p = prices[0]
    assert p["datetime"].startswith("2026-10-02T00:00:00")
    assert p["interval"] == "[00:00-00:15["
    assert p["period"] == "S"
    assert p["market_price"] == pytest.approx(0.08)
    assert p["tar_cost"] == pytest.approx(0.0607)
    # Month-to-date mean of days 1-2 (60 €/MWh), day 3 is in the future
    expected_provider = 0.06 * 1.1674 + 0.025 + 0.00194
    assert p["provider_price"] == pytest.approx(expected_provider, abs=1e-5)
    expected_price = expected_provider + 0.0607 + 0.0020666
    assert p["price"] == pytest.approx(expected_price, abs=1e-5)
    assert p["price_w_vat"] == pytest.approx(expected_price * 1.23, abs=1e-5)
    assert p["spot_price"] == pytest.approx(0.08 * 1.1674 + 0.025 + 0.00194 + 0.0607 + 0.0020666, abs=1e-5)


def test_get_prices_missing_constant_returns_empty(tmp_path: Path, caplog):
    session = FakeSession()
    session.bodies[HF_CONSTANTS_CSV] = session.bodies[HF_CONSTANTS_CSV].replace("Iberdrola_mFRR", "renamed")
    fetcher = CSVDataFetcher(session, tmp_path)
    prices = run(fetcher.get_prices(
        "Iberdrola | Simples Indexado", "SIMPLE", 23, target_date=datetime(2026, 10, 2, tzinfo=TZ)
    ))
    assert prices == []
    assert "Iberdrola_mFRR" in caplog.text
