const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');

const {
  collectFullManifest,
  hashFile,
  verifyCopiedManifest,
} = require('./prepare-backend');

async function run() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'vox-stella-prepare-backend-'));
  const source = path.join(root, 'source');
  const destination = path.join(root, 'destination');
  fs.mkdirSync(source);
  fs.mkdirSync(destination);
  fs.writeFileSync(path.join(source, 'runtime.bin'), 'compiled-runtime');
  fs.copyFileSync(path.join(source, 'runtime.bin'), path.join(destination, 'runtime.bin'));

  const expected = crypto.createHash('sha256').update('compiled-runtime').digest('hex');
  assert.strictEqual(await hashFile(path.join(source, 'runtime.bin')), expected);

  const manifest = await collectFullManifest(source);
  const stats = { filesVerified: 0 };
  await verifyCopiedManifest(source, destination, manifest, stats, 'test runtime');
  assert.strictEqual(stats.filesVerified, 1);

  fs.writeFileSync(path.join(destination, 'runtime.bin'), 'tampered-runtime');
  await assert.rejects(
    verifyCopiedManifest(source, destination, manifest, stats, 'test runtime'),
    /mismatch/i
  );

  const packageJson = require('../package.json');
  const resources = packageJson.build.extraResources;
  assert.deepStrictEqual(resources.map((entry) => entry.from), [
    'backend/runtime/horary_backend',
  ]);
  assert.ok(!JSON.stringify(resources).includes('"from":"backend"'));

  fs.rmSync(root, { recursive: true, force: true });
  console.log('prepare-backend integrity tests passed');
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
