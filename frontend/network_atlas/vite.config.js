import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

// Build target: docs/network_atlas/ so GitHub Pages serves from that URL.
// Base path matches the deployed sub-path on the site.
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: mode === 'production' ? '/elasmo_analyses/network_atlas/' : '/',
  build: {
    outDir: resolve(__dirname, '../../docs/network_atlas'),
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    open: true,
  },
}));
