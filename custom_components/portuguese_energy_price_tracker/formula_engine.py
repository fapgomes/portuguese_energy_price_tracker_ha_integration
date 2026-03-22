"""Formula engine for calculating energy prices from OMIE data + provider constants.

Each provider has a formula (from Indexados.csv) that combines:
- OMIE market price (per-interval or monthly average)
- Provider-specific constants (margins, fees)
- Perdas (losses factor, per-interval or annual average)
- BTN profile factors (for quarter-hourly indexed providers)
"""
from __future__ import annotations

import logging
import re
from typing import Any

_LOGGER = logging.getLogger(__name__)


def calculate_price(
    formula: str,
    omie_row: dict[str, Any],
    constants: dict[str, float],
    monthly_agg: dict[str, float],
    tariff_cycle: str,
    period_type: str,
) -> float | None:
    """Calculate the final price (€/kWh, no VAT) for one 15-min interval.

    Args:
        formula: Formula string from Indexados.csv
        omie_row: One row from OMIE CSV (Data, Hora, OMIE, Perdas, BTN_A/B/C, etc.)
        constants: Provider constants from Constantes.csv
        monthly_agg: Monthly aggregates (OMIE_S_M, Perdas_Anual_S, etc.)
        tariff_cycle: Tariff cycle code (e.g., "SIMPLE", "BIHORARIO_DIARIO")
        period_type: Period type for this interval (S, V, F, P, C)

    Returns:
        Price in €/kWh (without VAT), or None if calculation fails.
    """
    try:
        omie_mwh = float(omie_row.get("OMIE", 0))
        perdas = float(omie_row.get("Perdas", 1))

        # Determine BTN profile value
        if "TRIHORARIO" in tariff_cycle:
            perfil_btn = float(omie_row.get("BTN_C", 0))
        elif "BIHORARIO" in tariff_cycle:
            perfil_btn = float(omie_row.get("BTN_B", 0))
        else:
            perfil_btn = float(omie_row.get("BTN_A", 0))

        # Build variable context for formula evaluation
        ctx: dict[str, float] = {}

        # Add all constants
        ctx.update(constants)

        # Add all monthly aggregates
        ctx.update(monthly_agg)

        # Per-interval OMIE variables
        ctx["OMIE"] = omie_mwh
        ctx["PERDAS"] = perdas
        ctx["Perfil_BTN"] = perfil_btn

        # Case-insensitive aliases used in some formulas
        ctx["Iberdrola_Q"] = constants.get("Iberdrola_Media_Q", constants.get("Iberdrola_Dinamico_Q", 0))
        ctx["Luzigas_D_K"] = constants.get("Luzigas_K", 0)
        ctx["REPSOL_FA"] = constants.get("Repsol_FA", 1)
        ctx["REPSOL_Q_Tarifa"] = constants.get("Repsol_Q_Tarifa", 0)
        ctx["REPSOL_Q_Tarifa_PRO"] = constants.get("Repsol_Q_Tarifa_Pro", 0)
        ctx["Perdas_GE"] = monthly_agg.get("Perdas_M_S", 1.16)

        # Handle multi-period formulas (e.g., Ibelectra bi-horário)
        # Format: "formula_V para Vazio; formula_FV para Fora Vazio"
        active_formula = _select_period_formula(formula, period_type)

        result = _safe_eval_formula(active_formula, ctx)
        if result is not None:
            return round(result, 6)

        return None

    except Exception as err:
        _LOGGER.warning(f"Formula calculation error: {err}, formula={formula}")
        return None


def _select_period_formula(formula: str, period_type: str) -> str:
    """Select the correct sub-formula for multi-period formulas.

    Some formulas contain multiple parts like:
    "formula_V para Vazio; formula_FV para Fora Vazio"
    """
    if " para " not in formula:
        return formula

    parts = formula.split(";")
    for part in parts:
        part = part.strip()
        formula_part = part.split(" para ")[0].strip()

        if period_type == "V" and "Vazio" in part and "Fora" not in part:
            return formula_part
        if period_type in ("F", "FV") and "Fora Vazio" in part:
            return formula_part
        if period_type == "P" and "Ponta" in part:
            return formula_part
        if period_type == "C" and "Cheias" in part:
            return formula_part

    # Default to first formula part
    return parts[0].split(" para ")[0].strip()


def _safe_eval_formula(formula: str, ctx: dict[str, float]) -> float | None:
    """Safely evaluate a formula string with the given variable context.

    Only allows arithmetic operations (+, -, *, /, parentheses) and
    variable references from the context dict.
    """
    try:
        expr = formula.strip()

        # Replace variable names with their values (longest first to avoid partial matches)
        for name in sorted(ctx.keys(), key=len, reverse=True):
            expr = expr.replace(name, str(ctx[name]))

        # Remove spaces
        expr = expr.replace(" ", "")

        # Validate: only digits, dots, arithmetic ops, parentheses
        if not re.match(r'^[\d.+\-*/()e\-]+$', expr):
            _LOGGER.warning(f"Unsafe formula expression: {expr} (from: {formula})")
            return None

        result = eval(expr)  # noqa: S307 - validated to contain only arithmetic
        return float(result)

    except Exception as err:
        _LOGGER.warning(f"Formula eval error: {err}, expr={expr}, formula={formula}")
        return None
