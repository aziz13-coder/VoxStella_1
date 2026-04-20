const fs = require('fs').promises;
const path = require('path');

const BLOCKED_DIRS = new Set([
  '__pycache__',
  '.git',
  'node_modules',
  'venv',
  '.venv',
  'build',
  'dist',
  'research',
]);

const BLOCKED_FILE_SUFFIXES = [
  '.pyc',
  '.pyo',
  '.log',
  '.log.1',
  '.tmp',
  '.db',
  '.sqlite',
  '.exe',
];

function shouldSkipFile(name) {
  if (name === '.env' || name === 'horary_api.log') return true;
  return BLOCKED_FILE_SUFFIXES.some((suffix) => name.toLowerCase().endsWith(suffix));
}

function makeCopyError(action, srcPath, destPath, error) {
  const detail = error?.message || error;
  return new Error(`${action} failed for ${srcPath} -> ${destPath}: ${detail}`, { cause: error });
}

function createCopyStats() {
  return {
    directoriesCreated: 0,
    filesCopied: 0,
    filesSkipped: 0,
    filesVerified: 0,
  };
}

async function pathExists(targetPath) {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

async function collectCopyManifest(rootDir, currentDir = rootDir, manifest = []) {
  let entries;
  try {
    entries = await fs.readdir(currentDir, { withFileTypes: true });
  } catch (error) {
    throw new Error(`Failed to read packaging manifest from ${currentDir}: ${error?.message || error}`, { cause: error });
  }

  for (const entry of entries) {
    const entryPath = path.join(currentDir, entry.name);
    if (entry.isDirectory()) {
      if (BLOCKED_DIRS.has(entry.name)) {
        continue;
      }
      await collectCopyManifest(rootDir, entryPath, manifest);
      continue;
    }

    if (shouldSkipFile(entry.name)) {
      continue;
    }

    manifest.push(path.relative(rootDir, entryPath));
  }

  return manifest;
}

async function collectFullManifest(rootDir, currentDir = rootDir, manifest = []) {
  let entries;
  try {
    entries = await fs.readdir(currentDir, { withFileTypes: true });
  } catch (error) {
    throw new Error(`Failed to read runtime manifest from ${currentDir}: ${error?.message || error}`, { cause: error });
  }

  for (const entry of entries) {
    const entryPath = path.join(currentDir, entry.name);
    if (entry.isDirectory()) {
      await collectFullManifest(rootDir, entryPath, manifest);
      continue;
    }
    manifest.push(path.relative(rootDir, entryPath));
  }

  return manifest;
}

async function copyDirectory(src, dest, stats) {
  try {
    await fs.mkdir(dest, { recursive: true });
    stats.directoriesCreated += 1;
  } catch (error) {
    throw makeCopyError('mkdir', src, dest, error);
  }

  let entries;
  try {
    entries = await fs.readdir(src, { withFileTypes: true });
  } catch (error) {
    throw makeCopyError('readdir', src, dest, error);
  }

  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (entry.isDirectory()) {
      if (BLOCKED_DIRS.has(entry.name)) {
        continue;
      }
      await copyDirectory(srcPath, destPath, stats);
      continue;
    }

    if (shouldSkipFile(entry.name)) {
      stats.filesSkipped += 1;
      continue;
    }

    try {
      await fs.copyFile(srcPath, destPath);
      stats.filesCopied += 1;
    } catch (error) {
      throw makeCopyError('copyFile', srcPath, destPath, error);
    }
  }
}

async function verifyCopiedManifest(srcRoot, destRoot, manifest, stats, label) {
  const missingPaths = [];
  const mismatchedSizes = [];

  for (const relativePath of manifest) {
    const srcPath = path.join(srcRoot, relativePath);
    const destPath = path.join(destRoot, relativePath);

    let srcStat;
    let destStat;
    try {
      srcStat = await fs.stat(srcPath);
    } catch (error) {
      throw new Error(`Failed to stat source ${label} file ${srcPath}: ${error?.message || error}`, { cause: error });
    }

    try {
      destStat = await fs.stat(destPath);
    } catch (error) {
      if (error?.code === 'ENOENT') {
        missingPaths.push(relativePath);
        continue;
      }
      throw new Error(`Failed to stat copied ${label} file ${destPath}: ${error?.message || error}`, { cause: error });
    }

    if (srcStat.size !== destStat.size) {
      mismatchedSizes.push({
        relativePath,
        sourceSize: srcStat.size,
        destSize: destStat.size,
      });
    }
  }

  if (missingPaths.length || mismatchedSizes.length) {
    const lines = [`${label} verification failed after copy.`];

    if (missingPaths.length) {
      lines.push(`Missing files (${missingPaths.length}):`);
      missingPaths.slice(0, 20).forEach((item) => lines.push(`  - ${item}`));
      if (missingPaths.length > 20) {
        lines.push(`  ... and ${missingPaths.length - 20} more`);
      }
    }

    if (mismatchedSizes.length) {
      lines.push(`Size mismatches (${mismatchedSizes.length}):`);
      mismatchedSizes.slice(0, 20).forEach((item) => {
        lines.push(`  - ${item.relativePath} (source=${item.sourceSize}, dest=${item.destSize})`);
      });
      if (mismatchedSizes.length > 20) {
        lines.push(`  ... and ${mismatchedSizes.length - 20} more`);
      }
    }

    throw new Error(lines.join('\n'));
  }

  stats.filesVerified += manifest.length;
  console.log(`Verified ${manifest.length} ${label} files in ${destRoot}`);
}

