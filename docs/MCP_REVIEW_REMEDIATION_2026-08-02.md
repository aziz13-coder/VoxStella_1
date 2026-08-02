# MCP review remediation — 2026-08-02

This record closes the desktop and website MCP findings identified during the 3.1.10 source and installed-build review.

| Finding | Resolution | Regression coverage |
| --- | --- | --- |
| Quoted `cmd.exe /c` examples failed in the official Node MCP client | Client configurations now point directly to `VoxStella-MCP.cmd`; Settings generates and copies the exact installed path | Direct `.cmd` launch test with `StdioClientTransport` |
| The 60-second bridge deadline could not cover three 45-second backend attempts | Bridge budget is 180 seconds; documented client budget is 210 seconds | Source contract test plus installed/fixture bridge tests |
| Website endpoint ignored invalid `MCP-Protocol-Version` | Non-initialize requests validate the header, use the mandated missing-header fallback, and return HTTP 400 for unsupported versions | Six website MCP protocol tests included in the website build |
| Website discovery stopped at `2025-06-18` and advertised empty tool/prompt capabilities | The public endpoint now negotiates the compatible `2025-11-25` revision, retains older fallbacks, and advertises resources only; it does not falsely claim the incompatible 2026 per-request era | Initialization and duplicate-card contract assertions |
| Date-only values silently became midnight | The shared MCP datetime validator requires an ISO date and time before parsing | Chart and planetary-hours date-only tests |
| Loopback and route checks ran before canonicalization | Base and final URLs are parsed before token minting; credentials, origin changes, traversal, query, fragment, and invalid encoding are rejected | Malicious URL/path matrix test |
| Cancellation did not reach backend HTTP | Tool and resource handlers pass `ctx.mcpReq.signal` through the licensed client into the HTTP helper | In-flight abort test and handler signal assertion |
| MCP card referenced a dead schema | Card now declares the current `2025-12-11/server.schema.json` registry schema | Server-card contract test |
| Customers could not discover or configure desktop MCP | Settings now shows readiness, launcher, tools, scope, copy actions, and diagnostics access | React interaction tests and rendered browser QA |
| Desktop and website MCP roles could be confused | User guide and Settings explicitly distinguish licensed local calculations from public website discovery | Documentation review and UI assertions |
| Transit scope was ambiguous | The contract explicitly states that generic timestamp charts are not transit relationships; transit scans stay in the desktop workflow until a separate versioned contract exists | Capabilities/setup scope contract and UI assertion |

## Standards comparison

The review was checked against the official MCP sources current on 2026-08-02:

- [MCP 2026-07-28 Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http): the current per-request era requires body metadata plus matching `MCP-Protocol-Version`, `Mcp-Method`, and sometimes `Mcp-Name` headers. The website endpoint therefore does not advertise this revision until it implements that complete contract.
- [MCP 2025-11-25 lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle): initialization negotiates the latest mutually supported revision and subsequent HTTP requests carry the negotiated protocol header.
- [MCP 2025-11-25 transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports): missing protocol headers fall back to `2025-03-26`, invalid versions return HTTP 400, notifications return HTTP 202, and servers validate `Origin`.
- [MCP Registry remote publishing](https://modelcontextprotocol.io/registry/remote-servers): remote cards use the `2025-12-11` schema and a `streamable-http` remote URL.
- [Official TypeScript SDK client guide](https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/client.md): requests use bounded timeouts and the SDK sends cancellation when a request expires.

## Verification commands

```powershell
C:\Python313\python.exe -m pytest -q backend\test_mcp_chart_service.py backend\test_mcp_api.py backend\test_planetary_hours.py

Set-Location frontend
node --test tests\mcpServer.test.cjs tests\electronRuntimeSecurity.test.cjs
npx vitest run --config vitest.config.mjs src\tests\mcpIntegrationSection.test.jsx

Set-Location ..\website-source
npm run test:mcp
```

The release gate should also run the complete backend and frontend suites, package through `package-app-new.bat`, and perform the licensed/unlicensed installed-state checks in `LICENSED_MCP_ARCHITECTURE_2026-08-01.md`.

## Validation result

Completed on 2026-08-02 against the 3.1.10 source tree:

- Backend: `1254 passed`; the only warning is an existing `pytz` deprecation.
- Frontend: the complete `npm test` command passed, including 29 Electron security/MCP transport tests and 562 Vitest cases across 56 files.
- Static/build gates: ESLint passed with zero warnings, `node --check` passed for the changed process entry points, `git diff --check` passed, and the production Vite build completed. The existing large-chunk advisory remains informational.
- Website: all six MCP transport/card tests passed; both public card paths validate against the live official `2025-12-11` registry schema.
- Rendered QA: the Settings MCP surface was inspected at 1280×720 and 390×844. It exposes one panel, has no horizontal overflow, and retains the complete tool, setup, and privacy-boundary content on mobile. Browser-source mode correctly disables installed-only actions.

This validation covers source behavior. A newly packaged and signed installer should use a new release version rather than silently replacing an already-published 3.1.10 artifact.
