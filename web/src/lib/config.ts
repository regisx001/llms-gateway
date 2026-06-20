import { PUBLIC_API_URL } from '$env/static/public';

/**
 * Application configuration.
 *
 * - In development, PUBLIC_API_URL is set in .env (e.g. http://localhost:8000)
 *   so the SvelteKit dev server proxies requests to the FastAPI backend.
 * - In Docker / production, PUBLIC_API_URL is empty (or unset at build time),
 *   so the app uses relative paths (same origin) since the FastAPI backend
 *   also serves the static files.
 */
export const config = {
    apiBase: PUBLIC_API_URL || ''
};
