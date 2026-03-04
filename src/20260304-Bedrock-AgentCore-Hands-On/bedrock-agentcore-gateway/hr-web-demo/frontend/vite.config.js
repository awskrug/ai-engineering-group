import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
    base: process.env.VITE_BASE_PATH || '',
    plugins: [vue()],
    server: {
        port: 5173,
        host: '0.0.0.0'
    }
})