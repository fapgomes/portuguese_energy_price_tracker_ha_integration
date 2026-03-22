# Portuguese Energy Price Tracker for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub Release](https://img.shields.io/github/release/fapgomes/portuguese_energy_price_tracker_ha_integration.svg)](https://github.com/fapgomes/portuguese_energy_price_tracker_ha_integration/releases)
[![License](https://img.shields.io/github/license/fapgomes/portuguese_energy_price_tracker_ha_integration.svg)](https://github.com/fapgomes/portuguese_energy_price_tracker_ha_integration/blob/main/LICENSE)

A Home Assistant custom integration that tracks real-time electricity prices for Portuguese energy providers. Calculates hourly prices from OMIE market data using provider-specific formulas.

> **Note:** This is a fork of [joaofernandes/portuguese_energy_price_tracker_ha_integration](https://github.com/joaofernandes/portuguese_energy_price_tracker_ha_integration) with an expanded data source and additional providers.

## Features

- **Real-time Energy Prices**: Calculates electricity prices from OMIE market data + provider formulas
- **23 Providers**: Supports all major Portuguese indexed energy providers
- **Current & Future Data**: Access current prices, today's min/max, tomorrow's prices (available after ~13h)
- **Multi-tariff Support**: Simples, Bi-horário, Tri-horário and high-voltage tariffs
- **VAT Flexibility**: Configurable VAT rate (default 23%) with automatic price calculations
- **Smart Caching**: 1-hour cache with local file fallback for offline reliability
- **Active Provider Routing**: Generic sensors that follow your selected provider
- **Manual Refresh Service**: Force data updates with optional historical date lookup

## Supported Providers

| Provider | Type | Tariffs |
|----------|------|---------|
| Alfa Energia - ALFA POWER INDEX BTN | Quarto-horário | Simples, Bi, Tri |
| Coopérnico Base | Quarto-horário | Simples, Bi, Tri |
| Coopérnico GO | Quarto-horário | Simples, Bi, Tri |
| EDP - Eletricidade Indexada Horária | Quarto-horário | Simples, Bi, Tri |
| EDP - Eletricidade Indexada Média | Média | Simples, Bi, Tri |
| Endesa - Tarifa Indexada | Média | Simples, Bi |
| EZU - Indexada | Quarto-horário | Simples, Bi, Tri |
| G9 - Smart Dynamic | Quarto-horário | Simples, Bi, Tri |
| G9 - Smart Dynamic (Empresarial) | Quarto-horário | Simples, Bi, Tri |
| G9 - Smart Index | Média | Simples, Bi, Tri |
| G9 - Smart Index (Empresarial) | Média | Simples, Bi, Tri |
| Galp - Plano Flexível / Dinâmico | Quarto-horário | Simples, Bi, Tri |
| Goldenergy - Tarifário Indexado 100% | Média | Simples |
| **Ibelectra - Solução Amigo** | Média | Simples, Bi, Tri HV |
| **Ibelectra - Solução Família** | Média | Simples, Bi, Tri HV |
| Iberdrola - Simples Indexado | Média | Simples |
| Iberdrola - Simples Indexado Dinâmico | Quarto-horário | Simples |
| **Luzboa - BTN SPOTDEF** | Média | Simples, Bi, Tri |
| **LUZiGÁS - Super Lig Index** | Média | Simples, Bi, Tri |
| Meo Energia - Tarifa Variável | Quarto-horário | Simples, Bi, Tri HV |
| Plenitude - Tendência | Quarto-horário | Simples |
| Repsol - Leve PRO Sem Mais | Quarto-horário | Simples, Bi, Tri |
| Repsol - Leve Sem Mais | Quarto-horário | Simples, Bi, Tri |

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/fapgomes/portuguese_energy_price_tracker_ha_integration`
6. Select category: "Integration"
7. Click "Add"
8. Find "Portuguese Energy Price Tracker" in HACS and click "Download"
9. **Restart Home Assistant** (required, not just reload)

### Manual Installation

1. Download the latest release from [GitHub releases](https://github.com/fapgomes/portuguese_energy_price_tracker_ha_integration/releases)
2. Copy the `custom_components/portuguese_energy_price_tracker` folder to your `custom_components` directory
3. Restart Home Assistant

### Migrating from the original integration

If you already have [joaofernandes/portuguese_energy_price_tracker_ha_integration](https://github.com/joaofernandes/portuguese_energy_price_tracker_ha_integration) installed:

1. In HACS, remove the original integration (this only removes files, not your config/data)
2. Add this fork as a custom repository (see above)
3. Install and restart HA
4. Your existing config entries and sensor history are preserved
5. Provider names are automatically migrated (migration v7)

## Configuration

### Via UI

1. Go to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Portuguese Energy Price Tracker"
4. Follow the configuration flow:
   - **Provider**: Select your energy provider
   - **Tariff**: Choose your tariff plan
   - **Display Name**: Custom name for this configuration (optional)
   - **VAT Rate**: VAT percentage (default: 23)

### Multiple Providers

You can add multiple instances for different providers or tariffs. Each instance creates its own set of sensors. Use the **Active Energy Provider** select entity to switch between providers in the generic routing sensors.

## Sensors

### Generic Routing Sensors (Active Provider)

These sensors automatically reflect the currently selected provider's data:

| Sensor | Entity ID |
|--------|-----------|
| Active Provider Current Price | `sensor.active_provider_current_price` |
| Active Provider Current Price with VAT | `sensor.active_provider_current_price_with_vat` |
| Active Provider Today Max/Min Price | `sensor.active_provider_today_max_price` etc. |
| Active Provider Tomorrow Max/Min Price | `sensor.active_provider_tomorrow_max_price` etc. |
| Active Provider All Prices | `sensor.active_provider_all_prices` |

**Provider Selection:** `select.active_energy_provider`

### Provider-Specific Sensors

For each configured instance:

- **Current Price** / **Current Price with VAT**
- **Today's Max/Min Price** (with and without VAT)
- **Tomorrow's Max/Min Price** (with and without VAT) — includes `data_available` attribute
- **Today Prices** / **Tomorrow Prices** / **All Prices** — full price arrays in attributes

### Tomorrow Sensors

Tomorrow's prices are typically published after ~13h. Before that, these sensors show "Unknown" with attribute `data_available: false`. This is expected behaviour.

## Services

### `portuguese_energy_price_tracker.refresh_data`

Manually refresh energy price data.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `date` | No | Specific date (YYYY-MM-DD). Defaults to today. |

```yaml
# Refresh today's data
service: portuguese_energy_price_tracker.refresh_data

# Fetch data for specific date
service: portuguese_energy_price_tracker.refresh_data
data:
  date: "2026-03-22"
```

## Data Source

This integration calculates prices from three data files maintained by Tiago Felícia:

| Data | Description |
|------|-------------|
| **OMIE Market Prices** | 15-minute interval OMIE prices + losses factors |
| **Provider Constants** | Margins, fees, and loss factors per provider |
| **Provider Formulas** | Calculation formulas per provider/tariff |

Source: [HuggingFace - Simulador Tarifários Eletricidade](https://huggingface.co/spaces/tiagofelicia/simulador-tarifarios-eletricidade)

The integration fetches OMIE data (updated daily), applies provider-specific formulas and constants, and calculates the final price per 15-minute interval. Refresh interval: every 5 minutes.

## Automation Examples

### Charge Battery When Price is Low

```yaml
automation:
  - alias: "Charge Battery - Low Price"
    trigger:
      - platform: numeric_state
        entity_id: sensor.active_provider_current_price_with_vat
        below: 0.15
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.battery_charger
```

### Notify When Tomorrow's Prices Are Available

```yaml
automation:
  - alias: "Tomorrow Prices Available"
    trigger:
      - platform: state
        entity_id: sensor.active_provider_tomorrow_max_price
        from: "unknown"
    action:
      - service: notify.mobile_app
        data:
          message: >
            Tomorrow's prices available!
            Max: {{ states('sensor.active_provider_tomorrow_max_price_with_vat') }} €/kWh
            Min: {{ states('sensor.active_provider_tomorrow_min_price_with_vat') }} €/kWh
```

## Troubleshooting

### Sensors Show "Unknown"

- **Tomorrow sensors before ~13h**: Expected — data not yet published
- **All sensors**: Check logs at Settings > System > Logs (search for "portuguese_energy_price_tracker")
- **After update**: Restart HA (not just reload) if you added new files

### Sensors Show "Unavailable"

- Try reloading the integration: Settings > Devices & Services > ⋮ > Reload
- If it persists, restart Home Assistant

## Credits

This integration is based on [joaofernandes/portuguese_energy_price_tracker_ha_integration](https://github.com/joaofernandes/portuguese_energy_price_tracker_ha_integration) and would not be possible without the work of **[Tiago Felícia](https://github.com/tiagofelicia)**, who maintains the comprehensive Portuguese energy price dataset.

**Data source:** [tiagofelicia/simulador-tarifarios-eletricidade](https://huggingface.co/spaces/tiagofelicia/simulador-tarifarios-eletricidade)

Without Tiago's dedication to maintaining this data, this integration would not exist.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.

## Support

- **Issues**: [GitHub Issues](https://github.com/fapgomes/portuguese_energy_price_tracker_ha_integration/issues)
