const http = require('http');

const DEFAULT_MAX_RESPONSE_BYTES = 1024 * 1024;

function requestJsonWithDeadline(requestUrl, {
  headers = {},
  httpModule = http,
  maxResponseBytes = DEFAULT_MAX_RESPONSE_BYTES,
  timeoutMs = 2000,
} = {}) {
  const deadlineMs = Number(timeoutMs);
  const responseLimit = Number(maxResponseBytes);
  if (!Number.isFinite(deadlineMs) || deadlineMs <= 0) {
    throw new TypeError('timeoutMs must be a positive finite number');
  }
  if (!Number.isFinite(responseLimit) || responseLimit <= 0) {
    throw new TypeError('maxResponseBytes must be a positive finite number');
  }

  return new Promise((resolve) => {
    let request = null;
    let response = null;
    let settled = false;
    let deadlineTimer = null;

    const finish = (result) => {
      if (settled) return;
      settled = true;
      if (deadlineTimer) {
        clearTimeout(deadlineTimer);
        deadlineTimer = null;
      }
      resolve(result);
    };

    const fail = (error) => {
      finish({
        ok: false,
        statusCode: response?.statusCode,
        error,
      });
    };

    const abortRequest = (error) => {
      fail(error);
      try {
        request?.destroy();
      } catch (_) {}
    };

    deadlineTimer = setTimeout(() => abortRequest('timeout'), deadlineMs);
    if (typeof deadlineTimer.unref === 'function') {
      deadlineTimer.unref();
    }

    try {
      request = httpModule.get(requestUrl, { headers }, (incoming) => {
        response = incoming;
        let body = '';
        let bodyBytes = 0;

        incoming.setEncoding('utf8');
        incoming.on('data', (chunk) => {
          if (settled) return;
          bodyBytes += Buffer.byteLength(chunk, 'utf8');
          if (bodyBytes > responseLimit) {
            abortRequest('response_too_large');
            return;
          }
          body += chunk;
        });
        incoming.on('aborted', () => fail('response_aborted'));
        incoming.on('error', (error) => {
          fail(`response_error: ${String(error?.message || error)}`);
        });
        incoming.on('close', () => {
          if (!settled && incoming.complete !== true) {
            fail('response_closed');
          }
        });
        incoming.on('end', () => {
          if (settled) return;
          try {
            finish({
              ok: incoming.statusCode === 200,
              statusCode: incoming.statusCode,
              headers: incoming.headers || {},
              payload: JSON.parse(body || '{}'),
            });
          } catch (_) {
            fail('invalid_json');
          }
        });
      });
    } catch (error) {
      fail(String(error?.message || error));
      return;
    }

    request.on('error', (error) => {
      fail(String(error?.message || error));
    });
    request.on('close', () => {
      if (!settled && !response) {
        fail('request_closed');
      }
    });
    if (typeof request.setTimeout === 'function') {
      request.setTimeout(deadlineMs, () => abortRequest('timeout'));
    }
  });
}

module.exports = {
  DEFAULT_MAX_RESPONSE_BYTES,
  requestJsonWithDeadline,
};
