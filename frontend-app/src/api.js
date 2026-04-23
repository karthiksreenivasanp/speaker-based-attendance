import axios from 'axios';

// Get stored URL or default to the Hugging Face Space backend
const getBaseUrl = () => {
    const stored = localStorage.getItem('api_url');
    if (stored) return stored;

    const envUrl = import.meta.env.VITE_API_URL;
    if (envUrl) return envUrl.replace(/\/$/, "");

    const hostname = window.location.hostname;
    const isLocalDev = hostname === 'localhost' || hostname === '127.0.0.1';
    if (isLocalDev) {
        return `http://${hostname}:8000`;
    }

    // Default to the Hugging Face backend deployment in production
    return 'https://karthiksreenivasanp-speaker-attendance-backend.hf.space';
};

export const api = axios.create({
    baseURL: getBaseUrl(),
    timeout: 120000, // Increased to 120s for processing overhead
});

// Interceptor to update URL and add Token
api.interceptors.request.use((config) => {
    config.baseURL = getBaseUrl();
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    // Bypass Ngrok and Pinggy warning screens for API requests
    config.headers['ngrok-skip-browser-warning'] = 'true';
    config.headers['X-Pinggy-No-Screen'] = 'true';
    config.headers['Bypass-Tunnel-Reminder'] = 'true';
    return config;
});

export const saveApiUrl = (url) => {
    if (!url || !url.trim()) return;
    // Remove trailing slash
    const cleanUrl = url.trim().replace(/\/$/, "");
    localStorage.setItem('api_url', cleanUrl);
    window.location.reload(); // Reload to apply changes
};
