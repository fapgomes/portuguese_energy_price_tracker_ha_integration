"""HuggingFace Data Fetcher for Energy Price Tracker.

Fetches OMIE market prices, provider constants, and provider catalog
from Tiago Felícia's HuggingFace space.

Data Source Credits:
    The data is maintained by Tiago Felícia at:
    https://huggingface.co/spaces/tiagofelicia/simulador-tarifarios-eletricidade

    Special thanks to Tiago Felícia for collecting and maintaining accurate
    energy price data for multiple Portuguese providers and making it
    freely available to the community.
"""
from __future__ import annotations

import asyncio
import csv
import json
import logging
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any

import aiohttp
from homeassistant.util import dt as dt_util
from homeassistant.util.file import write_utf8_file

_LOGGER = logging.getLogger(__name__)

HF_BASE = "https://huggingface.co/spaces/tiagofelicia/simulador-tarifarios-eletricidade/resolve/main/data/csv"
HF_MANIFEST = f"{HF_BASE}/manifest.json"
HF_OMIE_CSV = f"{HF_BASE}/OMIE_PERDAS_CICLOS.csv"
HF_CONSTANTS_CSV = f"{HF_BASE}/Constantes.csv"
HF_INDEXADOS_CSV = f"{HF_BASE}/Indexados.csv"

# Period type mapping for tariff cycles
PERIOD_COLUMNS = {
    "SIMPLE": "Simp",
    "BIHORARIO_DIARIO": "BD",
    "BIHORARIO_SEMANAL": "BS",
    "TRIHORARIO_DIARIO": "TD",
    "TRIHORARIO_SEMANAL": "TS",
    "TRIHORARIO_DIARIO_HV": "TD",
    "TRIHORARIO_SEMANAL_HV": "TS",
}


