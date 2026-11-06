import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// base './' lets the same build run behind the agent (docker) and on GitHub Pages.
export default defineConfig({
  base: './',
  plugins: [react(), tailwindcss()],
});
