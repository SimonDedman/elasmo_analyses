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
    // Split the ~850 kB bundle into a few logical chunks so Pages can
    // cache them separately and first paint only needs the app shell.
    // maplibre-gl is already auto-split; here we peel off deck.gl (the
    // other big dep) and supercluster so they load in parallel and
    // cache independently across commits that only touch app code.
    rollupOptions: {
      output: {
        manualChunks: {
          deckgl: [
            '@deck.gl/core',
            '@deck.gl/react',
            '@deck.gl/layers',
            '@deck.gl/extensions',
          ],
          supercluster: ['supercluster'],
        },
      },
    },
    chunkSizeWarningLimit: 600,
  },
  server: {
    port: 5173,
    open: true,
  },
}));