class HFDataFetcher:
    """Fetches and caches data from HuggingFace."""

    def __init__(self, session: aiohttp.ClientSession, data_dir: Path):
        self.session = session
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._constants: dict[str, float] | None = None
        self._manifest: dict[str, str] | None = None
        self._omie_cache: dict[str, list[dict]] = {}  # date_key -> rows
        self._formulas: dict[str, dict[str, str]] | None = None  # provider -> {tariff -> formula}
        self._omie_loaded = False

    async def _fetch_url(self, url: str, cache_name: str, max_retries: int = 3) -> str:
        """Fetch a URL with retry logic and local disk caching."""
        cache_path = self.data_dir / cache_name

        for attempt in range(max_retries):
            try:
                async with self.session.get(
                    url, timeout=aiohttp.ClientTimeout(total=60), allow_redirects=True
                ) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status} fetching {url}")
                    content = await response.text()
                    write_utf8_file(str(cache_path), content)
                    return content
            except Exception as err:
                if attempt == max_retries - 1:
                    if cache_path.exists():
                        _LOGGER.warning(f"Using cached {cache_name} after fetch failure: {err}")
                        return cache_path.read_text(encoding="utf-8")
                    raise
                wait_time = 2 ** attempt
                _LOGGER.warning(f"Retry {attempt+1}/{max_retries} for {cache_name}: {err}")
                await asyncio.sleep(wait_time)

    @staticmethod
    def _strip_bom(content: str) -> str:
        """Remove BOM from content if present."""
        return content.lstrip('\ufeff')

    async def fetch_constants(self) -> dict[str, float]:
        """Fetch and parse provider constants."""
        if self._constants:
            return self._constants

        content = await self._fetch_url(HF_CONSTANTS_CSV, "hf_constantes.csv")
        content = self._strip_bom(content)

        constants = {}
        reader = csv.DictReader(StringIO(content))
        for row in reader:
            name = (row.get("\ufeffconstante") or row.get("constante", "")).strip()
            value = (row.get("valor_unitário") or row.get("valor_unit\u00e1rio", "")).strip()
            if name and value:
                try:
                    constants[name] = float(value)
                except ValueError:
                    pass

        self._constants = constants
        _LOGGER.info(f"Loaded {len(constants)} constants from HuggingFace")
        return constants

    async def fetch_formulas(self) -> dict[str, dict[str, str]]:
        """Fetch and parse provider formulas from Indexados.csv.

        Returns: {provider_name: {tariff_option: formula_string}}
        """
        if self._formulas:
            return self._formulas

        content = await self._fetch_url(HF_INDEXADOS_CSV, "hf_indexados.csv")
        content = self._strip_bom(content)

        formulas: dict[str, dict[str, str]] = {}
        reader = csv.DictReader(StringIO(content))
        for row in reader:
            nome = (row.get("nome") or "").strip()
            opcao = (row.get("opcao_horaria_e_ciclo") or "").strip()
            formula = (row.get("formula_calculo") or "").strip()
            if nome and opcao and formula:
                # Register under the original name
                if nome not in formulas:
                    formulas[nome] = {}
                if opcao not in formulas[nome]:
                    formulas[nome][opcao] = formula

                # Also register under alternate separator (| <-> -)
                # so both "Provider | Plan" and "Provider - Plan" work
                if " | " in nome:
                    alt_nome = nome.replace(" | ", " - ")
                elif " - " in nome:
                    alt_nome = nome.replace(" - ", " | ")
                else:
                    alt_nome = None

                if alt_nome:
                    if alt_nome not in formulas:
                        formulas[alt_nome] = {}
                    if opcao not in formulas[alt_nome]:
                        formulas[alt_nome][opcao] = formula

        self._formulas = formulas
        _LOGGER.info(f"Loaded formulas for {len(formulas)} providers from HuggingFace")
        return formulas

    async def load_omie_data(self) -> None:
        """Fetch and parse the full OMIE CSV into memory, indexed by date."""
        if self._omie_loaded:
            return

        content = await self._fetch_url(HF_OMIE_CSV, "hf_omie_perdas_ciclos.csv")
        content = self._strip_bom(content)

        self._omie_cache.clear()
        reader = csv.DictReader(StringIO(content))
        for row in reader:
            raw_date = (row.get("\ufeffData") or row.get("Data", "")).strip()
            if not raw_date:
                continue
            try:
                parsed = datetime.strptime(raw_date, "%m/%d/%Y")
                date_key = parsed.strftime("%Y-%m-%d")
            except ValueError:
                continue

            if date_key not in self._omie_cache:
                self._omie_cache[date_key] = []
            self._omie_cache[date_key].append(row)

        self._omie_loaded = True
        _LOGGER.info(f"Loaded OMIE data: {len(self._omie_cache)} dates")

    def get_omie_for_date(self, target_date: datetime) -> list[dict]:
        """Get OMIE rows for a specific date (must call load_omie_data first)."""
        date_key = target_date.strftime("%Y-%m-%d")
        return self._omie_cache.get(date_key, [])

    def compute_monthly_aggregates(self, target_date: datetime) -> dict[str, float]:
        """Compute monthly average OMIE and Perdas from cached data.

        Returns a dict with keys like:
        - OMIE_S_M: monthly avg OMIE for Simples
        - OMIE_BD_M_V: monthly avg OMIE for Bi-Diário Vazio
        - Perdas_Anual_S: monthly avg Perdas for Simples
        - Perdas_Anual_BD_V: monthly avg Perdas for Bi-Diário Vazio
        """
        month = target_date.month
        year = target_date.year

        month_rows = []
        for date_key, rows in self._omie_cache.items():
            try:
                dt = datetime.strptime(date_key, "%Y-%m-%d")
                if dt.month == month and dt.year == year:
                    month_rows.extend(rows)
            except ValueError:
                continue

        if not month_rows:
            _LOGGER.warning(f"No OMIE data for month {year}-{month:02d}")
            return {}

        aggregates: dict[str, float] = {}

        # Overall Simples average (all intervals)
        omie_sum, perdas_sum, count = 0.0, 0.0, 0
        for row in month_rows:
            try:
                omie_sum += float(row.get("OMIE", 0))
                perdas_sum += float(row.get("Perdas", 1))
                count += 1
            except (ValueError, TypeError):
                continue

        if count > 0:
            aggregates["OMIE_S_M"] = omie_sum / count
            aggregates["Perdas_Anual_S"] = perdas_sum / count
            aggregates["Perdas_Anuais_S"] = perdas_sum / count  # alias used by Ibelectra formulas
            aggregates["Perdas_M_S"] = perdas_sum / count

        # Per-cycle per-period averages
        cycle_periods = {
            "BD": {"V": "V", "FV": "F"},
            "BS": {"V": "V", "FV": "F"},
            "TD": {"V": "V", "C": "C", "P": "P"},
            "TS": {"V": "V", "C": "C", "P": "P"},
        }

        for cycle, period_map in cycle_periods.items():
            for period_key, period_value in period_map.items():
                o_sum, p_sum, cnt = 0.0, 0.0, 0
                for row in month_rows:
                    if row.get(cycle, "").strip() == period_value:
                        try:
                            o_sum += float(row.get("OMIE", 0))
                            p_sum += float(row.get("Perdas", 1))
                            cnt += 1
                        except (ValueError, TypeError):
                            continue
                if cnt > 0:
                    aggregates[f"OMIE_{cycle}_M_{period_key}"] = o_sum / cnt
                    aggregates[f"Perdas_Anual_{cycle}_{period_key}"] = p_sum / cnt
                    aggregates[f"Perdas_Anuais_{cycle}_{period_key}"] = p_sum / cnt  # alias
                    aggregates[f"Perdas_M_{cycle}_{period_key}"] = p_sum / cnt

        _LOGGER.debug(f"Monthly aggregates for {year}-{month:02d}: {len(aggregates)} values")
        return aggregates

    def invalidate_cache(self):
        """Clear all cached data to force re-fetch."""
        self._constants = None
        self._manifest = None
        self._formulas = None
        self._omie_cache.clear()
        self._omie_loaded = False
