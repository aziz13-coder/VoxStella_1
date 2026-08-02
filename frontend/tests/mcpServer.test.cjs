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
  assert.ok(
    mcpStart.indexOf('delete process.env.VOX_STELLA_MCP_BRIDGE_SECRET') <
      mcpStart.indexOf('backendProc = await startInitialBackend(logDir);'),
    'the one-time bridge secret must be deleted before the backend environment is cloned',
  );
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
    assert.deepEqual(toolList.tools.map((tool) => tool.name), [
      'get_astrological_capabilities',
      'calculate_astrological_chart',
      'get_current_astrological_positions',
      'calculate_planetary_hours',
    ]);
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
