import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { LicenseTokenProvider, VoxStellaAPI } from '../App.jsx';

function localSessionToken(id, exp) {
  const claims = {
    token_type: 'local_license_session',
    lic: id,
    exp,
    next_verify_at: exp,
  };
  return `signature.${btoa(JSON.stringify(claims))}`;
}

describe('horary license session refresh', () => {
  beforeEach(() => {
    LicenseTokenProvider.invalidate();
    window.API_BASE_URL = 'http://127.0.0.1:52525';
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    LicenseTokenProvider.invalidate();
    delete window.electronAPI;
    delete window.API_BASE_URL;
    delete window.IS_PACKAGED;
  });

  it('refreshes the renderer session and retries once after an auth-expiry response', async () => {
    const now = Math.floor(Date.now() / 1000);
    const expiredSession = localSessionToken('local-session:old', now + 180);
    const refreshedSession = localSessionToken('local-session:new', now + 180);
    window.electronAPI = {
      getLicenseToken: vi
        .fn()
        .mockResolvedValueOnce(expiredSession)
        .mockResolvedValueOnce(refreshedSession),
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 403,
        json: async () => ({
          error: 'license_invalid',
          detail: 'local license session expired',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ judgment: 'yes' }),
      });
    vi.stubGlobal('fetch', fetchMock);

    const result = await VoxStellaAPI.request('/api/calculate-chart', {
      method: 'POST',
      body: JSON.stringify({ question: 'Will this retry?' }),
    });

    expect(result).toEqual({ judgment: 'yes' });
    expect(window.electronAPI.getLicenseToken).toHaveBeenCalledTimes(2);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe(`Bearer ${expiredSession}`);
    expect(fetchMock.mock.calls[1][1].headers.Authorization).toBe(`Bearer ${refreshedSession}`);
  });

  it('uses the configured browser-development token for strict-license requests', async () => {
    vi.stubEnv('VITE_DEV_LICENSE_TOKEN', '  strict-browser-token  ');
    window.IS_PACKAGED = false;
    delete window.electronAPI;
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ judgment: 'yes' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await VoxStellaAPI.request('/api/calculate-chart', {
      method: 'POST',
      body: JSON.stringify({ question: 'Will strict browser licensing work?' }),
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe(
      'Bearer strict-browser-token'
    );
  });

  it('omits fake bearer credentials when browser development uses backend bypass', async () => {
    vi.stubEnv('VITE_DEV_LICENSE_TOKEN', '');
    window.IS_PACKAGED = false;
    delete window.electronAPI;
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ judgment: 'yes' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await VoxStellaAPI.request('/api/calculate-chart', {
      method: 'POST',
      body: JSON.stringify({ question: 'Will bypass mode omit auth?' }),
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][1].headers).not.toHaveProperty('Authorization');
  });
});
