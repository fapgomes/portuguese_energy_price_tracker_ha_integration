"""Constants for the Energy Price Tracker integration."""
from typing import Final

DOMAIN: Final = "portuguese_energy_price_tracker"

# Configuration
CONF_PROVIDER: Final = "provider"
CONF_TARIFF: Final = "tariff"
CONF_DISPLAY_NAME: Final = "display_name"
CONF_VAT: Final = "vat"
CONF_INCLUDE_VAT: Final = "include_vat"
CONF_ENABLE_DEBUG: Final = "enable_debug"

# Defaults
DEFAULT_SCAN_INTERVAL: Final = 300  # 5 minutes
SCAN_INTERVAL: Final = DEFAULT_SCAN_INTERVAL
DEFAULT_VAT: Final = 23
DEFAULT_INCLUDE_VAT: Final = True
DEFAULT_ENABLE_DEBUG: Final = False

# Supported providers and their tariffs (from HuggingFace Indexados.csv)
# Provider names MUST match the 'nome' column in Indexados.csv exactly
PROVIDERS: Final = {
    "Alfa Energia | ALFA POWER INDEX BTN": {
        "name": "Alfa Energia | ALFA POWER INDEX BTN",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "Coopérnico | Base": {
        "name": "Coopérnico | Base",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "Coopérnico | GO": {
        "name": "Coopérnico | GO",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "EDP | Eletricidade Indexada Horária": {
        "name": "EDP | Eletricidade Indexada Horária",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "EDP | Eletricidade Indexada Média": {
        "name": "EDP | Eletricidade Indexada Média",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "Endesa | Tarifa Indexada": {
        "name": "Endesa | Tarifa Indexada",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
        ],
    },
    "EZU | Indexada": {
        "name": "EZU | Indexada",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "G9 | Smart Dynamic": {
        "name": "G9 | Smart Dynamic",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "G9 | Smart Dynamic (Empresarial)": {
        "name": "G9 | Smart Dynamic (Empresarial)",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "G9 | Smart Index": {
        "name": "G9 | Smart Index",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "G9 | Smart Index (Empresarial)": {
        "name": "G9 | Smart Index (Empresarial)",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "Galp | Plano Flexível / Dinâmico": {
        "name": "Galp | Plano Flexível / Dinâmico",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "Goldenergy | Tarifário Indexado 100%": {
        "name": "Goldenergy | Tarifário Indexado 100%",
        "tariffs": [
            "SIMPLE",
        ],
    },
    "Ibelectra | Solução Amigo": {
        "name": "Ibelectra | Solução Amigo",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "Ibelectra | Solução Família": {
        "name": "Ibelectra | Solução Família",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "Iberdrola | Simples Indexado": {
        "name": "Iberdrola | Simples Indexado",
        "tariffs": [
            "SIMPLE",
        ],
    },
    "Iberdrola | Simples Indexado Dinâmico": {
        "name": "Iberdrola | Simples Indexado Dinâmico",
        "tariffs": [
            "SIMPLE",
        ],
    },
    "Luzboa | BTN SPOTDEF": {
        "name": "Luzboa | BTN SPOTDEF",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "LUZiGÁS | Super Lig Index": {
        "name": "LUZiGÁS | Super Lig Index",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "Meo Energia | Tarifa Dinâmica": {
        "name": "Meo Energia | Tarifa Dinâmica",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "Plenitude | Tendência": {
        "name": "Plenitude | Tendência",
        "tariffs": [
            "SIMPLE",
        ],
    },
    "Repsol | Leve PRO Sem Mais": {
        "name": "Repsol | Leve PRO Sem Mais",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "Repsol | Leve Sem Mais": {
        "name": "Repsol | Leve Sem Mais",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
}

# Migration mapping: old provider names -> new names (HuggingFace with | separator)
PROVIDER_NAME_MIGRATION: Final = {
    # Original GitHub CSV names
    "Alfa Power Index BTN": "Alfa Energia | ALFA POWER INDEX BTN",
    "Coopérnico Base": "Coopérnico | Base",
    "Coopérnico GO": "Coopérnico | GO",
    "EDP Indexada Horária": "EDP | Eletricidade Indexada Horária",
    "EZU Tarifa Coletiva": "EZU | Indexada",
    "EZU Tarifa Indexada": "EZU | Indexada",
    "G9 Smart Dynamic": "G9 | Smart Dynamic",
    "Galp Plano Dinâmico": "Galp | Plano Flexível / Dinâmico",
    "MeoEnergia Tarifa Variável": "Meo Energia | Tarifa Dinâmica",
    "Repsol Leve Sem Mais": "Repsol | Leve Sem Mais",
    # v2.3.0 names (with - separator)
    "Alfa Energia - ALFA POWER INDEX BTN": "Alfa Energia | ALFA POWER INDEX BTN",
    "EDP - Eletricidade Indexada Horária": "EDP | Eletricidade Indexada Horária",
    "EDP - Eletricidade Indexada Média": "EDP | Eletricidade Indexada Média",
    "Endesa - Tarifa Indexada": "Endesa | Tarifa Indexada",
    "EZU - Indexada": "EZU | Indexada",
    "G9 - Smart Dynamic": "G9 | Smart Dynamic",
    "G9 - Smart Dynamic (Empresarial)": "G9 | Smart Dynamic (Empresarial)",
    "G9 - Smart Index": "G9 | Smart Index",
    "G9 - Smart Index (Empresarial)": "G9 | Smart Index (Empresarial)",
    "Galp - Plano Flexível / Dinâmico": "Galp | Plano Flexível / Dinâmico",
    "Goldenergy - Tarifário Indexado 100%": "Goldenergy | Tarifário Indexado 100%",
    "Ibelectra - Solução Amigo": "Ibelectra | Solução Amigo",
    "Ibelectra - Solução Família": "Ibelectra | Solução Família",
    "Iberdrola - Simples Indexado": "Iberdrola | Simples Indexado",
    "Iberdrola - Simples Indexado Dinâmico": "Iberdrola | Simples Indexado Dinâmico",
    "Luzboa - BTN SPOTDEF": "Luzboa | BTN SPOTDEF",
    "LUZiGÁS - Super Lig Index": "LUZiGÁS | Super Lig Index",
    "Meo Energia - Tarifa Variável": "Meo Energia | Tarifa Dinâmica",
    "Plenitude - Tendência": "Plenitude | Tendência",
    "Repsol - Leve PRO Sem Mais": "Repsol | Leve PRO Sem Mais",
    "Repsol - Leve Sem Mais": "Repsol | Leve Sem Mais",
}

# Tariff display names (internal codes)
TARIFF_NAMES: Final = {
    "SIMPLE": "Simples",
    "BIHORARIO_DIARIO": "Bi-horário - Ciclo Diário",
    "BIHORARIO_SEMANAL": "Bi-horário - Ciclo Semanal",
    "TRIHORARIO_DIARIO": "Tri-horário - Ciclo Diário",
    "TRIHORARIO_DIARIO_HV": "Tri-horário > 20.7 kVA - Ciclo Diário",
    "TRIHORARIO_SEMANAL": "Tri-horário - Ciclo Semanal",
    "TRIHORARIO_SEMANAL_HV": "Tri-horário > 20.7 kVA - Ciclo Semanal",
}
