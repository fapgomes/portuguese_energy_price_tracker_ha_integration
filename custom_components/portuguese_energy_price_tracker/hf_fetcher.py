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

from .pricing import TariffFlags

_LOGGER = logging.getLogger(__name__)

HF_BASE = "https://huggingface.co/spaces/tiagofelicia/simulador-tarifarios-eletricidade/resolve/main/data/csv"
HF_MANIFEST = f"{HF_BASE}/manifest.json"
HF_OMIE_CSV = f"{HF_BASE}/OMIE_PERDAS_CICLOS.csv"
HF_CONSTANTS_CSV = f"{HF_BASE}/Constantes.csv"
HF_INDEXADOS_CSV = f"{HF_BASE}/Indexados.csv"


def _is_true(value: str | None) -> bool:
    return (value or "").strip().lower() == "true"


class HFDataFetcher:
    """Fetches and caches data from HuggingFace."""

    def __init__(self, session: aiohttp.ClientSession, data_dir: Path):
        self.session = session
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._constants: dict[str, float] | None = None
        self._manifest: dict[str, str] | None = None
        self._omie_cache: dict[str, list[dict]] = {}  # date_key -> rows
        self._tariff_flags: dict[str, TariffFlags] | None = None  # provider -> flags
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

    async def fetch_tariff_flags(self) -> dict[str, TariffFlags]:
        """Fetch per-provider flags (TSE/TAR included) from Indexados.csv.

        Returns: {provider_name: TariffFlags}
        """
        if self._tariff_flags:
            return self._tariff_flags

        content = await self._fetch_url(HF_INDEXADOS_CSV, "hf_indexados.csv")
        content = self._strip_bom(content)

        flags: dict[str, TariffFlags] = {}
        reader = csv.DictReader(StringIO(content))
        for row in reader:
            nome = (row.get("nome") or "").strip()
            if nome and nome not in flags:
                flags[nome] = TariffFlags(
                    tse_included=_is_true(row.get("financiamento_tse_incluido")),
                    tar_included=_is_true(row.get("tar_incluida_energia")),
                )

        self._tariff_flags = flags
        _LOGGER.info(f"Loaded tariff flags for {len(flags)} providers from HuggingFace")
        return flags

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

    def get_month_to_date_rows(self, target_date: datetime) -> list[dict]:
        """OMIE rows from the 1st of target_date's month up to and including target_date."""
        rows: list[dict] = []
        for day in range(1, target_date.day + 1):
            date_key = f"{target_date.year:04d}-{target_date.month:02d}-{day:02d}"
            rows.extend(self._omie_cache.get(date_key, []))
        return rows

    def get_year_rows(self, year: int) -> list[dict]:
        """All OMIE rows of a calendar year."""
        prefix = f"{year:04d}-"
        return [
            row
            for date_key, rows in self._omie_cache.items()
            if date_key.startswith(prefix)
            for row in rows
        ]

    def invalidate_cache(self):
        """Clear all cached data to force re-fetch."""
        self._constants = None
        self._manifest = None
        self._tariff_flags = None
        self._omie_cache.clear()
        self._omie_loaded = False
