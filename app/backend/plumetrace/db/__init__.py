"""Database access for PlumeTrace (local Supabase Postgres).

Only this package and the injected LangGraph checkpointer touch the database. Queries are
parameterised; schema changes happen only through migrations in ``app/supabase/migrations``.
"""
