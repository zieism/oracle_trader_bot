import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': '/src',
      '@features': '/src/features',
      '@components': '/src/components',
      '@services': '/src/services',
      '@assets': '/src/assets',
    },
  },
  server: {
    port: 5173,
    host: true,
    cors: true,
  },
  define: {
    // Make environment variables available at build time
    'import.meta.env.VITE_API_BASE_URL': JSON.stringify(process.env.VITE_API_BASE_URL),
    'import.meta.env.VITE_WS_BASE_URL': JSON.stringify(process.env.VITE_WS_BASE_URL),
  }
})
