import { describe, expect, it, vi } from 'vitest';
import {
  PREMIUM_UPGRADE_URL,
  redirectToPremiumUpgrade,
  shouldGatePremiumFeature,
} from '../utils/premiumAccess.mjs';

describe('premiumAccess', () => {
  it('gates premium features only for packaged unlicensed runtime', () => {
    expect(shouldGatePremiumFeature({ packagedRuntime: true, licenseActive: false })).toBe(true);
    expect(shouldGatePremiumFeature({ packagedRuntime: true, licenseActive: true })).toBe(false);
    expect(shouldGatePremiumFeature({ packagedRuntime: false, licenseActive: false })).toBe(false);
  });

  it('redirects to the premium plans page', () => {
    const openExternal = vi.fn();
    redirectToPremiumUpgrade(openExternal);
    expect(openExternal).toHaveBeenCalledWith(PREMIUM_UPGRADE_URL);
  });
});

