import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import basicSsl from '@vitejs/plugin-basic-ssl';

export default defineConfig({
    plugins: [react(), tailwindcss(), basicSsl()],
    base: '/speaker-based-attendance/',
    server: {
        host: true, // Listen on all network interfaces
    }
});
