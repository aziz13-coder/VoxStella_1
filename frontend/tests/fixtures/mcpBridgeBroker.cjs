const net = require('node:net');

const { serveStdio, StdioServerTransport } = require('@modelcontextprotocol/server/stdio');
const { createVoxStellaMcpServer } = require('../../main/mcp/server');


const pipeName = Buffer.from(process.env.VOX_STELLA_MCP_PIPE_B64 || '', 'base64').toString('utf8');
const secret = process.env.VOX_STELLA_MCP_BRIDGE_SECRET || '';
const socket = net.createConnection(pipeName);
socket.once('connect', () => {
  socket.write(`${JSON.stringify({ protocol: 'vox-stella-mcp-bridge-v1', secret })}\n`);
  serveStdio(
    () => createVoxStellaMcpServer({
      appVersion: 'bridge-test',
      licensedBackendCall: async (pathname) => {
        if (pathname.endsWith('/capabilities')) {
          return {
            schema_version: 'voxstella.astrology.v1',
            app_version: 'bridge-test',
            license_required: true,
            tools: [],
            house_systems: [],
            bodies: { default: [], optional: [] },
            sections: [],
          };
        }
        return {};
      },
    }),
    { legacy: 'serve', transport: new StdioServerTransport(socket, socket) },
  );
});
socket.once('error', (error) => {
  process.stderr.write(`${String(error?.stack || error)}\n`);
  process.exitCode = 1;
});
