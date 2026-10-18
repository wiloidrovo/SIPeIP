import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// Compila React y habilita su recarga en desarrollo; las peticiones a Django
// se configuran en src/services/api.ts, no mediante un proxy en este archivo.
export default defineConfig({
  plugins: [react()],
})
