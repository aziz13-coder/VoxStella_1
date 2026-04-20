/*
  Lightweight icon validator for packaging.
  - Warns if expected icon files are missing, but never exits non-zero.
*/
const fs = require('fs');
const path = require('path');

const root = __dirname;
const assets = path.join(root, 'assets');

const expected = {
  mac: path.join(assets, 'icon.icns'),
  win: path.join(assets, 'icon.ico'),
  linux: path.join(assets, 'icon.png'),
};

function exists(p) {
  try { return fs.existsSync(p); } catch { return false; }
}

let ok = true;
if (!exists(expected.mac)) {
  console.warn(`[validate-icons] Warning: Missing mac icon: ${expected.mac}`);
  ok = false;
}
if (!exists(expected.win)) {
  // Fallbacks users might already have
  const fallbacks = [path.join(assets, 'voxstella-favicon.png'), path.join(assets, 'voxstella-logo.png')];
  const hasFallback = fallbacks.some(exists);
  console.warn(`[validate-icons] Warning: Missing Windows .ico: ${expected.win}${hasFallback ? ' (PNG fallback present)' : ''}`);
  ok = false;
}
if (!exists(expected.linux)) {
  const maybe = path.join(assets, 'voxstella-logo.png');
  console.warn(`[validate-icons] Warning: Missing Linux icon: ${expected.linux}${exists(maybe) ? ` (found ${maybe})` : ''}`);
  ok = false;
}

if (!ok) {
  console.warn('[validate-icons] Proceeding without strict icon validation. Electron-builder may use defaults or fallbacks.');
}
process.exit(0);

