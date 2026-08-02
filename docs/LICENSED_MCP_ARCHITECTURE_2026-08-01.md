# Vox Stella licensed MCP architecture

Status: implemented in source on 2026-08-01.

## Purpose

Vox Stella exposes its astronomical calculation engine to local AI agents through Model Context Protocol (MCP). The first contract is intentionally narrow: it returns astrological positions, houses, aspects, Moon context, calculation parameters, and planetary hours. It does not expose durable license credentials, arbitrary backend routes, saved user data, or mutation tools.

The non-negotiable access invariant is:

> If the installed Vox Stella application cannot establish an active license for its current device, it must not initialize an MCP tool server and it must not perform an MCP calculation.

The MCP client configuration is not a credential. Copying it to another computer, another Windows account, or an unlicensed installation does not grant access.

## Standards baseline

The implementation uses the stable `@modelcontextprotocol/server` 2.0.0 package and its `serveStdio` entry. This supports the current MCP 2026-07-28 protocol and retains the SDK's 2025-era fallback for clients that have not migrated.

The transport follows the official MCP stdio requirements: the client launches the server, protocol messages use stdin/stdout, and all non-protocol logging goes to stderr. See:

- [MCP 2026-07-28 specification](https://modelcontextprotocol.io/specification/2026-07-28)
- [Official TypeScript SDK server documentation](https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/server.md)
- [Official 2026-07-28 stdio migration guidance](https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/migration/support-2026-07-28.md)

## Runtime flow

```mermaid
sequenceDiagram
    participant Agent as "AI agent / MCP host"
    participant Bridge as "VoxStella-MCP.cmd / stdio bridge"
    participant Electron as "Vox Stella.exe --mcp-broker"
    participant License as "Electron LicenseManager"
    participant Backend as "Private loopback backend"
    participant Engine as "Astrology engine"

    Agent->>Bridge: Launch with stdio pipes
    Bridge->>Electron: Launch hidden broker with one-time named pipe secret
    Electron->>Bridge: Authenticate private pipe
    Electron->>License: Validate signed device-bound license
    alt License inactive, expired, deactivated, or unverifiable
        License-->>Electron: No active local session
        Electron-->>Bridge: Exit without advertising tools
        Bridge-->>Agent: Close without a tool server
    else License active
        License-->>Electron: Short-lived local session available
        Electron->>Backend: Start on isolated 127.0.0.1 port
        Electron-->>Bridge: Negotiate MCP on private pipe
        Bridge-->>Agent: Advertise tools over stdio
        Agent->>Bridge: Call calculation tool
        Bridge->>Electron: Forward MCP bytes
        Electron->>License: Mint/refresh a new local session token
        Electron->>Backend: /api/mcp/* with X-License-Token
        Backend->>Backend: Verify HMAC, expiry, and device binding
        Backend->>Engine: Validate inputs and calculate
        Engine-->>Backend: Raw internal chart result
        Backend-->>Electron: Compact voxstella.astrology.v1 result
        Electron-->>Bridge: MCP structuredContent + JSON text
        Bridge-->>Agent: Forward MCP bytes
    end
```

## License enforcement

Enforcement is deliberately split across two processes.

### Electron gate

Electron is the only process that reads encrypted durable license state. In MCP mode it:

1. Initializes the same `LicenseManager` used by the desktop application.
2. Validates the packaged license trust root and device identity.
3. Calls `getStatus()` and `getToken()` before starting the backend or advertising MCP tools.
4. Calls `getToken()` again immediately before every resource read or tool call.
5. Returns a neutral `license_required` error when the license expires, is deactivated, or requires verification.

The token returned by `getToken()` is not the durable signed activation token. It is an opaque HMAC session scoped to the local backend, bound to the device, and capped to five minutes by both Electron and Python. The present Electron default is 180 seconds.

### Windows stdio bridge

Packaged Electron is a Windows GUI-subsystem executable and does not reliably retain stdin when launched directly by an MCP host. The installer therefore places `VoxStella-MCP.cmd` next to `Vox Stella.exe`. It runs the same signed Electron runtime in Node mode as a small console bridge, then launches a hidden normal Electron broker.

The two processes communicate through a random per-launch Windows named pipe authenticated by a 256-bit one-time secret delivered only in the broker child's environment and deleted after startup validation. The bridge only forwards MCP bytes and never reads license storage or receives a backend license token. Electron still performs the license-first startup and per-call token minting. MCP logs remain on stderr.

### Backend gate

All `/api/mcp/*` routes are included in `PROTECTED_ENDPOINT_PREFIXES`. Flask rejects a request before its route handler when the local session is missing, malformed, expired, overlong, or bound to another device.

The backend binds only to `127.0.0.1`. The MCP bridge can call only `/api/mcp/*`; it cannot be used as a general authenticated proxy into other Vox Stella endpoints.

### Development behavior

The desktop UI's existing source-mode convenience bypass does not apply to `--mcp`. Source-mode MCP explicitly disables `ALLOW_DEV_LICENSE_BYPASS` and `LICENSE_BYPASS` in the backend child. Tests use dependency injection and temporary HMAC sessions instead of a production bypass.

## Exposed MCP contract

### Tools

| Tool | Purpose | Time behavior |
| --- | --- | --- |
| `get_astrological_capabilities` | Returns supported schema, bodies, sections, house systems, and required inputs | Stable for an installed build |
| `calculate_astrological_chart` | Calculates a chart for an explicit ISO-8601 time and location | Deterministic for identical inputs and engine data |
| `get_current_astrological_positions` | Calculates positions for the current instant | Time-varying |
| `calculate_planetary_hours` | Calculates 24 unequal planetary hours for the selected local date | Deterministic when `datetime` is supplied |

Every tool is read-only and non-destructive. Calculation tools use Zod validation in the MCP server and repeat validation in Python.

### Resources

| URI | Content |
| --- | --- |
| `voxstella://capabilities` | Versioned supported-parameter contract |
| `voxstella://engine/version` | Installed app version, calculation schema version, and license requirement |

Resource reads are licensed calls too; they mint a fresh local backend session.

### Required location inputs

All calculation tools require:

- `latitude`: decimal degrees from -90 through 90
- `longitude`: decimal degrees from -180 through 180, east positive
- `timezone`: a valid IANA timezone such as `America/Los_Angeles`

`location` is an optional human-readable label. Coordinates are authoritative. Requiring coordinates and timezone prevents silent Greenwich defaults, network geocoding ambiguity, and daylight-saving errors.

`calculate_astrological_chart` additionally requires `datetime`. It accepts ISO-8601 timestamps with offsets. A timestamp without an offset is interpreted as local civil time in the supplied IANA timezone, with nonexistent daylight-saving wall times rejected.

### House systems

The default is Regiomontanus (`R`). Supported codes are:

| Code | System |
| --- | --- |
| `R` | Regiomontanus |
| `P` | Placidus |
| `E` | Equal |
| `W` | Whole Sign |
| `O` | Porphyry |
| `C` | Campanus |
| `K` | Koch |
| `T` | Topocentric |

### Bodies and sections

The default body set is Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, and North Node. Optional bodies are Uranus, Neptune, Pluto, and Chiron. Selecting an optional body automatically enables its engine calculation.

Selectable response sections are `metadata`, `angles`, `planets`, `houses`, `aspects`, `moon`, and `considerations`. Aspect rows are filtered so both bodies are in the requested body set.

The response schema is `voxstella.astrology.v1`. Numeric longitudes and speeds remain machine-readable; internal engine objects and license claims are not returned.

## Client configuration

On Windows, use the installed `VoxStella-MCP.cmd` launcher as the MCP command. Do not point a client directly at `Vox Stella.exe` because a GUI-subsystem process may lose stdin, and do not point it at `horary_backend.exe`; direct backend access has no durable-license authority and is intentionally rejected.

Replace the command with the actual installation path chosen by the user.

### JSON-style MCP clients

```json
{
  "mcpServers": {
    "vox-stella": {
      "command": "C:\\Windows\\System32\\cmd.exe",
      "args": [
        "/d",
        "/s",
        "/c",
        "\"C:\\Users\\YOUR_USER\\AppData\\Local\\Programs\\Vox Stella\\VoxStella-MCP.cmd\""
      ]
    }
  }
}
```

### Codex TOML

```toml
[mcp_servers.vox_stella]
command = 'C:\Windows\System32\cmd.exe'
args = ['/d', '/s', '/c', '"C:\Users\YOUR_USER\AppData\Local\Programs\Vox Stella\VoxStella-MCP.cmd"']
startup_timeout_sec = 60
tool_timeout_sec = 120
```

Activate Vox Stella normally in the desktop application before the first MCP launch. Closing the desktop window does not remove the encrypted activation. MCP can also run while the desktop UI is open because MCP processes intentionally do not join the UI single-instance lock.

## Error contract

| Condition | Behavior |
| --- | --- |
| No active license at startup | Process exits before tool advertisement |
| License expires or is deactivated after startup | The next call fails with a neutral license error |
| Missing/invalid backend session | Backend returns HTTP 402/403; Electron maps it to `license_required` |
| Bad coordinates, timezone, time, body, section, or house code | Tool error with a bounded correction message |
| Calculation failure | Tool error without license token or internal object disclosure |
| Oversized/partial/non-JSON backend response | Bounded bridge error and aborted request |

## Source map

| Source | Responsibility |
| --- | --- |
| `frontend/main.js` | `--mcp-broker` headless lifecycle, license-first startup, private pipe, and backend lifetime |
| `frontend/main/license.js` | Encrypted durable token ownership and local session minting |
| `frontend/main/mcp/server.js` | MCP v2 tools, resources, Zod schemas, stdio era negotiation |
| `frontend/main/mcp/licensed-backend-client.js` | Fresh-token-per-call policy and restricted backend client |
| `frontend/main/mcp/stdio-bridge.js` | Windows console stdio to authenticated named-pipe proxy |
| `frontend/packaging/VoxStella-MCP.cmd` | Installed MCP launcher |
| `frontend/main/backend-http.js` | Deadline, response-size, GET/POST JSON transport |
| `backend/app.py` | Global license middleware and MCP blueprint registration |
| `backend/mcp_api.py` | Private licensed HTTP routes |
| `backend/mcp_chart_service.py` | Public input validation, engine invocation, compact versioned output |

## Verification and release gates

Run the focused tests:

```powershell
python -m pytest -q backend/test_mcp_chart_service.py backend/test_mcp_api.py backend/test_planetary_hours.py
Set-Location frontend
node --test tests/electronRuntimeSecurity.test.cjs tests/mcpServer.test.cjs
```

The test coverage includes:

- a fixed Jerusalem chart with known engine positions;
- parameter boundaries and required location context;
- complete 24-hour planetary-hour output;
- missing, expired, and valid device-bound local license sessions;
- a fresh session token on every backend call;
- no token detail in MCP license errors;
- Zod rejection before backend invocation;
- MCP tools/resources through an in-memory client;
- a real child-process stdio negotiation proving the 2026 protocol path while legacy fallback remains enabled; and
- a Windows console-bridge round trip through an authenticated private broker pipe.

Before a release, also run the full backend/frontend suites, package only through `package-app-new.bat`, then test the packaged executable in these states:

1. Licensed installation: tools list and a known chart call succeed.
2. Desktop UI already open: a separate MCP process succeeds.
3. Unlicensed clean user-data directory: process exits without tools.
4. Deactivated or expired license during an open MCP session: next call fails.
5. Captured stdout: every line is valid MCP protocol data; diagnostics appear only on stderr.

## Deliberate non-goals for the first release

- No remote Streamable HTTP endpoint.
- No API keys separate from the Vox Stella device license.
- No activation, purchase, deactivation, or license-status tools.
- No file, snap, notebook, or user-data access.
- No chart mutation or forensic-judgment tools.
- No durable tokens, license IDs, device IDs, emails, or customer identity in MCP results.

Future tools should reuse the same license-first startup, per-call token minting, `/api/mcp/*` backend guard, strict input schema, and compact versioned output pattern.
