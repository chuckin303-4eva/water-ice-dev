/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_TILE_URL_TEMPLATE: string
  readonly VITE_TILE_ATTRIBUTION: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
