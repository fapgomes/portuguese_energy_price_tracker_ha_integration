"""Tests for HuggingFace fetching and the end-to-end price calculation."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

import pytest

from conftest import FIXTURES, TZ
from pept.csv_fetcher import CSVDataFetcher
from pept.hf_fetcher import (
    HF_CONSTANTS_CSV,
    HF_INDEXADOS_CSV,
    HF_MANIFEST,
    HF_OMIE_CSV,
    HFDataFetcher,
)
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


def omie_csv(days=((1, 40.0), (2, 80.0), (3, 500.0))) -> str:
    lines = [OMIE_HEADER]
    for day, omie in days:
        for hh in range(24):
            for mm in (0, 15, 30, 45):
                period = "V" if hh < 8 else "F"
                lines.append(
                    f"10/{day:02d}/2026,{hh:02d}:{mm:02d},S,{period},{period},{period},{period},"
                    f"0.03,0.03,0.03,{omie},1.1,1\n"
                )
    return "".join(lines)


class FakeResponse:
    def __init__(self, body: str | None):
        self.status = 200 if body is not None else 500
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
        self.set_manifest(constantes="c1", indexados="i1", omie="o1")
        self.urls: list[str] = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        return FakeResponse(self.bodies[url])

    def set_manifest(self, constantes: str, indexados: str, omie: str):
        self.bodies[HF_MANIFEST] = json.dumps(
            {"Constantes": constantes, "Indexados": indexados, "OMIE_PERDAS_CICLOS": omie}
        )

    def count(self, url: str) -> int:
        return self.urls.count(url)


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


IBERDROLA = ("Iberdrola | Simples Indexado", "SIMPLE", 23)


def test_unchanged_manifest_keeps_data(tmp_path: Path):
    session = FakeSession()
    fetcher = CSVDataFetcher(session, tmp_path)
    run(fetcher.get_prices(*IBERDROLA, target_date=datetime(2026, 10, 2, tzinfo=TZ)))
    run(fetcher.get_prices(*IBERDROLA, target_date=datetime(2026, 10, 2, tzinfo=TZ), bypass_cache=True))
    assert session.count(HF_MANIFEST) == 2
    assert session.count(HF_OMIE_CSV) == 1
    assert session.count(HF_CONSTANTS_CSV) == 1


def test_changed_omie_is_reloaded(tmp_path: Path):
    """Tomorrow's prices appear once the upstream OMIE file changes."""
    session = FakeSession()
    fetcher = CSVDataFetcher(session, tmp_path)
    assert run(fetcher.get_prices(*IBERDROLA, target_date=datetime(2026, 10, 4, tzinfo=TZ))) == []

    session.bodies[HF_OMIE_CSV] = omie_csv(((1, 40.0), (2, 80.0), (3, 500.0), (4, 100.0)))
    session.set_manifest(constantes="c1", indexados="i1", omie="o2")
    prices = run(fetcher.get_prices(*IBERDROLA, target_date=datetime(2026, 10, 4, tzinfo=TZ), bypass_cache=True))
    assert len(prices) == 96
    assert session.count(HF_OMIE_CSV) == 2
    assert session.count(HF_CONSTANTS_CSV) == 1
    assert session.count(HF_INDEXADOS_CSV) == 1


def test_changed_data_clears_cached_prices(tmp_path: Path):
    session = FakeSession()
    fetcher = CSVDataFetcher(session, tmp_path)
    day = datetime(2026, 10, 2, tzinfo=TZ)
    before = run(fetcher.get_prices(*IBERDROLA, target_date=day))

    session.bodies[HF_OMIE_CSV] = omie_csv(((1, 40.0), (2, 160.0)))
    session.set_manifest(constantes="c1", indexados="i1", omie="o2")
    fetcher.hf._manifest_checked = None  # past the check interval
    after = run(fetcher.get_prices(*IBERDROLA, target_date=day))
    # Month-to-date mean went from 60 to 100 €/MWh
    assert after[0]["provider_price"] - before[0]["provider_price"] == pytest.approx(0.04 * 1.1674, abs=1e-5)


def test_manifest_check_is_throttled(tmp_path: Path):
    session = FakeSession()
    hf = HFDataFetcher(session, tmp_path)
    run(hf.refresh_if_changed())
    session.set_manifest(constantes="c2", indexados="i1", omie="o1")
    assert run(hf.refresh_if_changed()) is False
    assert session.count(HF_MANIFEST) == 1
    assert run(hf.refresh_if_changed(force=True)) is True
    assert hf._constants is None


def test_manifest_failure_keeps_data(tmp_path: Path):
    session = FakeSession()
    fetcher = CSVDataFetcher(session, tmp_path)
    day = datetime(2026, 10, 2, tzinfo=TZ)
    run(fetcher.get_prices(*IBERDROLA, target_date=day))
    session.bodies[HF_MANIFEST] = None
    prices = run(fetcher.get_prices(*IBERDROLA, target_date=day, bypass_cache=True))
    assert len(prices) == 96
    assert session.count(HF_OMIE_CSV) == 1
