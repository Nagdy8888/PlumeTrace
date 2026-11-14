# Security

Reference for security controls as they exist in the code. The process (quick gate, full gate,
hardening phase, release gate) is described in the `security-checks` project skill; this page
records what the code does today and is extended by later tasks. It states only what is
implemented.

## Outbound network

Status on 2026-11-14: the repository makes exactly **one** kind of outbound call, to the free
public Open-Meteo archive API. No call to OpenAI or LangSmith exists in the code yet (only their
settings names are in `config.py`); when they are added, they get a row here in the same change.

| Call | Host | Where in the code | When it runs | Data sent | Data received |
|---|---|---|---|---|---|
| Historical weather | `archive-api.open-meteo.com` (HTTPS) | `plumetrace/data_sources/open_meteo.py`, started by `scripts/fetch_weather.py` | Only when a developer runs the script by hand to refresh the snapshot. The backend and the tests never call it | Latitude and longitude of the fictional KS-07 site, a date range, the five weather variable names, `wind_speed_unit=ms`, `timezone=UTC` | Hourly ERA5 weather (public data, CC BY 4.0) |

Controls in `data_sources/open_meteo.py`:

- **Fixed host.** The URL is the constant `ARCHIVE_URL`. No part of it comes from user input, a
  request, a database row or a file, so there is no server-side request forgery path.
- **Timeout.** Every request passes `timeout=TIMEOUT_S` (20 s). A timeout is raised to the
  caller (`httpx.TimeoutException`), never swallowed or retried silently.
- **TLS is verified.** The module and the script use the httpx default (certificate verification
  on) and never pass a `verify` argument. A test fails if the word appears in either file.
- **No secret and no user data in the request.** The API needs no key. The query holds only the
  parameters in the table above (a test asserts the exact set of query names and that no
  `Authorization` header is sent). The `User-Agent` is the httpx default (`python-httpx/<version>`);
  no name, email or machine identifier is added. The server that answers sees the IP address of the
  machine that runs the script, as with any HTTP request.
- **Errors are visible.** A non-2xx status raises `httpx.HTTPStatusError`. A `null` value, a
  missing field, a gap or shift in the time axis, an unphysical value or a wind unit other than m/s
  raises `OpenMeteoError`. `fetch_weather.py` then prints the reason to stderr, exits 1 and writes
  nothing, so a failed refresh never leaves a partial or altered snapshot.
- **No network in tests.** The Open-Meteo tests and the script tests use `httpx.MockTransport`.

The committed snapshot is generated output. It is read by `plumetrace/simulator/weather.py`, which
rejects a file with gaps, so a bad snapshot cannot reach a scenario.

Licence and terms (checked against the Open-Meteo licence and terms pages on 2026-11-14): the API
data is offered under CC BY 4.0, free of charge for non-commercial use within the published rate
limits, which the single manual fetch of one week is far below. The attribution text is stored in
the snapshot and must be shown, with a link to <https://open-meteo.com/>, wherever the weather data
is displayed.
