import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Vite is the tool that runs the site while you work on it, and packages it up
// when you're done. `npm run dev` starts it on http://localhost:5173.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
})
