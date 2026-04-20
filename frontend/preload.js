// Preload: expose API base to the renderer without enabling nodeIntegration
const { contextBridge, ipcRenderer } = require('electron');

const PORT = process.env.HORARY_PORT ? Number(process.env.HORARY_PORT) : 52525;
const API_BASE_URL = process.env.API_BASE_URL || `http://127.0.0.1:${PORT}`;
const IS_PACKAGED = process.env.APP_IS_PACKAGED === '1' || process.env.NODE_ENV === 'production';
const DEV_LICENSE_BYPASS = process.env.ALLOW_DEV_LICENSE_BYPASS === '1';
const allowDevBypass = !IS_PACKAGED && DEV_LICENSE_BYPASS;
const onChannel = (channel, cb) => {
  if (typeof cb !== 'function') return () => {};
  const handler = (_event, payload) => cb(payload);
  ipcRenderer.on(channel, handler);
  return () => ipcRenderer.removeListener(channel, handler);
};
const invokeWithStartupRetry = async (channel, ...args) => {
  try {
    return await ipcRenderer.invoke(channel, ...args);
  } catch (error) {
    const msg = String(error?.message || error || '');
    if (!/No handler registered/i.test(msg)) throw error;
    await new Promise((resolve) => setTimeout(resolve, 120));
    return ipcRenderer.invoke(channel, ...args);
  }
};

contextBridge.exposeInMainWorld('API_BASE_URL', API_BASE_URL);
contextBridge.exposeInMainWorld('IS_PACKAGED', IS_PACKAGED);

// Expose minimal, promise-based bridge for updates and licensing
contextBridge.exposeInMainWorld('electronAPI', {
  // Updates
  checkForUpdates: () => ipcRenderer.invoke('update:check'),
  restartToUpdate: () => ipcRenderer.invoke('update:restart'),
  onUpdateAvailable: (cb) => onChannel('update:available', cb),
  onUpdateNotAvailable: (cb) => onChannel('update:not-available', cb),
  onUpdateError: (cb) => onChannel('update:error', cb),
  onUpdateProgress: (cb) => onChannel('update:progress', cb),
  onUpdateDownloaded: (cb) => onChannel('update:downloaded', cb),

  // Licensing
  getLicenseStatus: () => {
    if (allowDevBypass) return Promise.resolve({ active: true, plan: 'dev' });
    return invokeWithStartupRetry('license:get-status');
  },
  activateLicense: (payload) => {
    if (allowDevBypass) return Promise.resolve({ ok: true, status: { active: true, plan: 'dev' } });
    return invokeWithStartupRetry('license:activate', payload);
  },
  deactivateLicense: () => {
    if (allowDevBypass) return Promise.resolve({ ok: true });
    return invokeWithStartupRetry('license:deactivate');
  },
  getLicenseToken: () => {
    if (allowDevBypass) return Promise.resolve('dev-token');
    return invokeWithStartupRetry('license:get-token');
  },
  verifyLicense: () => {
    if (allowDevBypass) return Promise.resolve({ ok: true });
    return invokeWithStartupRetry('license:verify');
  },
  getBackendStatus: () => invokeWithStartupRetry('backend:get-status'),
  refreshBackendStatus: () => invokeWithStartupRetry('backend:refresh-status'),
  onBackendStatus: (cb) => onChannel('backend:status', cb),
  openExternal: (url) => ipcRenderer.invoke('shell:open-external', url),

  // Reporting
  exportReport: (payload) => ipcRenderer.invoke('report:export', payload),
});
