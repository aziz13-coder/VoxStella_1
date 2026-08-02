const path = require('node:path');
const { MCP_FEATURE_TOOL_NAMES } = require('./feature-tools');


const MCP_STARTUP_TIMEOUT_SECONDS = 210;
const MCP_TOOL_TIMEOUT_SECONDS = 300;
const MCP_TOOL_NAMES = Object.freeze([
  'get_astrological_capabilities',
  'calculate_astrological_chart',
  'get_current_astrological_positions',
  'calculate_planetary_hours',
  ...MCP_FEATURE_TOOL_NAMES,
]);
const MCP_RESOURCE_URIS = Object.freeze([
  'voxstella://capabilities',
  'voxstella://engine/version',
]);


function resolveMcpLauncherPath({ appIsPackaged, executablePath, frontendRoot }) {
  if (appIsPackaged) {
    if (typeof executablePath !== 'string' || !path.isAbsolute(executablePath)) {
      throw new TypeError('A packaged executable path is required');
    }
    return path.join(path.dirname(executablePath), 'VoxStella-MCP.cmd');
  }
  if (typeof frontendRoot !== 'string' || !path.isAbsolute(frontendRoot)) {
    throw new TypeError('An absolute frontend root is required in development');
  }
  return path.join(frontendRoot, 'packaging', 'VoxStella-MCP.cmd');
}


function buildMcpClientConfigurations(launcherPath) {
  if (typeof launcherPath !== 'string' || !path.isAbsolute(launcherPath)) {
    throw new TypeError('An absolute MCP launcher path is required');
  }
  const json = JSON.stringify({
    mcpServers: {
      'vox-stella': {
        command: launcherPath,
      },
    },
  }, null, 2);
  const codex = [
    '[mcp_servers.vox_stella]',
    `command = ${JSON.stringify(launcherPath)}`,
    `startup_timeout_sec = ${MCP_STARTUP_TIMEOUT_SECONDS}`,
    `tool_timeout_sec = ${MCP_TOOL_TIMEOUT_SECONDS}`,
  ].join('\n');
  return { json, codex };
}


function buildMcpSetupStatus({
  appIsPackaged,
  appVersion,
  launcherExists,
  launcherPath,
  licenseActive,
  platform = process.platform,
}) {
  const supported = platform === 'win32' && appIsPackaged === true;
  const configurations = buildMcpClientConfigurations(launcherPath);
  let state = 'ready';
  let detail = 'Licensed MCP is ready for local clients.';
  if (!supported) {
    state = 'installed_build_required';
    detail = 'MCP setup is available in the installed Windows application.';
  } else if (!launcherExists) {
    state = 'launcher_missing';
    detail = 'The MCP launcher is missing. Repair or reinstall Vox Stella.';
  } else if (!licenseActive) {
    state = 'license_required';
    detail = 'Activate Vox Stella before connecting an MCP client.';
  }
  return {
    ok: true,
    supported,
    ready: state === 'ready',
    state,
    detail,
    appVersion: String(appVersion || 'development'),
    launcherPath,
    launcherExists: Boolean(launcherExists),
    licenseActive: Boolean(licenseActive),
    protocolVersions: ['2026-07-28', '2025-compatible fallback'],
    tools: [...MCP_TOOL_NAMES],
    resources: [...MCP_RESOURCE_URIS],
    configurations,
    scope: {
      readOnly: true,
      excluded: [
        'horary judgments',
        'listing or searching saved charts, notes, and other user data',
        'chart, note, preference, or account mutations',
        'license identity and durable credentials',
      ],
    },
  };
}


module.exports = {
  MCP_RESOURCE_URIS,
  MCP_STARTUP_TIMEOUT_SECONDS,
  MCP_TOOL_NAMES,
  MCP_TOOL_TIMEOUT_SECONDS,
  buildMcpClientConfigurations,
  buildMcpSetupStatus,
  resolveMcpLauncherPath,
};
