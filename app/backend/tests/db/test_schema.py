"""Schema tests against the local Supabase Postgres (design section 10.1)."""

import psycopg


def test_every_plumetrace_table_has_rls(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """RLS is enabled on every table in schema plumetrace."""
    rows = db_conn.execute(
        "select c.relname, c.relrowsecurity from pg_class c "
        "join pg_namespace n on n.oid = c.relnamespace "
        "where n.nspname = 'plumetrace' and c.relkind = 'r'"
    ).fetchall()
    assert rows, "schema plumetrace has no tables"
    assert all(rls for _, rls in rows), rows


def test_no_client_policies_exist(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """No RLS policies are defined: only the backend (owner) accesses the tables."""
    count = db_conn.execute(
        "select count(*) from pg_policies where schemaname = 'plumetrace'"
    ).fetchone()
    assert count == (0,)


def test_mvp_scenarios_are_seeded(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """The three MVP scenarios exist after migrations + seed."""
    ids = {r[0] for r in db_conn.execute("select id from plumetrace.scenarios").fetchall()}
    assert ids == {"s1_rod_packing", "s4_planned_blowdown", "s5_sensor_drift"}