async function copyRuntimeBundle(src, dest, stats) {
  try {
    await fs.cp(src, dest, { recursive: true, force: true });
  } catch (error) {
    throw makeCopyError('cp', src, dest, error);
  }

  const runtimeManifest = await collectFullManifest(src);
  stats.filesCopied += runtimeManifest.length;
  return runtimeManifest;
}

async function prepareBackend() {
  console.log('Preparing backend for packaging...');

  const backendSrc = path.join(__dirname, '..', '..', 'backend');
  const backendDest = path.join(__dirname, '..', 'backend');
  const traitCorpusSrc = path.join(__dirname, '..', '..', 'extracted_text_docs', 'new_sources_inspection');
  const traitCorpusDest = path.join(backendDest, 'traits', 'corpus', 'new_sources_inspection');
  const stats = createCopyStats();

  try {
    try {
      await fs.access(backendSrc);
      console.log(`Source backend found at: ${backendSrc}`);
    } catch (error) {
      console.error(`Source backend not found at: ${backendSrc}`);
      throw new Error(`Backend source directory not found: ${backendSrc}`);
    }

    const backendManifest = await collectCopyManifest(backendSrc);
    if (!backendManifest.length) {
      throw new Error(`Backend source manifest is empty: ${backendSrc}`);
    }
    console.log(`Backend source manifest contains ${backendManifest.length} files`);

    try {
      await fs.rm(backendDest, { recursive: true, force: true });
      console.log('Cleaned existing backend directory');
    } catch {
      console.log('No existing backend directory to clean');
    }

    await copyDirectory(backendSrc, backendDest, stats);
    await verifyCopiedManifest(backendSrc, backendDest, backendManifest, stats, 'backend source');

    if (await pathExists(traitCorpusSrc)) {
      const traitCorpusManifest = await collectCopyManifest(traitCorpusSrc);
      await copyDirectory(traitCorpusSrc, traitCorpusDest, stats);
      await verifyCopiedManifest(traitCorpusSrc, traitCorpusDest, traitCorpusManifest, stats, 'trait corpus');
      console.log(`Trait corpus copied: ${traitCorpusSrc} -> ${traitCorpusDest}`);
    } else {
      console.warn(`Trait corpus source not found, skipping optional copy: ${traitCorpusSrc}`);
    }

    const executableName = process.platform === 'win32' ? 'horary_backend.exe' : 'horary_backend';
    const runtimeBundleSrc = path.join(backendSrc, 'dist', 'horary_backend');
    const runtimeBundleDest = path.join(backendDest, 'runtime', 'horary_backend');
    const executableSrc = path.join(runtimeBundleSrc, executableName);
    const executableDest = path.join(runtimeBundleDest, executableName);

    try {
      await fs.access(executableSrc);
      const runtimeManifest = await copyRuntimeBundle(runtimeBundleSrc, runtimeBundleDest, stats);
      await verifyCopiedManifest(runtimeBundleSrc, runtimeBundleDest, runtimeManifest, stats, 'backend runtime bundle');
      const executableStat = await fs.stat(executableDest);
      if (!executableStat.size) {
        throw new Error(`Copied backend executable is empty: ${executableDest}`);
      }
      console.log(`Backend runtime bundle copied: ${runtimeBundleSrc} -> ${runtimeBundleDest}`);
    } catch (error) {
      const isLocked = error?.code === 'EBUSY' || error?.code === 'EPERM';
      throw new Error(
        `${isLocked
          ? `Backend executable destination is locked at ${executableDest}. Close any running Vox Stella or horary_backend process.`
          : `Backend executable not found at ${executableSrc}.`} ` +
        'Run "npm run build-backend-exe" before packaging.'
      );
    }

    const files = await fs.readdir(backendDest);
    console.log(`Backend files copied (${files.length} top-level entries):`);
    files.slice(0, 10).forEach((file) => {
      console.log(`  - ${file}`);
    });
    if (files.length > 10) {
      console.log(`  ... and ${files.length - 10} more`);
    }

    console.log(
      `Copy stats: ${stats.filesCopied} files copied, ${stats.filesSkipped} files skipped, ` +
      `${stats.filesVerified} files verified`
    );
    console.log('Backend prepared successfully!');
    console.log(`Copied from: ${backendSrc}`);
    console.log(`Copied to: ${backendDest}`);
  } catch (error) {
    console.error('Error preparing backend:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  prepareBackend();
}

module.exports = {
  prepareBackend,
  collectCopyManifest,
  collectFullManifest,
  copyDirectory,
  copyRuntimeBundle,
  verifyCopiedManifest,
};
