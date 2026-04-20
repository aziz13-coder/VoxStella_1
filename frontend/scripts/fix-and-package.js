const fs = require('fs').promises;
const path = require('path');
const { exec } = require('child_process');
const { promisify } = require('util');

const execAsync = promisify(exec);

async function fixAndPackage() {
  console.log('Fixing working build and creating APPX...');

  const backendRuntimeSrc = path.join(__dirname, '..', '..', 'backend', 'dist', 'horary_backend');
  const workingDir = path.join(__dirname, '..', 'dist-electron', 'win-unpacked');
  const workingBackendRuntimeDir = path.join(workingDir, 'resources', 'backend', 'runtime', 'horary_backend');
  const backendExeDest = path.join(
    workingBackendRuntimeDir,
    process.platform === 'win32' ? 'horary_backend.exe' : 'horary_backend',
  );

  try {
    try {
      await fs.access(workingDir);
      console.log(`Working directory found: ${workingDir}`);
    } catch {
      console.error('Working directory not found. Please run "npm run electron:pack" first.');
      return;
    }

    try {
      await fs.access(backendRuntimeSrc);
      console.log(`Backend runtime bundle found: ${backendRuntimeSrc}`);
    } catch {
      console.error('Backend runtime bundle not found. Please run "npm run build-backend-exe" first.');
      return;
    }

    console.log('Copying backend runtime bundle into working directory...');
    await fs.rm(workingBackendRuntimeDir, { recursive: true, force: true });
    await fs.mkdir(path.dirname(workingBackendRuntimeDir), { recursive: true });
    await fs.cp(backendRuntimeSrc, workingBackendRuntimeDir, { recursive: true, force: true });

    const stats = await fs.stat(backendExeDest);
    console.log(`Backend runtime copied; launcher verified (${Math.round(stats.size / 1024 / 1024)}MB exe)`);

    console.log('Creating APPX from working directory...');
    const { stdout } = await execAsync('npx electron-builder --win appx --prepackaged dist-electron/win-unpacked', {
      cwd: path.join(__dirname, '..'),
    });

    console.log('APPX created successfully.');
    if (stdout) console.log('Build output:', stdout);

    const appxDir = path.join(__dirname, '..', 'dist-electron');
    const files = await fs.readdir(appxDir);
    const appxFiles = files.filter((file) => file.endsWith('.appx'));

    console.log('Packaging complete.');
    console.log(`APPX files created: ${appxFiles.length}`);
    appxFiles.forEach((file) => {
      console.log(`  - ${file}`);
    });
  } catch (error) {
    console.error('Error during fix and package:', error);
    if (error.stderr) {
      console.error('Build errors:', error.stderr);
    }
  }
}

if (require.main === module) {
  fixAndPackage();
}

module.exports = { fixAndPackage };
