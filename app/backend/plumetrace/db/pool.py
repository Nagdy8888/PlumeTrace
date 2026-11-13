"""Connection pool factory for the local Supabase Postgres."""

from psycopg_pool import ConnectionPool

from plumetrace.config import Settings, require_db_url


def create_pool(settings: Settings, *, min_size: int = 1, max_size: int = 5) -> ConnectionPool:
    """Create and open a connection pool to the local database.

    Args:
        settings: Settings holding ``SUPABASE_DB_URL``.
        min_size: Connections kept open at minimum.
        max_size: Maximum number of connections.

    Returns:
        An open ``ConnectionPool``. The caller closes it.

    Raises:
        ConfigurationError: If ``SUPABASE_DB_URL`` is not set (raised before any connection).
    """
    url = require_db_url(settings)
    return ConnectionPool(conninfo=url, min_size=min_size, max_size=max_size, open=True)
