# Vox Stella MCP user guide

## What Vox Stella provides

The installed Windows application includes a licensed, local Model Context Protocol server. It lets compatible AI clients request read-only calculations from the same packaged astrology engine used by Vox Stella.

This desktop MCP server is different from `https://voxstella.app/mcp`. The website endpoint exposes only public documentation and discovery resources. It never exposes the licensed calculation engine.

## Requirements

1. Install Vox Stella 3.1.10 or later on Windows.
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

The server also exposes `voxstella://capabilities` and `voxstella://engine/version` resources.

All tools are read-only. Every resource read and tool call requires the active device license and mints a new short-lived local backend session.

## Calculation inputs

Calculation tools require explicit latitude, longitude, and an IANA timezone. Chart calculation also requires an ISO-8601 date and time. Date-only values such as `2026-08-01` are rejected rather than interpreted as midnight.

A timestamp with a UTC offset describes an exact instant. A timestamp without an offset is interpreted as civil time in the supplied IANA timezone; nonexistent and ambiguous daylight-saving times are rejected.

## Deliberate boundary

The MCP contract does not expose saved charts, notes, license identity, horary judgments, synastry, or transit relationship/window scans. Those workflows remain inside the desktop application until each can be published as a separate, versioned, compact, and testable contract. A generic chart at a requested timestamp must not be presented as a natal-to-transit analysis.

## Troubleshooting

- **Setup required / license required:** activate or verify the license in Settings, then reconnect the MCP client.
- **Launcher missing:** use **Show launcher** in Settings. If the file is missing, repair or reinstall Vox Stella.
- **Startup timeout:** use at least 210 seconds. The bridge allows the packaged backend to complete all readiness retries.
- **Tool timeout:** use at least 120 seconds.
- **Connection closes immediately:** open the desktop application and inspect Settings and diagnostics logs. An inactive license intentionally exits before tools are advertised.
- **Invalid datetime:** include both date and time, plus an offset or a valid IANA timezone.

The desktop application can remain open while an MCP client runs. MCP brokers are deliberately separate from the UI single-instance process.

## Security model

- Durable license material remains inside Electron.
- MCP traffic uses stdio through an authenticated, one-time named pipe bridge.
- The calculation backend binds only to `127.0.0.1` on an isolated port.
- The bridge canonicalizes the final URL before attaching a short-lived token and permits only `/api/mcp/*`.
- Cancellation closes pending local HTTP requests.
- Credentials, device identifiers, email addresses, saved data, and arbitrary backend routes are not exposed.
