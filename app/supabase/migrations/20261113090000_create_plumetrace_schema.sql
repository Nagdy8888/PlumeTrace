-- Migration: create the plumetrace schema and the scenarios catalogue.
-- Date: 2026-11-13. Design: docs/superpowers/specs/2026-11-12-plumetrace-design.md section 10.1.
-- Rules: RLS on every table, no anon/authenticated policies (only the backend, as the database
-- owner, reads and writes). Never edit this file after it has been applied; add a new migration.

create schema if not exists plumetrace;

create table plumetrace.scenarios (
    id          text        primary key check (id ~ '^s[0-9]+_[a-z0-9_]+$'),
    title       text        not null,
    seed        bigint      not null,
    version     integer     not null default 1,
    is_mvp      boolean     not null,
    created_at  timestamptz not null default now()
);

comment on table plumetrace.scenarios is 'Scenario catalogue (S1-S6). Seeded; read by the backend.';

alter table plumetrace.scenarios enable row level security;
