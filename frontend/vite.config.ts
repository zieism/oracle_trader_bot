import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    cors: true,
  },
  resolve: {
    alias: {
      // Path aliases for feature-based architecture
      '@': '/src',
      '@app': '/src/app',
      '@components': '/src/components',
      '@features': '/src/features',
      '@services': '/src/services',
      '@hooks': '/src/hooks',
      '@utils': '/src/utils',
      '@types': '/src/types',
      
      // Legacy compatibility aliases (will be deprecated)
      '@pages': '/src/features',
      '@api': '/src/services/api',
    },
  },
  define: {
    // Make environment variables available at build time
    'import.meta.env.VITE_API_BASE_URL': JSON.stringify('http://localhost:8000/api/v1'),
    'import.meta.env.VITE_WS_BASE_URL': JSON.stringify('ws://localhost:8000/api/v1'),
  }
})
