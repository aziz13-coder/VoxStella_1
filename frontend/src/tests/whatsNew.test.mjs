import { describe, expect, it } from 'vitest';

import packageJson from '../../package.json';
import {
  getLatestWhatsNewRelease,
  getWhatsNewRelease,
  WHATS_NEW_RELEASES,
} from '../content/whatsNew.mjs';
import {
  WHATS_NEW_STORAGE_KEY,
  markWhatsNewSeen,
  readSeenWhatsNewVersion,
  shouldShowWhatsNew,
} from '../utils/whatsNew.mjs';

function createStorage() {
  const data = new Map();
  return {
    getItem(key) {
      return data.has(key) ? data.get(key) : null;
    },
    setItem(key, value) {
      data.set(key, String(value));
    },
    removeItem(key) {
      data.delete(key);
    },
  };
}

function bumpPatchVersion(version) {
  const parts = String(version || '').split('.');
  const patchIndex = Math.max(0, parts.length - 1);
  const patch = Number.parseInt(parts[patchIndex], 10);
  parts[patchIndex] = String(Number.isFinite(patch) ? patch + 1 : 1);
  return parts.join('.');
}

describe('whats new release gating', () => {
  it('keeps an explicit release entry for the current bundled version', () => {
    expect(WHATS_NEW_RELEASES[packageJson.version]).toBeTruthy();
  });

  it('returns release content for the current bundled version', () => {
    const release = getWhatsNewRelease(packageJson.version);
    expect(release).toBeTruthy();
    expect(release.version).toBe(packageJson.version);
    expect(typeof release.summary).toBe('string');
    expect(release.items.length).toBeGreaterThan(0);
    expect(release.items[0]).toMatchObject({
      title: expect.any(String),
      body: expect.any(String),
    });
    expect(release.isFallback).toBe(false);
  });

  it('keeps the current 3.1.1 release copy product-facing', () => {
    expect(packageJson.version).toBe('3.1.1');

    const release = getWhatsNewRelease(packageJson.version);
    const copy = [
      release.headline,
      release.summary,
      release.note,
      ...release.items.flatMap((item) => [item.title, item.tag, item.body]),
    ]
      .filter(Boolean)
      .join(' ');

    expect(release.headline).toBe('Stronger activation and deeper Chinese Astrology');
    expect(copy).toContain('Activation reliability');
    expect(copy).toContain('Chinese Astrology');
    expect(copy).toContain('Relationship readings');
    expect(copy).toContain('Life timing');
    expect(copy).not.toMatch(/\b(backend|benchmark|module|filtered catalog|API)\b/i);
  });

  it('preserves the 3.1.0 release copy', () => {
    const release = getWhatsNewRelease('3.1.0');

    expect(release.version).toBe('3.1.0');
    expect(release.headline).toBe('Bug fixes');
    expect(release.summary).toContain('reliability improvements');
  });

  it('shows for a new install until the version is marked seen', () => {
    const storage = createStorage();
    const release = getWhatsNewRelease(packageJson.version);

    expect(shouldShowWhatsNew(packageJson.version, release, storage)).toBe(true);

    markWhatsNewSeen(packageJson.version, storage);

    expect(readSeenWhatsNewVersion(storage)).toBe(packageJson.version);
    expect(storage.getItem(WHATS_NEW_STORAGE_KEY)).toBe(packageJson.version);
    expect(shouldShowWhatsNew(packageJson.version, release, storage)).toBe(false);
  });

  it('falls back to the latest known release when a future version is newer than the registry', () => {
    const latest = getLatestWhatsNewRelease();
    const futureVersion = bumpPatchVersion(packageJson.version);
    const release = getWhatsNewRelease(futureVersion);

    expect(latest).toBeTruthy();
    expect(release).toBeTruthy();
    expect(release.isFallback).toBe(true);
    expect(release.requestedVersion).toBe(futureVersion);
    expect(release.sourceVersion).toBe(latest.version);
  });

  it('shows again after an update when the bundled version changes', () => {
    const storage = createStorage();
    const oldVersion = '2.0.6';
    const currentRelease = getWhatsNewRelease(packageJson.version);

    markWhatsNewSeen(oldVersion, storage);

    expect(shouldShowWhatsNew(packageJson.version, currentRelease, storage)).toBe(true);
  });
});
