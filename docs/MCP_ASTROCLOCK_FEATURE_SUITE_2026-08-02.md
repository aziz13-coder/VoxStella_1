# MCP AstroClock feature suite — 2026-08-02

## Outcome

The licensed local MCP contract now exposes read-only tools for the requested AstroClock families:

| Family | MCP tools | Input boundary |
| --- | --- | --- |
| Synastry | `analyze_synastry` | Two explicit chart objects; no saved-chart access |
| Trait Profile | `calculate_trait_profile` | Explicit natal chart |
| Transits | `analyze_transits`, `scan_transit_window` | Explicit natal chart plus exact time or bounded window |
| Astrocartography | `analyze_astrocartography_location`, `generate_astrocartography_map`, `compare_astrocartography_locations`, `search_astrocartography_atlas` | Explicit natal chart and exact or bounded target selection; ranked atlas search also requires a canonical goal ID |
| Election | `find_election_times` | Explicit bounded scan; optional user-supplied snap IDs only for models that require participants |
| Chinese Astrology | `calculate_bazi`, `analyze_chinese_compatibility`, `cast_iching_oracle` | Explicit birth inputs or explicit oracle cast inputs |
| Forensic | `analyze_forensic_event` | Explicit event chart; symbolic analysis only |
| Certification | `run_birth_time_certification` | Explicit birth context, bounded minute range, and dated evidence events |

The four original core tools remain available. A packaged build from this source therefore advertises 18 read-only tools in total.

Every expanded feature result carries `mcp_schema_version: voxstella.features.v1` and `feature_tool`; the existing compact chart contract remains `voxstella.astrology.v1`.

## Design decisions

1. **Specific typed tools, not a generic proxy.** Each operation has a Zod input schema and structured output. Tool handlers choose fixed backend paths; callers cannot supply a route or URL.
2. **Explicit state.** Synastry and Chinese Compatibility accept complete input objects, so they do not depend on an MCP connection session or silently read saved charts. This follows the MCP rule that cross-call state must use explicit handles rather than implicit connection state.
3. **Least-privilege backend access.** The local client permits five exact core `/api/mcp/...` calculation routes plus a finite feature-route table. Every table row fixes the HTTP method and legal query keys. Unknown or encoded routes, methods, keys, URL credentials, fragments, traversal, oversized URLs, and excessive timeouts are rejected before a license token is minted.
4. **License first and per call.** MCP startup still fails closed without an active installed-device license. Every tool call mints a fresh short-lived session; durable activation data never enters tool inputs, outputs, environment configuration, or logs.
5. **Read-only and bounded.** All tools declare `readOnlyHint: true` and `destructiveHint: false`. Transit and Election windows, atlas candidate counts, Certification rows, HTTP response bytes, and request deadlines remain bounded. Election's SSE workflow is consumed locally and returned as one normal structured MCP result. Transit tools request a compact backend projection by default (`detail_level: summary`) so ordinary bounded scans stay below the bridge response limit; callers may explicitly opt into `detail_level: full`.
6. **Domain boundaries stay visible.** Forensic results are not factual evidence or suspect identification. Certification reports rectification evidence quality and is not independent documentary certification. I Ching is marked non-idempotent when it uses an unseeded cast.

## Standards checked

- [MCP 2026-07-28 server concepts](https://modelcontextprotocol.io/docs/2026-07-28/learn/server-concepts): tools are specific operations with typed inputs and outputs.
- [MCP tool specification](https://modelcontextprotocol.io/specification/draft/server/tools): tool names, JSON Schemas, output schemas, annotations, and explicit state handles.
- [MCP 2026-07-28 security best practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices): local stdio isolation, authorization, input validation, scope minimization, and protection against local-server abuse.

The desktop remains a direct stdio MCP server. The loopback backend is an internal implementation detail and requires the device-bound session issued by Electron.

## Verification

Focused coverage includes:

- strict core chart and datetime validation;
- explicit Synastry calculation with no saved-chart state;
- valid minimal inputs for all 14 new feature tools through an official in-memory MCP client;
- rejection of undeclared backend routes, wrong methods, and unknown query keys before token minting;
- fresh token minting for each permitted feature call;
- bounded Election SSE completion extraction;
- cancellation propagation;
- explicit Chinese Compatibility inputs while retaining the existing saved-snap desktop workflow;
- licensed and unlicensed `/api/mcp/synastry` route behavior;
- canonical feature suites for Synastry, Trait Profile, Transits, Astrocartography, Chinese Astrology, Certification, Forensic, and Election.

Release packaging must still run the complete gates in `docs/electron_updates.md`, followed by an installed-launcher smoke test that lists all 18 tools and calls representative lightweight and long-running tools.
