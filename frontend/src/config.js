// In production set VITE_API_BASE to the hosted backend URL (e.g. https://your-api.onrender.com).
// Without it, the app talks to a backend on port 8000 of the same machine (local dev).
const configured = import.meta.env.VITE_API_BASE?.trim().replace(/\/+$/, '');

export const API_BASE = configured || `http://${window.location.hostname}:8000`;
