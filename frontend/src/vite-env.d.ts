/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the Arcus backend. Falls back to the Render deployment. */
  readonly VITE_API_URL?: string;
  /** Base path the app is served from (e.g. /Arcus/ on GitHub Pages). */
  readonly VITE_BASE_PATH?: string;
  /** Exposes the Arcus Research route and navigation item when set to "true". */
  readonly VITE_ENABLE_RESEARCH?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
