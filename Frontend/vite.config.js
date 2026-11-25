import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Proxy de desarrollo: el navegador habla con Vite y Vite consulta Django.
// No es necesario agregar CORS a Omega-main.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5500,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        secure: false
      }
    }
  }
});
