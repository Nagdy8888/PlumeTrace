"""Fixtures for tests that need the local Supabase Postgres.

Locally, the tests skip with a hint when the database is not running. In
`python scripts/ci_local.py --full` the stage sets PLUMETRACE_REQUIRE_DB=1, which turns the same
condition into a failure.
"""

import os
from collections.abc import Iterator

import psycopg
import pytest

from plumetrace.config import ConfigurationError, get_settings, require_db_url

START_HINT = "Supabase not running: run `npx --yes supabase@3.1.0 start` in app/"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark every test in this folder with the `db` marker."""
    for item in items:
        if "tests/db/" in item.nodeid.replace("\\", "/"):
            item.add_marker(pytest.mark.db)


@pytest.fixture
def db_conn() -> Iterator[psycopg.Connection[tuple[object, ...]]]:
    """Yield a connection to the local database, or skip/fail when it is unavailable."""
    try:
        url = require_db_url(get_settings())
        conn = psycopg.connect(url, connect_timeout=3)
    except (ConfigurationError, psycopg.OperationalError) as exc:
        if os.environ.get("PLUMETRACE_REQUIRE_DB") == "1":
            pytest.fail(f"database required but unavailable: {exc}")
        pytest.skip(START_HINT)
    try:
        yield conn
    finally:
        conn.close()
