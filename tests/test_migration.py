"""Tests for the provider name migration map."""
from __future__ import annotations

from conftest import PKG_DIR, load_providers

NS = load_providers()
PROVIDERS = NS["PROVIDERS"]
MIGRATION = NS["PROVIDER_NAME_MIGRATION"]


def test_every_migration_target_is_a_current_provider():
    """The map is applied in a single hop, so every target must be final."""
    stale = {old: new for old, new in MIGRATION.items() if new not in PROVIDERS}
    assert not stale


def test_current_providers_are_not_migrated():
    assert not set(MIGRATION) & set(PROVIDERS)


def test_removed_tariffs_are_migrated():
    assert MIGRATION["Coopérnico | Base"] == "Coopérnico | Único"
    assert MIGRATION["Coopérnico | GO"] == "Coopérnico | Único"
    assert MIGRATION["G9 | Smart Dynamic SPOT 8! (Empresarial)"] == "G9 | Smart Dynamic SPOT 8!"


def test_migration_v9_exists():
    src = (PKG_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "if migration_version < 9:" in src
