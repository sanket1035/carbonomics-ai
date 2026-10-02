import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// base './' so the built site works on any host or sub-path (Vercel, Netlify, GitHub Pages).
export default defineConfig({
  base: './',
  plugins: [react(), tailwindcss()],
})
