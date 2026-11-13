"""Tests for plumetrace.db.pool that need no database."""

import pytest

from plumetrace.config import ConfigurationError, Settings
from plumetrace.db.pool import create_pool


def test_create_pool_without_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """No SUPABASE_DB_URL -> actionable ConfigurationError, no connection attempt."""
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    with pytest.raises(ConfigurationError, match="SUPABASE_DB_URL"):
        create_pool(Settings(_env_file=None))
