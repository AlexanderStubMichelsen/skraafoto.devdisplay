import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Local dev: forward API calls to Flask (`npm run dev` starts it on port 5000)
    proxy: {
      '/api': 'http://127.0.0.1:5000',
    },
  },
})
