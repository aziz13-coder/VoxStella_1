const fs = require('fs');
const path = require('path');

function validatePackagedBackendSmoke(versionPayload, healthPayload, {
  expectedVersion,
  expectedCommit = '',
  requireCleanBuild = false,
} = {}) {
  const errors = [];
  const backendBuild = versionPayload?.backend_build;
  const buildGit = backendBuild?.git;
  const commit = typeof buildGit?.commit === 'string' ? buildGit.commit.trim() : '';
  const normalizedExpectedCommit = String(expectedCommit || '').trim();
  if (!expectedVersion) {
    errors.push('expected application version is missing');
  } else if (versionPayload?.app_version !== expectedVersion) {
    errors.push(`backend app_version ${versionPayload?.app_version || 'missing'} does not match ${expectedVersion}`);
  }
  if (
    typeof versionPayload?.app_version !== 'string' ||
    !versionPayload.app_version.trim() ||
    typeof versionPayload?.api_version !== 'string' ||
    !versionPayload.api_version.trim()
  ) {
    errors.push('version endpoint is missing app/api version fields');
  }
  if (backendBuild?.metadata_source !== 'file') {
    errors.push(`backend metadata source is ${backendBuild?.metadata_source || 'missing'}, expected file`);
  }
  if (backendBuild?.runtime_kind !== 'pyinstaller_bundle') {
    errors.push(`backend runtime kind is ${backendBuild?.runtime_kind || 'missing'}, expected pyinstaller_bundle`);
  }
  if (!/^[0-9a-f]{40}$/i.test(commit)) {
    errors.push('backend build metadata is missing a full Git commit');
  }
  if (
    normalizedExpectedCommit &&
    commit.toLowerCase() !== normalizedExpectedCommit.toLowerCase()
  ) {
    errors.push(`backend commit ${commit || 'missing'} does not match expected ${normalizedExpectedCommit}`);
  }
  if (requireCleanBuild && buildGit?.dirty !== false) {
    errors.push('backend build metadata is not clean');
  }
  if (healthPayload?.ready !== true || healthPayload?.status === 'unhealthy') {
    errors.push(`backend health is not ready (${healthPayload?.status || 'missing'})`);
  }
  if (expectedVersion && healthPayload?.version !== expectedVersion) {
    errors.push(`health version ${healthPayload?.version || 'missing'} does not match ${expectedVersion}`);
  }
  const healthCommit = healthPayload?.backend_build?.git?.commit;
  if (healthCommit !== commit) {
    errors.push('health and version endpoints report different backend commits');
  }
  return {
    ok: errors.length === 0,
    errors,
    appVersion: versionPayload?.app_version || null,
    apiVersion: versionPayload?.api_version || null,
    commit: commit || null,
    tree: buildGit?.tree || null,
    dirty: typeof buildGit?.dirty === 'boolean' ? buildGit.dirty : null,
  };
}

function writeSmokeResultFile(configuredPath, payload) {
  const targetValue = String(configuredPath || '').trim();
  if (!targetValue) return null;
  if (!path.isAbsolute(targetValue)) {
    throw new Error('VOX_STELLA_SMOKE_RESULT_PATH must be absolute');
  }
  const targetPath = path.resolve(targetValue);
  const parentDir = path.dirname(targetPath);
  fs.mkdirSync(parentDir, { recursive: true });
  const tempPath = `${targetPath}.${process.pid}.tmp`;
  const document = {
    schemaVersion: 1,
    ...payload,
  };
  fs.writeFileSync(tempPath, `${JSON.stringify(document, null, 2)}\n`, {
    encoding: 'utf8',
    flag: 'wx',
  });
  try {
    if (fs.existsSync(targetPath)) fs.unlinkSync(targetPath);
    fs.renameSync(tempPath, targetPath);
  } catch (error) {
    try { fs.unlinkSync(tempPath); } catch (_) {}
    throw error;
  }
  return targetPath;
}

module.exports = {
  validatePackagedBackendSmoke,
  writeSmokeResultFile,
};
