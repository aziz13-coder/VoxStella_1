import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Ensure assets are referenced with relative paths for Electron file:// loading
export default defineConfig({
  plugins: [react()],
  base: './',
});

