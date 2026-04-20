export const PREMIUM_UPGRADE_URL = 'https://voxstella.app/product';

export function shouldGatePremiumFeature({
  packagedRuntime = false,
  licenseActive = false,
} = {}) {
  return Boolean(packagedRuntime && !licenseActive);
}

export function redirectToPremiumUpgrade(openExternal) {
  try {
    openExternal?.(PREMIUM_UPGRADE_URL);
  } catch (_) {}
}

