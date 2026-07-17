export const PREMIUM_UPGRADE_URL = 'https://voxstella.app/product';

export function shouldGatePremiumFeature({
  packagedRuntime = false,
  licenseActive = false,
  licenseChecking = false,
} = {}) {
  return Boolean(packagedRuntime && !licenseChecking && !licenseActive);
}

export function redirectToPremiumUpgrade(openExternal) {
  try {
    const openResult = openExternal?.(PREMIUM_UPGRADE_URL);
    if (openResult && typeof openResult.catch === 'function') {
      openResult.catch(() => {});
    }
  } catch (_) {}
}
