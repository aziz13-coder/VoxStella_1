const http = require('http');

const DEFAULT_MAX_RESPONSE_BYTES = 1024 * 1024;

function requestBody(requestUrl, {
  body,
  headers = {},
  httpModule = http,
  maxResponseBytes = DEFAULT_MAX_RESPONSE_BYTES,
  method = 'GET',
  responseType = 'json',
  signal,
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
  const normalizedMethod = String(method || 'GET').trim().toUpperCase();
  if (!/^[A-Z]+$/.test(normalizedMethod)) {
    throw new TypeError('method must be an HTTP method token');
  }
  if (responseType !== 'json' && responseType !== 'text') {
    throw new TypeError('responseType must be json or text');
  }
  let encodedBody = null;
  if (body !== undefined) {
    encodedBody = Buffer.from(JSON.stringify(body), 'utf8');
  }

  return new Promise((resolve) => {
    let request = null;
    let response = null;
    let settled = false;
    let deadlineTimer = null;
    let abortListener = null;

    const finish = (result) => {
      if (settled) return;
      settled = true;
      if (deadlineTimer) {
        clearTimeout(deadlineTimer);
        deadlineTimer = null;
      }
      if (signal && abortListener) {
        signal.removeEventListener('abort', abortListener);
        abortListener = null;
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
    if (signal) {
      if (typeof signal.addEventListener !== 'function' || typeof signal.removeEventListener !== 'function') {
        finish({ ok: false, error: 'invalid_abort_signal' });
        return;
      }
      abortListener = () => abortRequest('aborted');
      if (signal.aborted) {
        abortListener();
        return;
      }
      signal.addEventListener('abort', abortListener, { once: true });
    }

    try {
      const requestHeaders = { ...headers };
      if (encodedBody) {
        if (!Object.keys(requestHeaders).some((key) => key.toLowerCase() === 'content-type')) {
          requestHeaders['Content-Type'] = 'application/json';
        }
        requestHeaders['Content-Length'] = String(encodedBody.length);
      }
      const requestOptions = { headers: requestHeaders, method: normalizedMethod };
      const onResponse = (incoming) => {
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
          if (responseType === 'text') {
            finish({
              ok: incoming.statusCode === 200,
              statusCode: incoming.statusCode,
              headers: incoming.headers || {},
              payload: body,
            });
            return;
          }
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
      };
      if (normalizedMethod === 'GET' && encodedBody === null && typeof httpModule.get === 'function') {
        request = httpModule.get(requestUrl, requestOptions, onResponse);
      } else {
        request = httpModule.request(requestUrl, requestOptions, onResponse);
        if (encodedBody) request.write(encodedBody);
        request.end();
      }
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

function requestJson(requestUrl, options = {}) {
  return requestBody(requestUrl, { ...options, responseType: 'json' });
}

function requestText(requestUrl, options = {}) {
  return requestBody(requestUrl, { ...options, responseType: 'text' });
}

function requestJsonWithDeadline(requestUrl, options = {}) {
  return requestJson(requestUrl, { ...options, method: 'GET' });
}

module.exports = {
  DEFAULT_MAX_RESPONSE_BYTES,
  requestJson,
  requestJsonWithDeadline,
  requestText,
};
