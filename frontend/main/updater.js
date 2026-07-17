// Safe auto-update wiring. Works when electron-updater is installed;
// otherwise reports an explicit terminal state to the renderer.

function normalizeError(error) {
  if (error instanceof Error) return error.message || String(error);
  return String(error || 'Unknown updater error');
}

function initAutoUpdater(ipcMain, windowOrGetter, options = {}) {
  const getMainWindow = typeof windowOrGetter === 'function'
    ? windowOrGetter
    : () => windowOrGetter;
  const authorizeIpc = typeof options.authorizeIpc === 'function'
    ? options.authorizeIpc
    : () => true;
  const send = (channel, payload) => {
    try {
      const targetWindow = getMainWindow();
      if (!targetWindow || targetWindow.isDestroyed?.()) return false;
      const contents = targetWindow.webContents;
      if (!contents || contents.isDestroyed?.()) return false;
      contents.send(channel, payload);
      return true;
    } catch (_) {
      return false;
    }
  };
  const registerHandler = (channel, handler) => {
    ipcMain.handle(channel, async (event, ...args) => {
      if (!authorizeIpc(event)) {
        return { ok: false, error: 'unauthorized_sender' };
      }
      return handler(event, ...args);
    });
  };

  let autoUpdater = Object.prototype.hasOwnProperty.call(options, 'autoUpdater')
    ? options.autoUpdater
    : null;
  let log = Object.prototype.hasOwnProperty.call(options, 'log')
    ? options.log
    : null;
  if (!Object.prototype.hasOwnProperty.call(options, 'autoUpdater')) {
    try {
      ({ autoUpdater } = require('electron-updater'));
      log = safeRequire('electron-log');
    } catch (_err) {
      autoUpdater = null;
    }
  }

  if (!autoUpdater) {
    console.warn('[updater] electron-updater not installed; skipping.');
    registerHandler('update:check', async () => {
      const error = 'Automatic updates are unavailable in this build';
      send('update:error', error);
      return { ok: false, available: false, reason: 'updater-not-installed', error };
    });
    registerHandler('update:restart', async () => ({ ok: false, error: 'updater-not-installed' }));
    return { available: false };
  }

  if (log) {
    autoUpdater.logger = log;
    if (log.transports?.file) log.transports.file.level = 'info';
  }
  autoUpdater.autoDownload = true;

  autoUpdater.on('error', (error) => send('update:error', normalizeError(error)));
  autoUpdater.on('update-available', (info) => send('update:available', info));
  autoUpdater.on('update-not-available', (info) => send('update:not-available', info));
  autoUpdater.on('download-progress', (progress) => send('update:progress', progress));
  autoUpdater.on('update-downloaded', (info) => send('update:downloaded', info));

  registerHandler('update:check', async () => {
    try {
      await autoUpdater.checkForUpdates();
      return { ok: true };
    } catch (error) {
      const message = normalizeError(error);
      send('update:error', message);
      return { ok: false, error: message };
    }
  });

  registerHandler('update:restart', async () => {
    try {
      autoUpdater.quitAndInstall();
      return { ok: true };
    } catch (error) {
      const message = normalizeError(error);
      send('update:error', message);
      return { ok: false, error: message };
    }
  });
  return { available: true };
}

function safeRequire(mod) {
  try {
    return require(mod);
  } catch (_) {
    return null;
  }
}

module.exports = {
  initAutoUpdater,
  normalizeError,
};
