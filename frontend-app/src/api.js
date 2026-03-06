import axios from 'axios';

// Get stored URL or default to the current host at port 8000
const getBaseUrl = () => {
    const stored = localStorage.getItem('api_url');
    if (stored) return stored;

    // In production (unified hosting), the API is on the same host and port
    if (import.meta.env.PROD) {
        return window.location.origin;
    }

    // Auto-detect host for local dev/testing
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') return 'http://127.0.0.1:8000';
    return `http://${host}:8000`;
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
    // Remove trailing slash
    const cleanUrl = url.replace(/\/$/, "");
    localStorage.setItem('api_url', cleanUrl);
    window.location.reload(); // Reload to apply changes
};
