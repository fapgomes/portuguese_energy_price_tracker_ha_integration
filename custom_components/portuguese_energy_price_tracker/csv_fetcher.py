"""CSV Data Fetcher for Energy Price Tracker.

This module fetches Portuguese energy price data from Tiago Felícia's
HuggingFace space, which contains OMIE market prices, provider constants,
and the per-provider flags (TSE/TAR included). Formulas live in tariffs.py.

Data Source Credits:
    The data is maintained by Tiago Felícia at:
    https://huggingface.co/spaces/tiagofelicia/simulador-tarifarios-eletricidade

    Special thanks to Tiago Felícia for collecting and maintaining accurate
    energy price data for multiple Portuguese providers and making it
    freely available to the community.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiohttp
from homeassistant.util import dt as dt_util

from .hf_fetcher import HFDataFetcher
from .pricing import TariffFlags, compute_day

_LOGGER = logging.getLogger(__name__)

# Cache settings
CACHE_DURATION = timedelta(hours=1)


class CSVDataCache:
    """Cache for calculated price data."""

    def __init__(self):
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_times: dict[str, datetime] = {}

    def get(self, date_key: str, bypass_cache: bool = False) -> dict[str, Any] | None:
        if bypass_cache:
            return None
        if date_key not in self._cache:
            return None
        cache_time = self._cache_times.get(date_key)
        if cache_time and datetime.now() - cache_time < CACHE_DURATION:
            return self._cache[date_key]
        del self._cache[date_key]
        del self._cache_times[date_key]
        return None

    def set(self, date_key: str, data: dict[str, Any]):
        self._cache[date_key] = data
        self._cache_times[date_key] = datetime.now()


class CSVDataFetcher:
    """Fetcher for energy price data using HuggingFace OMIE data + tariffs.py formulas."""

    def __init__(self, session: aiohttp.ClientSession, data_dir: Path):
        self.session = session
        self.data_dir = data_dir
        self.cache = CSVDataCache()
        self.hf = HFDataFetcher(session, data_dir)
        self._warned_unlisted: set[str] = set()

    async def get_prices(
        self,
        provider: str,
        tariff: str,
        vat_rate: int,
        target_date: datetime | None = None,
        bypass_cache: bool = False,
    ) -> list[dict]:
        """Get prices for provider/tariff, optionally for a specific date.

        Fetches OMIE market data, provider constants and tariff flags from
        HuggingFace, then prices each 15-min interval with the formulas in
        tariffs.py (see pricing.compute_day).

        Args:
            provider: Provider name (key of PROVIDERS / TARIFFS)
            tariff: Tariff code (e.g., SIMPLE, BIHORARIO_DIARIO)
            vat_rate: VAT percentage (e.g., 23)
            target_date: Date to fetch data for (defaults to today)
            bypass_cache: Force recalculation, ignore cache

        Returns:
            List of price dicts with datetime, interval, period, price, price_w_vat,
            provider_price, spot_price, market_price and tar_cost
        """
        if target_date is None:
            target_date = dt_util.now()

        date_key = target_date.strftime("%Y-%m-%d")
        cache_key = f"{provider}_{tariff}"

        # Check memory cache
        if not bypass_cache:
            cached = self.cache.get(date_key)
            if cached and cache_key in cached:
                _LOGGER.debug(f"Using cached prices for {cache_key} on {date_key}")
                return cached[cache_key]

        # Ensure OMIE data is loaded
        await self.hf.load_omie_data()

        constants = await self.hf.fetch_constants()
        tariff_flags = await self.hf.fetch_tariff_flags()

        flags = tariff_flags.get(provider)
        if flags is None:
            flags = TariffFlags()
            if provider not in self._warned_unlisted:
                self._warned_unlisted.add(provider)
                _LOGGER.warning(
                    f"Provider '{provider}' is no longer listed in Indexados.csv; "
                    f"assuming TSE and TAR are not included in its energy price"
                )

        # Get OMIE rows for the target date
        omie_rows = self.hf.get_omie_for_date(target_date)
        if not omie_rows:
            _LOGGER.info(f"No OMIE data for {date_key}")
            return []

        try:
            computed = compute_day(
                tariff_name=provider,
                tariff_code=tariff,
                day_rows=omie_rows,
                month_rows=self.hf.get_month_to_date_rows(target_date),
                year_rows=self.hf.get_year_rows(target_date.year),
                constants=constants,
                flags=flags,
            )
        except KeyError as err:
            _LOGGER.warning(
                f"Cannot price {provider} - {tariff} on {date_key}: "
                f"{err} is missing from the HuggingFace data"
            )
            return []

        prices = []
        for row, values in zip(omie_rows, computed):
            raw_date = (row.get("\ufeffData") or row.get("Data", "")).strip()
            raw_hora = row.get("Hora", "").strip()
            parsed_date = datetime.strptime(raw_date, "%m/%d/%Y")
            hour, minute = (int(x) for x in raw_hora.split(":"))
            dt_obj = dt_util.as_local(datetime(
                parsed_date.year, parsed_date.month, parsed_date.day, hour, minute, 0
            ))

            end_minute = minute + 15
            end_hour = hour
            if end_minute >= 60:
                end_minute = 0
                end_hour += 1
            interval_str = f"[{hour:02d}:{minute:02d}-{end_hour:02d}:{end_minute:02d}["

            spot_price = values["spot_price"]
            prices.append({
                "datetime": dt_obj.isoformat(),
                "interval": interval_str,
                "period": values["period"],
                "price": round(values["price"], 5),
                "price_w_vat": round(values["price"] * (1 + vat_rate / 100), 5),
                "provider_price": round(values["provider_price"], 5),
                "spot_price": round(spot_price, 5) if spot_price is not None else None,
                "market_price": round(float(row.get("OMIE", 0)) / 1000, 5),  # €/MWh -> €/kWh
                "tar_cost": round(values["tar_cost"], 5),
            })

        _LOGGER.info(f"Calculated {len(prices)} prices for {provider} - {tariff} on {date_key}")

        # Cache the result
        if date_key not in self.cache._cache:
            self.cache._cache[date_key] = {}
        self.cache._cache[date_key][cache_key] = prices
        self.cache._cache_times[date_key] = datetime.now()

        return prices
