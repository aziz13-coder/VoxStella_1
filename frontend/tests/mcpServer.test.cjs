const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const test = require('node:test');

const path = require('node:path');

const { Client, InMemoryTransport } = require('@modelcontextprotocol/client');
const { StdioClientTransport } = require('@modelcontextprotocol/client/stdio');

const { requestJson } = require('../main/backend-http');
const {
  LicensedMcpAccessError,
  assertLicensedMcpAccess,
  createLicensedBackendClient,
} = require('../main/mcp/licensed-backend-client');
const { createVoxStellaMcpServer } = require('../main/mcp/server');
const {
  MCP_STARTUP_TIMEOUT_SECONDS,
  MCP_TOOL_NAMES,
  MCP_TOOL_TIMEOUT_SECONDS,
  buildMcpClientConfigurations,
  buildMcpSetupStatus,
  resolveMcpLauncherPath,
} = require('../main/mcp/setup');


function listen(server) {
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      server.removeListener('error', reject);
      resolve(server.address().port);
    });
  });
}


test('JSON helper sends bounded POST bodies and parses the response', async () => {
  let received = null;
  const server = http.createServer((request, response) => {
    let body = '';
    request.setEncoding('utf8');
    request.on('data', (chunk) => { body += chunk; });
    request.on('end', () => {
      received = {
        method: request.method,
        contentType: request.headers['content-type'],
        body: JSON.parse(body),
      };
      response.writeHead(200, { 'Content-Type': 'application/json' });
      response.end(JSON.stringify({ success: true, data: { ok: true } }));
    });
  });
  const port = await listen(server);
  try {
    const result = await requestJson(`http://127.0.0.1:${port}/api/mcp/chart`, {
      method: 'POST',
      body: { latitude: 31.7 },
      timeoutMs: 2000,
    });
    assert.equal(result.ok, true);
    assert.deepEqual(received, {
      method: 'POST',
      contentType: 'application/json',
      body: { latitude: 31.7 },
    });
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});


test('JSON helper aborts an in-flight backend request when MCP is cancelled', async () => {
  const server = http.createServer(() => {});
  const port = await listen(server);
  const controller = new AbortController();
  try {
    const pending = requestJson(`http://127.0.0.1:${port}/api/mcp/chart`, {
      method: 'POST',
      body: {},
      signal: controller.signal,
      timeoutMs: 5000,
    });
    controller.abort();
    const result = await pending;
    assert.equal(result.ok, false);
    assert.equal(result.error, 'aborted');
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});


test('packaging installs the console bridge and broker secrets cannot reach the backend child', () => {
  const packageJson = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'package.json'), 'utf8'));
  const launcher = fs.readFileSync(
    path.join(__dirname, '..', 'packaging', 'VoxStella-MCP.cmd'),
    'utf8',
  );
  const mainSource = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  const mcpStart = mainSource.slice(mainSource.indexOf('async function startMcpApplication()'));

  assert.equal(packageJson.build.asarUnpack.includes('main/mcp/stdio-bridge.js'), true);
  assert.equal(
    packageJson.build.extraFiles.some((entry) => entry.to === 'VoxStella-MCP.cmd'),
    true,
  );
  assert.match(launcher, /ELECTRON_RUN_AS_NODE=1/);
  assert.match(launcher, /app\.asar\.unpacked\\main\\mcp\\stdio-bridge\.js/);
  const bridgeSource = fs.readFileSync(
    path.join(__dirname, '..', 'main', 'mcp', 'stdio-bridge.js'),
    'utf8',
  );
  assert.match(bridgeSource, /DEFAULT_CONNECT_TIMEOUT_MS = 180000/);
  assert.ok(
    mcpStart.indexOf('delete process.env.VOX_STELLA_MCP_BRIDGE_SECRET') <
      mcpStart.indexOf('backendProc = await startInitialBackend(logDir);'),
    'the one-time bridge secret must be deleted before the backend environment is cloned',
  );
});


