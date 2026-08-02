# Vox Stella MCP user guide

## What Vox Stella provides

The installed Windows application includes a licensed, local Model Context Protocol server. It lets compatible AI clients request read-only calculations from the same packaged astrology engine used by Vox Stella.

This desktop MCP server is different from `https://voxstella.app/mcp`. The website endpoint exposes only public documentation and discovery resources. It never exposes the licensed calculation engine.

## Requirements

1. Install a Vox Stella Windows build whose MCP Settings panel lists the feature tool you want to use.
2. Open the desktop application and activate the license on that device.
3. Open **Settings → Model Context Protocol (MCP)**.
4. Confirm the status says **Ready**.
5. Copy the JSON or Codex configuration and paste it into the MCP client.
6. Restart or reconnect the MCP client.

The generated configuration points directly to `VoxStella-MCP.cmd`. Do not add `cmd.exe /c` around it; Node-based hosts may pass the required quotes literally when the installation path contains spaces.

## Exposed tools

- `get_astrological_capabilities`
- `calculate_astrological_chart`
- `get_current_astrological_positions`
- `calculate_planetary_hours`
- `analyze_synastry`
- `calculate_trait_profile`
- `analyze_transits`
- `scan_transit_window`
- `analyze_astrocartography_location`
- `generate_astrocartography_map`
- `compare_astrocartography_locations`
- `search_astrocartography_atlas`
- `find_election_times`
- `calculate_bazi`
- `analyze_chinese_compatibility`
- `cast_iching_oracle`
- `analyze_forensic_event`
- `run_birth_time_certification`

The server also exposes `voxstella://capabilities` and `voxstella://engine/version` resources.

All tools are read-only. Every resource read and tool call requires the active device license and mints a new short-lived local backend session.

## Calculation inputs

Calculation tools require explicit, typed context. Western chart workflows use an ISO-8601 date/time, latitude, longitude, and an IANA timezone. Chinese Astrology uses an explicit birth date, optional birth time, coordinates, and timezone. Date-only values are accepted only by schemas that genuinely operate on a civil date, such as a BaZi birth date; Western event and natal chart timestamps require a time.

A timestamp with a UTC offset describes an exact instant. A timestamp without an offset is interpreted as civil time in the supplied IANA timezone; nonexistent and ambiguous daylight-saving times are rejected by the core chart contract.

Synastry accepts two explicit chart objects and does not create or read saved charts. Trait Profile, Transits, Astrocartography, and Forensic likewise accept explicit chart context. Election accepts explicit scan bounds and may accept a user-supplied saved-chart ID only for desktop models that require a selected participant or natal chart. The server never lists saved charts for an agent.

Transit, Election, Astrocartography atlas, and Certification calculations are bounded. MCP defaults to compact outputs where the desktop workflow offers a series toggle; callers must deliberately request larger series data.

Ranked Astrocartography atlas searches require a canonical `goal_id` (for example `love`, `career`, `home`, `education`, or `travel_relax`). Their resolution is one of `coarse`, `standard`, `fine`, or `ultra`, and each call returns at most 20 ranked locations.

## Deliberate boundary

The MCP contract exposes licensed, read-only calculations for Synastry, Trait Profile, Transits, Astrocartography, Election, Chinese Astrology, Forensic, and Certification. It does not list or search saved charts and notes, mutate chart or account state, expose license identity, reveal durable credentials, or expose horary judgments.

Feature tools call only fixed backend routes declared in the MCP bridge. There is no generic route, URL, SQL, filesystem, or command parameter. Each request is schema-validated before a fresh short-lived device-bound session is minted.

Forensic output is symbolic astrological analysis, not factual evidence, a determination of guilt, or a safe basis for identifying a suspect. Birth-time Certification reports the engine's evidence-quality classification; rectification output must not be represented as independent documentary certification.

## Troubleshooting

- **Setup required / license required:** activate or verify the license in Settings, then reconnect the MCP client.
- **Launcher missing:** use **Show launcher** in Settings. If the file is missing, repair or reinstall Vox Stella.
- **Startup timeout:** use at least 210 seconds. The bridge allows the packaged backend to complete all readiness retries.
- **Tool timeout:** use at least 300 seconds for bounded scans and Certification.
- **Connection closes immediately:** open the desktop application and inspect Settings and diagnostics logs. An inactive license intentionally exits before tools are advertised.
- **Invalid datetime:** include both date and time, plus an offset or a valid IANA timezone.

The desktop application can remain open while an MCP client runs. MCP brokers are deliberately separate from the UI single-instance process.

## Security model

- Durable license material remains inside Electron.
- MCP traffic uses stdio through an authenticated, one-time named pipe bridge.
- The calculation backend binds only to `127.0.0.1` on an isolated port.
- The bridge canonicalizes the final URL before attaching a short-lived token and permits only `/api/mcp/*` plus an exact method-and-query allowlist for the requested read-only AstroClock feature routes.
- Cancellation closes pending local HTTP requests.
- Credentials, device identifiers, email addresses, saved data, and arbitrary backend routes are not exposed.
