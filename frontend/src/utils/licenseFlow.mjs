export const HORARY_ACTIVATION_REQUIRED_MESSAGE =
  'Activate Vox Stella in Settings to cast charts in the packaged app.';

export const HORARY_API_OFFLINE_MESSAGE =
  'Horary engine is offline. Reconnect the backend before casting a chart.';

export function requiresHoraryActivation({
  licenseActive = false,
  packagedRuntime = false,
  devLicenseRuntime = false,
} = {}) {
  return Boolean(packagedRuntime && !devLicenseRuntime && !licenseActive);
}

export function getHorarySubmitDisabledReason({
  loading = false,
  question = '',
  location = '',
  requiresActivation = false,
  apiStatus = '',
} = {}) {
  if (loading) return 'Casting chart in progress...';
  if (requiresActivation) return HORARY_ACTIVATION_REQUIRED_MESSAGE;
  if (!String(question || '').trim()) return 'Enter your question first.';
  if (!String(location || '').trim()) return 'Enter a location first.';
  if (apiStatus === 'offline') return HORARY_API_OFFLINE_MESSAGE;
  return '';
}