test('MCP setup emits direct, quote-safe client configurations and readiness state', () => {
  const launcherPath = resolveMcpLauncherPath({
    appIsPackaged: true,
    executablePath: 'C:\\Program Files\\Vox Stella\\Vox Stella.exe',
    frontendRoot: path.join(__dirname, '..'),
  });
  const configurations = buildMcpClientConfigurations(launcherPath);
  const json = JSON.parse(configurations.json);

  assert.equal(launcherPath, 'C:\\Program Files\\Vox Stella\\VoxStella-MCP.cmd');
  assert.deepEqual(json.mcpServers['vox-stella'], { command: launcherPath });
  assert.doesNotMatch(configurations.json, /cmd\.exe|\"\\\"C:/i);
  assert.match(configurations.codex, /^command = "C:\\\\Program Files/m);
  assert.equal(MCP_STARTUP_TIMEOUT_SECONDS, 210);

  const setup = buildMcpSetupStatus({
    appIsPackaged: true,
    appVersion: '3.1.10',
    launcherExists: true,
    launcherPath,
    licenseActive: true,
    platform: 'win32',
  });
  assert.equal(setup.ready, true);
  assert.deepEqual(setup.tools, [...MCP_TOOL_NAMES]);
  assert.equal(setup.tools.length, 18);
  assert.equal(MCP_TOOL_TIMEOUT_SECONDS, 300);
  assert.equal(setup.scope.excluded.some((value) => value.includes('saved charts')), true);
});


test('licensed backend client canonicalizes loopback URLs before attaching a token', async () => {
  let tokenCalls = 0;
  const licenseManager = {
    getToken: async () => { tokenCalls += 1; return 'short-session'; },
  };

  assert.throws(
    () => createLicensedBackendClient({
      apiBaseUrl: 'http://127.0.0.1:123@evil.example',
      licenseManager,
    }),
    /IPv4 loopback/,
  );

  const call = createLicensedBackendClient({
    apiBaseUrl: 'http://127.0.0.1:52525',
    licenseManager,
    requestJsonImpl: async () => {
      throw new Error('request must not be reached');
    },
  });
  for (const pathname of [
    '/api/mcp/../../api/calculate-chart',
    '/api/mcp/%2F..%2Fapi/calculate-chart',
    '/api/%6dcp/chart',
    '/api/mcp/%63hart',
    '/api/mcp/private-future-operation',
    '/api/astro-clock/%74raits/profile',
    '//evil.example/api/mcp/chart',
    '/api/mcp/chart?redirect=1',
  ]) {
    await assert.rejects(call(pathname, {}), /licensed feature allowlist/);
  }
  assert.equal(tokenCalls, 0);
});


test('MCP startup fails closed before advertising tools without an active license', async () => {
  let tokenCalls = 0;
  const licenseManager = {
    getStatus: async () => ({ active: false }),
    getToken: async () => { tokenCalls += 1; return 'must-not-be-read'; },
  };

  await assert.rejects(
    assertLicensedMcpAccess(licenseManager),
    (error) => error instanceof LicensedMcpAccessError && error.code === 'license_required',
  );
  assert.equal(tokenCalls, 0);
});


test('licensed backend client mints a fresh local session for every MCP call', async () => {
  const observedTokens = [];
  let tokenCounter = 0;
  const call = createLicensedBackendClient({
    apiBaseUrl: 'http://127.0.0.1:52525',
    licenseManager: {
      getToken: async () => `short-session-${++tokenCounter}`,
    },
    requestJsonImpl: async (_url, options) => {
      observedTokens.push(options.headers['X-License-Token']);
      return {
        ok: true,
        statusCode: 200,
        payload: { success: true, data: { schema_version: 'test.v1' } },
      };
    },
  });

  await call('/api/mcp/capabilities', undefined, { method: 'GET' });
  await call('/api/mcp/chart', { latitude: 0, longitude: 0 });

  assert.deepEqual(observedTokens, ['short-session-1', 'short-session-2']);
});


test('licensed backend client permits only declared feature routes, methods, and query keys', async () => {
  const observed = [];
  const call = createLicensedBackendClient({
    apiBaseUrl: 'http://127.0.0.1:52525',
    licenseManager: { getToken: async () => 'short-session' },
    requestJsonImpl: async (url, options) => {
      observed.push({ url: String(url), options });
      return { ok: true, statusCode: 200, payload: { success: true, data: { top_traits: [] } } };
    },
  });

  await call('/api/astro-clock/traits/profile', undefined, {
    method: 'GET',
    query: {
      datetime: '2026-08-01T12:00:00+03:00',
      latitude: 31.778,
      longitude: 35.235,
      special_degree: ['25 Leo', '0 Aries'],
    },
  });
  assert.match(observed[0].url, /special_degree=25\+Leo&special_degree=0\+Aries/);
  assert.equal(observed[0].options.headers['X-License-Token'], 'short-session');

  await assert.rejects(
    call('/api/astro-clock/traits/profile', undefined, { method: 'POST' }),
    /method is not allowed/,
  );
  await assert.rejects(
    call('/api/astro-clock/traits/profile', undefined, {
      method: 'GET', query: { arbitrary_backend_path: '/api/secrets' },
    }),
    /query parameter is not allowed/,
  );
  await assert.rejects(
    call('/api/astro-clock/snaps', undefined, { method: 'GET' }),
    /licensed feature allowlist/,
  );
});


test('licensed backend client extracts the completed bounded election SSE result', async () => {
  const call = createLicensedBackendClient({
    apiBaseUrl: 'http://127.0.0.1:52525',
    licenseManager: { getToken: async () => 'short-session' },
    requestTextImpl: async () => ({
      ok: true,
      statusCode: 200,
      payload: [
        'data: {"type":"progress","progress":0.5}',
        '',
        'data: {"type":"done","data":{"matter":"contract","top":[]}}',
        '',
      ].join('\n'),
    }),
  });

  const result = await call('/api/astro-clock/election/suggest/stream', undefined, {
    method: 'GET',
    query: { matter: 'contract', start: '2026-08-01T00:00:00Z', end: '2026-08-01T01:00:00Z' },
    responseType: 'sse',
    timeoutMs: 300000,
  });
  assert.deepEqual(result, { matter: 'contract', top: [] });
});


test('licensed backend client converts backend license rejection to a neutral MCP error', async () => {
  const call = createLicensedBackendClient({
    apiBaseUrl: 'http://127.0.0.1:52525',
    licenseManager: { getToken: async () => 'sensitive-session-token' },
    requestJsonImpl: async () => ({
      ok: false,
      statusCode: 403,
      payload: { error: 'license_invalid', detail: 'bad sensitive-session-token' },
    }),
  });

  await assert.rejects(
    call('/api/mcp/chart', {}),
    (error) => (
      error instanceof LicensedMcpAccessError &&
      error.code === 'license_required' &&
      !error.message.includes('sensitive-session-token')
    ),
  );
});


test('MCP protocol exposes versioned read-only tools and resources', async () => {
  const calls = [];
  const licensedBackendCall = async (pathname, body, options) => {
    calls.push({ pathname, body, options });
    if (pathname.endsWith('/capabilities')) {
      return {
        schema_version: 'voxstella.astrology.v1',
        app_version: '3.1.9',
        license_required: true,
        tools: [],
        house_systems: [],
        bodies: { default: [], optional: [] },
        sections: [],
      };
    }
    if (pathname.endsWith('/traits/profile')) {
      return { summary: {}, top_traits: [], traits: [] };
    }
    if (pathname.endsWith('/election/suggest/stream')) {
      return { matter: 'contract', top: [] };
    }
    return {
      schema_version: 'voxstella.astrology.v1',
      calculation: {
        timestamp: body.datetime,
        location: body.location || '31.778, 35.235',
        timezone: body.timezone,
        latitude: body.latitude,
        longitude: body.longitude,
      },
      planets: [],
    };
  };
  const server = createVoxStellaMcpServer({ appVersion: '3.1.9', licensedBackendCall });
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  const client = new Client({ name: 'vox-stella-test', version: '1.0.0' });
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
  try {
    const toolList = await client.listTools();
    assert.deepEqual(toolList.tools.map((tool) => tool.name), [...MCP_TOOL_NAMES]);
    assert.equal(toolList.tools.every((tool) => tool.annotations.readOnlyHint === true), true);

    const chartResult = await client.callTool({
      name: 'calculate_astrological_chart',
      arguments: {
        datetime: '2026-08-01T14:30:00+03:00',
        latitude: 31.778,
        longitude: 35.235,
        timezone: 'Asia/Jerusalem',
      },
    });
    assert.equal(chartResult.structuredContent.schema_version, 'voxstella.astrology.v1');
    assert.equal(calls.at(-1).pathname, '/api/mcp/chart');
    assert.equal(calls.at(-1).body.house_system_code, 'R');
    assert.equal(calls.at(-1).options.signal instanceof AbortSignal, true);

    const traitResult = await client.callTool({
      name: 'calculate_trait_profile',
      arguments: {
        datetime: '1990-01-01T12:00:00+02:00',
        location: 'Jerusalem, Israel',
        timezone: 'Asia/Jerusalem',
        latitude: 31.778,
        longitude: 35.235,
      },
    });
    assert.deepEqual(traitResult.structuredContent.top_traits, []);
    assert.equal(traitResult.structuredContent.mcp_schema_version, 'voxstella.features.v1');
    assert.equal(traitResult.structuredContent.feature_tool, 'calculate_trait_profile');
    assert.equal(calls.at(-1).pathname, '/api/astro-clock/traits/profile');
    assert.equal(calls.at(-1).options.method, 'GET');
    assert.equal(calls.at(-1).options.query.house_system_code, 'R');

    await client.callTool({
      name: 'find_election_times',
      arguments: {
        matter: 'contract',
        start: '2026-08-01T10:00:00+03:00',
        end: '2026-08-01T12:00:00+03:00',
        location: 'Jerusalem, Israel',
        timezone: 'Asia/Jerusalem',
        latitude: 31.778,
        longitude: 35.235,
      },
    });
    assert.equal(calls.at(-1).pathname, '/api/astro-clock/election/suggest/stream');
    assert.equal(calls.at(-1).options.responseType, 'sse');
    assert.equal(calls.at(-1).options.query.include_series, '0');

    const resources = await client.listResources();
    assert.deepEqual(resources.resources.map((resource) => resource.uri), [
      'voxstella://capabilities',
      'voxstella://engine/version',
    ]);
    const capabilities = await client.readResource({ uri: 'voxstella://capabilities' });
    const parsed = JSON.parse(capabilities.contents[0].text);
    assert.equal(parsed.license_required, true);
  } finally {
    await client.close();
  }
});


test('MCP protocol rejects incomplete calculation input before the backend', async () => {
  let calls = 0;
  const server = createVoxStellaMcpServer({
    appVersion: '3.1.9',
    licensedBackendCall: async () => { calls += 1; return {}; },
  });
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  const client = new Client({ name: 'vox-stella-test', version: '1.0.0' });
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
  try {
    const result = await client.callTool({
      name: 'calculate_astrological_chart',
      arguments: { datetime: '2026-08-01T14:30:00+03:00', timezone: 'UTC' },
    });
    assert.equal(result.isError, true);
    assert.equal(calls, 0);
  } finally {
    await client.close();
  }
});


test('every licensed feature tool accepts its documented minimal explicit input', async () => {
  const calls = [];
  const server = createVoxStellaMcpServer({
    appVersion: '3.1.11',
    licensedBackendCall: async (pathname, body, options) => {
      calls.push({ pathname, body, options });
      return { ok: true, pathname };
    },
  });
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  const client = new Client({ name: 'vox-stella-feature-test', version: '1.0.0' });
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
  const chart = {
    datetime: '1990-01-01T12:00:00+02:00',
    location: 'Jerusalem, Israel',
    timezone: 'Asia/Jerusalem',
    latitude: 31.778,
    longitude: 35.235,
  };
  const natal = {
    natal_datetime: chart.datetime,
    natal_location: chart.location,
    natal_timezone: chart.timezone,
    latitude: chart.latitude,
    longitude: chart.longitude,
  };
  const birth = {
    date: '1990-01-01',
    time: '12:00',
    location: chart.location,
    timezone: chart.timezone,
    latitude: chart.latitude,
    longitude: chart.longitude,
  };
  const featureCalls = [
    ['analyze_synastry', { chart_a: { label: 'A', ...chart }, chart_b: { label: 'B', ...chart, datetime: '1992-06-15T18:30:00+03:00' } }],
    ['calculate_trait_profile', chart],
    ['analyze_transits', { ...natal, transit_datetime: '2026-08-01T12:00:00+03:00' }],
    ['scan_transit_window', { ...natal, start: '2026-08-01T10:00:00+03:00', end: '2026-08-01T12:00:00+03:00' }],
    ['analyze_astrocartography_location', { ...natal, target_location: 'London, UK', target_latitude: 51.5074, target_longitude: -0.1278 }],
    ['generate_astrocartography_map', natal],
    ['compare_astrocartography_locations', { ...natal, targets: [
      { location: 'London, UK', latitude: 51.5074, longitude: -0.1278 },
      { location: 'Paris, France', latitude: 48.8566, longitude: 2.3522 },
    ] }],
    ['search_astrocartography_atlas', { ...natal, goal_id: 'love' }],
    ['find_election_times', { matter: 'contract', start: '2026-08-01T10:00:00+03:00', end: '2026-08-01T12:00:00+03:00', location: chart.location, timezone: chart.timezone, latitude: chart.latitude, longitude: chart.longitude }],
    ['calculate_bazi', { birth }],
    ['analyze_chinese_compatibility', { primary: birth, relationship: { ...birth, date: '1992-06-15' } }],
    ['cast_iching_oracle', { method: 'manual', lines: [7, 8, 7, 8, 7, 8] }],
    ['analyze_forensic_event', chart],
    ['run_birth_time_certification', {
      birth: { date: '1990-01-01', location: chart.location, timezone: chart.timezone, latitude: chart.latitude, longitude: chart.longitude },
      search: { start_time: '11:55', end_time: '12:05' },
      events: [{ label: 'Documented event', timestamp: '2020-01-01T12:00:00+02:00', latitude: chart.latitude, longitude: chart.longitude, timezone: chart.timezone }],
    }],
  ];

  try {
    for (const [name, args] of featureCalls) {
      const result = await client.callTool({ name, arguments: args });
      assert.notEqual(result.isError, true, `${name} rejected its minimal documented input`);
      assert.equal(result.structuredContent.mcp_schema_version, 'voxstella.features.v1');
      assert.equal(result.structuredContent.feature_tool, name);
    }
    assert.equal(calls.length, featureCalls.length);
  } finally {
    await client.close();
  }
});


test('stdio entry negotiates the current 2026 protocol and retains legacy fallback', async () => {
  const client = new Client(
    { name: 'vox-stella-modern-test', version: '1.0.0' },
    { versionNegotiation: { mode: 'auto' } },
  );
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [path.join(__dirname, 'fixtures', 'mcpProtocolServer.cjs')],
    stderr: 'pipe',
  });
  await client.connect(transport, { timeout: 10000 });
  try {
    assert.equal(client.getProtocolEra(), 'modern');
    const toolList = await client.listTools();
    assert.equal(toolList.tools.some((tool) => tool.name === 'calculate_astrological_chart'), true);
  } finally {
    await client.close();
  }
});


