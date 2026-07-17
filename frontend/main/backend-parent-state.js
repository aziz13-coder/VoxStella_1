const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

function normalizeProcessId(value) {
  const pid = Number(value);
  if (!Number.isSafeInteger(pid) || pid <= 0) {
    throw new TypeError('Backend parent state requires a positive process ID');
  }
  return pid;
}

function normalizeInstanceId(value) {
  const instanceId = String(value || '').trim();
  if (!/^[A-Za-z0-9_-]{8,128}$/.test(instanceId)) {
    throw new TypeError('Backend parent state requires a safe instance ID');
  }
  return instanceId;
}

function createBackendParentState(baseDir, options = {}) {
  if (typeof baseDir !== 'string' || !baseDir.trim()) {
    throw new TypeError('Backend parent state requires a base directory');
  }

  const pid = normalizeProcessId(options.pid ?? process.pid);
  const instanceId = normalizeInstanceId(
    options.instanceId || crypto.randomBytes(16).toString('hex'),
  );
  const stateFile = path.join(
    baseDir,
    `backend-parent-state-${pid}-${instanceId}.json`,
  );
  const temporaryFile = `${stateFile}.tmp`;
  let cleaned = false;

  fs.mkdirSync(baseDir, { recursive: true });

  const removeFile = (filePath) => {
    try {
      fs.unlinkSync(filePath);
    } catch (error) {
      if (error?.code !== 'ENOENT') throw error;
    }
  };

  return {
    instanceId,
    pid,
    stateFile,
    temporaryFile,
    write(updatedAtMs = Date.now()) {
      if (cleaned) {
        throw new Error('Backend parent state has already been cleaned up');
      }
      const payload = JSON.stringify({
        pid,
        instance_id: instanceId,
        updated_at_ms: updatedAtMs,
      });
      try {
        fs.writeFileSync(temporaryFile, payload, {
          encoding: 'utf8',
          flag: 'w',
        });
        fs.renameSync(temporaryFile, stateFile);
      } catch (error) {
        try {
          removeFile(temporaryFile);
        } catch (_) {}
        throw error;
      }
    },
    cleanup() {
      cleaned = true;
      removeFile(temporaryFile);
      removeFile(stateFile);
    },
  };
}

module.exports = {
  createBackendParentState,
};
