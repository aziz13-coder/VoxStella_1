// Safe auto-update wiring. Works when electron-updater is installed;
// otherwise becomes a no-op so builds still run without network installs.
const path = require('path');

function initAutoUpdater(ipcMain, mainWindow) {
  let autoUpdater = null;
  let log = null;
  try {
    ({ autoUpdater } = require('electron-updater'));
    log = safeRequire('electron-log');
  } catch (_err) {
    console.warn('[updater] electron-updater not installed; skipping.');
    // Expose minimal IPC that reports unavailable
    ipcMain.handle('update:check', async () => ({ available: false, reason: 'updater-not-installed' }));
    ipcMain.handle('update:restart', () => false);
    return;
  }

  if (log) {
    autoUpdater.logger = log;
    log.transports.file.level = 'info';
  }
  autoUpdater.autoDownload = true;
  const send = (channel, payload) => {
    try { mainWindow && mainWindow.webContents.send(channel, payload); } catch (_) {}
  };

  autoUpdater.on('error', (e) => send('update:error', String(e)));
  autoUpdater.on('update-available', (info) => send('update:available', info));
  autoUpdater.on('update-not-available', (info) => send('update:not-available', info));
  autoUpdater.on('download-progress', (p) => send('update:progress', p));
  autoUpdater.on('update-downloaded', (info) => send('update:downloaded', info));

  ipcMain.handle('update:check', async () => {
    try {
      await autoUpdater.checkForUpdates();
      return { ok: true };
    } catch (e) {
      return { ok: false, error: String(e) };
    }
  });

  ipcMain.handle('update:restart', () => {
    try { autoUpdater.quitAndInstall(); return true; } catch (_) { return false; }
  });
}

function safeRequire(mod) {
  try { return require(mod); } catch (_) { return null; }
}

module.exports = { initAutoUpdater };

