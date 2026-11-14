-- Migration: run storage (runs, detection events, downsampled readings).
-- Date: 2026-11-20. Design section 10.1. RLS on, no policies.

create table plumetrace.runs (
    run_id            uuid        primary key default gen_random_uuid(),
    scenario_id       text        not null references plumetrace.scenarios (id),
    variant_seed      bigint,
    mode              text        not null check (mode in ('live', 'record', 'eval')),
    status            text        not null check (status in
                          ('running', 'awaiting_approval', 'completed', 'aborted_budget', 'failed')),
    branch            text        check (branch in ('approve', 'reject_redraft')),
    sim_start_utc     timestamptz not null,
    started_at        timestamptz not null default now(),
    finished_at       timestamptz,
    model_fast        text,
    model_reasoning   text,
    prompt_tokens     integer     not null default 0 check (prompt_tokens >= 0),
    completion_tokens integer     not null default 0 check (completion_tokens >= 0),
    cost_usd          numeric(10, 4) not null default 0 check (cost_usd >= 0),
    langsmith_run_url text
);

create table plumetrace.events (
    event_id          bigint      generated always as identity primary key,
    run_id            uuid        not null references plumetrace.runs (run_id) on delete cascade,
    sensor_id         text        not null,
    window_index      integer     not null check (window_index >= 0),
    window_start_s    double precision not null,
    mean_ppm          double precision not null,
    baseline_ppm      double precision not null,
    cusum             double precision not null,
    downwind_of_site  boolean     not null,
    status            text        not null default 'new'
                          check (status in ('new', 'queued', 'investigating', 'closed')),
    created_at        timestamptz not null default now(),
    unique (run_id, sensor_id, window_index)
);
create index events_run_id_idx on plumetrace.events (run_id);

create table plumetrace.sensor_readings (
    run_id  uuid             not null references plumetrace.runs (run_id) on delete cascade,
    tag     text             not null,
    t_s     double precision not null,
    value   double precision,
    unit    text             not null,
    primary key (run_id, tag, t_s)
);

comment on table plumetrace.runs is 'One row per simulation/agent run; run_id = LangGraph thread_id.';
comment on table plumetrace.events is 'CUSUM detection events raised during a run.';
comment on table plumetrace.sensor_readings is '60 s mean readings per tag (methane and instruments).';

alter table plumetrace.runs enable row level security;
alter table plumetrace.events enable row level security;
alter table plumetrace.sensor_readings enable row level security;
