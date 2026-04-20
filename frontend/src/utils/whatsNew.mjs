export const WHATS_NEW_STORAGE_KEY = 'vox_stella_whats_new_seen_version';

export function readSeenWhatsNewVersion(storage = globalThis?.localStorage) {
  try {
    return String(storage?.getItem?.(WHATS_NEW_STORAGE_KEY) || '').trim() || null;
  } catch (_) {
    return null;
  }
}

export function shouldShowWhatsNew(version, release, storage = globalThis?.localStorage) {
  const currentVersion = String(version || '').trim();
  if (!currentVersion || !release) return false;
  return readSeenWhatsNewVersion(storage) !== currentVersion;
}

export function markWhatsNewSeen(version, storage = globalThis?.localStorage) {
  const currentVersion = String(version || '').trim();
  if (!currentVersion) return;
  try {
    storage?.setItem?.(WHATS_NEW_STORAGE_KEY, currentVersion);
  } catch (_) {
    // Ignore storage write failures; the modal will show again next launch.
  }
}
