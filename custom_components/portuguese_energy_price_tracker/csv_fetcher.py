"""CSV Data Fetcher for Energy Price Tracker.

This module fetches Portuguese energy price data from Tiago Felícia's
HuggingFace space, which contains OMIE market prices, provider constants,
and provider formulas.

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

from .hf_fetcher import HFDataFetcher, PERIOD_COLUMNS
from .formula_engine import calculate_price

_LOGGER = logging.getLogger(__name__)

# Tariff code to display name mapping (for formula lookup in Indexados.csv)
TARIFF_CODE_TO_CSV = {
    "SIMPLE": "Simples",
    "BIHORARIO_DIARIO": "Bi-horário - Ciclo Diário",
    "BIHORARIO_SEMANAL": "Bi-horário - Ciclo Semanal",
    "TRIHORARIO_DIARIO": "Tri-horário - Ciclo Diário",
    "TRIHORARIO_SEMANAL": "Tri-horário - Ciclo Semanal",
    "TRIHORARIO_DIARIO_HV": "Tri-horário > 20.7 kVA - Ciclo Diário",
    "TRIHORARIO_SEMANAL_HV": "Tri-horário > 20.7 kVA - Ciclo Semanal",
}

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
    """Fetcher for energy price data using HuggingFace OMIE data + provider formulas."""

    def __init__(self, session: aiohttp.ClientSession, data_dir: Path):
        self.session = session
        self.data_dir = data_dir
        self.cache = CSVDataCache()
        self.hf = HFDataFetcher(session, data_dir)

    async def get_prices(
        self,
        provider: str,
        tariff: str,
        vat_rate: int,
        target_date: datetime | None = None,
        bypass_cache: bool = False,
    ) -> list[dict]:
        """Get prices for provider/tariff, optionally for a specific date.

        Fetches OMIE market data from HuggingFace, loads provider constants
        and formulas, then calculates final prices for each 15-min interval.

        Args:
            provider: Provider name (must match Indexados.csv 'nome' column)
            tariff: Tariff code (e.g., SIMPLE, BIHORARIO_DIARIO)
            vat_rate: VAT percentage (e.g., 23)
            target_date: Date to fetch data for (defaults to today)
            bypass_cache: Force recalculation, ignore cache

        Returns:
            List of price dicts with datetime, interval, price, price_w_vat, market_price, tar_cost
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

        # Fetch constants and formulas
        constants = await self.hf.fetch_constants()
        formulas = await self.hf.fetch_formulas()

        # Look up the formula for this provider + tariff
        tariff_csv_name = TARIFF_CODE_TO_CSV.get(tariff, tariff)
        provider_formulas = formulas.get(provider, {})
        formula = provider_formulas.get(tariff_csv_name)

        if not formula:
            _LOGGER.warning(
                f"No formula found for provider='{provider}', tariff='{tariff_csv_name}'. "
                f"Available: {list(provider_formulas.keys())}"
            )
            return []

        # Get OMIE rows for the target date
        omie_rows = self.hf.get_omie_for_date(target_date)
        if not omie_rows:
            _LOGGER.info(f"No OMIE data for {date_key}")
            return []

        # Compute monthly aggregates (for Indexado Média providers)
        monthly_agg = self.hf.compute_monthly_aggregates(target_date)

        # Determine which column gives us the period type for this tariff
        period_col = PERIOD_COLUMNS.get(tariff, "Simp")

        # Calculate prices for each 15-min interval
        prices = []
        skipped = 0
        for row in omie_rows:
            try:
                raw_date = (row.get("\ufeffData") or row.get("Data", "")).strip()
                raw_hora = row.get("Hora", "").strip()
                if not raw_date or not raw_hora:
                    skipped += 1
                    continue

                # Parse date and time
                parsed_date = datetime.strptime(raw_date, "%m/%d/%Y")
                hour, minute = raw_hora.split(":")
                dt_obj = dt_util.as_local(datetime(
                    parsed_date.year, parsed_date.month, parsed_date.day,
                    int(hour), int(minute), 0
                ))

                # Get period type for this interval
                period_type = row.get(period_col, "S").strip()

                # Calculate price using formula engine
                price_no_vat = calculate_price(
                    formula=formula,
                    omie_row=row,
                    constants=constants,
                    monthly_agg=monthly_agg,
                    tariff_cycle=tariff,
                    period_type=period_type,
                )

                if price_no_vat is None:
                    skipped += 1
                    continue

                # Calculate price with VAT
                price_with_vat = price_no_vat * (1 + vat_rate / 100)

                # Build interval string (matching old format)
                end_minute = int(minute) + 15
                end_hour = int(hour)
                if end_minute >= 60:
                    end_minute = 0
                    end_hour += 1
                interval_str = f"[{int(hour):02d}:{int(minute):02d}-{end_hour:02d}:{end_minute:02d}["

                omie_kwh = float(row.get("OMIE", 0)) / 1000  # Convert €/MWh to €/kWh

                prices.append({
                    "datetime": dt_obj.isoformat(),
                    "interval": interval_str,
                    "price": round(price_no_vat, 5),
                    "price_w_vat": round(price_with_vat, 5),
                    "market_price": round(omie_kwh, 5),
                    "tar_cost": 0,  # TAR is now embedded in the formula
                })

            except (ValueError, KeyError) as err:
                _LOGGER.debug(f"Error processing OMIE row: {err}")
                skipped += 1
                continue

        if skipped > 0:
            _LOGGER.debug(f"Skipped {skipped} OMIE rows for {provider} - {tariff_csv_name}")

        _LOGGER.info(f"Calculated {len(prices)} prices for {provider} - {tariff_csv_name} on {date_key}")

        # Cache the result
        if date_key not in self.cache._cache:
            self.cache._cache[date_key] = {}
        self.cache._cache[date_key][cache_key] = prices
        self.cache._cache_times[date_key] = datetime.now()

        return prices
