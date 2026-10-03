import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The API returns relative image URLs like /media/products/<slug>.jpg, so the
// dev server proxies both /api and /media to FastAPI. That keeps the frontend
// free of hardcoded hostnames and lets the stored image paths work as-is.
//
// Port comes from BACKEND_PORT so a blocked 8000 can be worked around without
// editing code.
const backend = `http://127.0.0.1:${process.env.BACKEND_PORT ?? '8000'}`

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: backend, changeOrigin: true },
      '/media': { target: backend, changeOrigin: true },
    },
  },
})
