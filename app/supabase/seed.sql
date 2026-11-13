-- Seed data: reference rows only (no secrets, no personal data).
insert into plumetrace.scenarios (id, title, seed, version, is_mvp) values
    ('s1_rod_packing',      'Rod packing failure, K-202',         101, 1, true),
    ('s4_planned_blowdown', 'Planned blowdown, compressor K-201', 104, 1, true),
    ('s5_sensor_drift',     'Sensor drift, AT-106',               105, 1, true)
on conflict (id) do nothing;
