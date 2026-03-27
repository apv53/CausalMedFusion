import axios from 'axios';

// Detects the environment variable, or falls back to localhost for your local dev
const api = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000',
    headers: {
        'Content-Type': 'application/json',
        // CRITICAL: This skips the ngrok "Browser Warning" screen automatically
        'ngrok-skip-browser-warning': 'true',
    },
});

export default api;