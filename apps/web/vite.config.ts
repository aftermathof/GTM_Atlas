import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Public learning pages live beside the other knowledge sources, not in the UI code.
export default defineConfig({
  plugins: [vue()],
  publicDir: fileURLToPath(new URL('../../knowledge/site', import.meta.url)),
  server: {
    fs: { allow: [fileURLToPath(new URL('.', import.meta.url)), fileURLToPath(new URL('../../knowledge', import.meta.url))] },
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  preview: { port: 4173 },
})
