"""Test setup: load the integration modules without Home Assistant installed."""
from __future__ import annotations

import csv
import sys
import types
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parent.parent
PKG_DIR = ROOT / "custom_components" / "portuguese_energy_price_tracker"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
TZ = ZoneInfo("Europe/Lisbon")


def _stub_homeassistant() -> None:
    """Minimal stubs for the homeassistant helpers used by the pure modules."""
    ha = types.ModuleType("homeassistant")
    util = types.ModuleType("homeassistant.util")
    dt = types.ModuleType("homeassistant.util.dt")
    dt.now = lambda: datetime.now(TZ)
    dt.as_local = lambda d: d.replace(tzinfo=TZ) if d.tzinfo is None else d.astimezone(TZ)
    file = types.ModuleType("homeassistant.util.file")
    file.write_utf8_file = lambda p, c: Path(p).write_text(c, encoding="utf-8")
    util.dt, util.file = dt, file
    sys.modules.setdefault("homeassistant", ha)
    sys.modules.setdefault("homeassistant.util", util)
    sys.modules.setdefault("homeassistant.util.dt", dt)
    sys.modules.setdefault("homeassistant.util.file", file)


def _load_package() -> None:
    """Register the integration directory as package 'pept' without running __init__.py."""
    pkg = types.ModuleType("pept")
    pkg.__path__ = [str(PKG_DIR)]
    sys.modules["pept"] = pkg


_stub_homeassistant()
_load_package()


def load_providers() -> dict:
    """Read PROVIDERS and PROVIDER_NAME_MIGRATION from const.py (it imports homeassistant.const)."""
    src = (PKG_DIR / "const.py").read_text(encoding="utf-8")
    ns: dict = {}
    for name in ("PROVIDERS", "PROVIDER_NAME_MIGRATION"):
        start = src.index(f"{name}: Final = {{")
        end = src.index("\n}\n", start) + 3
        exec(src[start:end].replace(f"{name}: Final =", f"{name} ="), ns)  # noqa: S102
    return ns


@pytest.fixture(scope="session")
def constants() -> dict[str, float]:
    """Constants from a snapshot of upstream Constantes.csv."""
    result = {}
    with open(FIXTURES / "Constantes.csv", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                result[row["constante"].strip()] = float(row["valor_unitário"])
            except ValueError:
                continue
    return result
