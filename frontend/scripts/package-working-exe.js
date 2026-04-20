const fs = require('fs').promises;
const path = require('path');

async function packageWorkingExe() {
  console.log('Packaging working build with backend runtime bundle...');

  const workingDir = path.join(__dirname, '..', 'dist-electron', 'win-unpacked');
  const backendRuntimeSrc = path.join(__dirname, '..', '..', 'backend', 'dist', 'horary_backend');
  const backendRuntimeDest = path.join(workingDir, 'resources', 'backend', 'runtime', 'horary_backend');
  const backendExeDest = path.join(
    backendRuntimeDest,
    process.platform === 'win32' ? 'horary_backend.exe' : 'horary_backend',
  );

  try {
    try {
      await fs.access(workingDir);
      console.log(`Working directory found: ${workingDir}`);
    } catch {
      console.error(`Working directory not found: ${workingDir}`);
      console.log('Please run "npm run electron:pack" first to create the base package.');
      throw new Error('Working directory not found');
    }

    try {
      await fs.access(backendRuntimeSrc);
      console.log(`Backend runtime bundle found: ${backendRuntimeSrc}`);
    } catch {
      console.error(`Backend runtime bundle not found: ${backendRuntimeSrc}`);
      console.log('Please run "npm run build-backend-exe" first.');
      throw new Error('Backend runtime bundle not found');
    }

    await fs.rm(backendRuntimeDest, { recursive: true, force: true });
    await fs.mkdir(path.dirname(backendRuntimeDest), { recursive: true });
    await fs.cp(backendRuntimeSrc, backendRuntimeDest, { recursive: true, force: true });
    console.log(`Backend runtime bundle copied to: ${backendRuntimeDest}`);

    const stats = await fs.stat(backendExeDest);
    console.log(`Backend launcher verified (${Math.round(stats.size / 1024 / 1024)}MB)`);

    console.log('Creating APPX from working build...');
    const { spawn } = require('child_process');

    return new Promise((resolve, reject) => {
      const builderProcess = spawn(
        'npx',
        ['electron-builder', '--win', '--dir', workingDir, '--config.directories.output=dist-electron-working'],
        {
          stdio: 'inherit',
          shell: true,
          cwd: path.join(__dirname, '..'),
        },
      );

      builderProcess.on('close', (code) => {
        if (code === 0) {
          console.log('APPX package created successfully with backend runtime bundle.');
          resolve();
        } else {
          console.error(`APPX packaging failed with code ${code}`);
          reject(new Error(`Packaging failed with code ${code}`));
        }
      });

      builderProcess.on('error', (error) => {
        console.error('Error running electron-builder:', error);
        reject(error);
      });
    });
  } catch (error) {
    console.error('Error packaging working build:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  packageWorkingExe();
}

module.exports = { packageWorkingExe };