test('official Node MCP client can launch the documented direct Windows batch command', {
  skip: process.platform !== 'win32',
}, async () => {
  const client = new Client(
    { name: 'vox-stella-direct-launch-test', version: '1.0.0' },
    { versionNegotiation: { mode: 'auto' } },
  );
  const transport = new StdioClientTransport({
    command: path.join(__dirname, 'fixtures', 'mcpDirectLauncher.cmd'),
    stderr: 'pipe',
  });
  await client.connect(transport, { timeout: 10000 });
  try {
    assert.equal(client.getProtocolEra(), 'modern');
    const tools = await client.listTools();
    assert.equal(tools.tools.length, 18);
  } finally {
    await client.close();
  }
});


test('Windows console bridge preserves MCP stdio through a private broker pipe', {
  skip: process.platform !== 'win32',
}, async () => {
  const client = new Client(
    { name: 'vox-stella-bridge-test', version: '1.0.0' },
    { versionNegotiation: { mode: 'auto' } },
  );
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [
      path.join(__dirname, '..', 'main', 'mcp', 'stdio-bridge.js'),
      `--target-exe=${process.execPath}`,
      `--target-app=${path.join(__dirname, 'fixtures', 'mcpBridgeBroker.cjs')}`,
    ],
    stderr: 'pipe',
  });
  await client.connect(transport, { timeout: 15000 });
  try {
    assert.equal(client.getProtocolEra(), 'modern');
    const capabilities = await client.callTool({
      name: 'get_astrological_capabilities',
      arguments: {},
    });
    assert.equal(capabilities.structuredContent.app_version, 'bridge-test');
  } finally {
    await client.close();
  }
});
