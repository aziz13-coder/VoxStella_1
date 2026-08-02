const { serveStdio } = require('@modelcontextprotocol/server/stdio');
const { createVoxStellaMcpServer } = require('../../main/mcp/server');


const licensedBackendCall = async (pathname, body) => {
  if (pathname.endsWith('/capabilities')) {
    return {
      schema_version: 'voxstella.astrology.v1',
      app_version: 'test',
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
      timestamp: body?.datetime || 'current',
      location: body?.location || 'test',
      timezone: body?.timezone || 'UTC',
      latitude: body?.latitude || 0,
      longitude: body?.longitude || 0,
    },
  };
};

serveStdio(
  () => createVoxStellaMcpServer({ appVersion: 'test', licensedBackendCall }),
  { legacy: 'serve' },
);
