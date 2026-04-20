export const HORARY_ACTIVATION_REQUIRED_MESSAGE =
  'Activate Vox Stella in Settings to cast charts in the packaged app.';

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
} = {}) {
  if (loading) return 'Casting chart in progress...';
  if (requiresActivation) return HORARY_ACTIVATION_REQUIRED_MESSAGE;
  if (!String(question || '').trim()) return 'Enter your question first.';
  if (!String(location || '').trim()) return 'Enter a location first.';
  return '';
}
