function focusWindow(targetWindow) {
  if (!targetWindow || targetWindow.isDestroyed?.()) return false;

  if (targetWindow.isMinimized?.()) {
    targetWindow.restore?.();
  }
  if (targetWindow.isVisible?.() === false) {
    targetWindow.show?.();
  }
  targetWindow.focus?.();
  return true;
}

function acquireSingleInstanceLock(
  app,
  getMainWindow,
  { onWindowUnavailable } = {},
) {
  if (!app || typeof app.requestSingleInstanceLock !== 'function') {
    throw new TypeError('Electron app single-instance API is unavailable');
  }

  const acquired = app.requestSingleInstanceLock();
  if (!acquired) return false;

  app.on('second-instance', () => {
    const targetWindow = typeof getMainWindow === 'function' ? getMainWindow() : null;
    if (!focusWindow(targetWindow) && typeof onWindowUnavailable === 'function') {
      onWindowUnavailable();
    }
  });
  return true;
}

module.exports = {
  acquireSingleInstanceLock,
  focusWindow,
};
