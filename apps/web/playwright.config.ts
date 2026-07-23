import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  use: { baseURL: 'http://127.0.0.1:4173' },
  webServer: [
    {
      command:
        'UV_CACHE_DIR=../api/.uv-cache uv --directory ../api run uvicorn service_advisor_api.main:app --host 127.0.0.1 --port 8000',
      port: 8000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'pnpm dev --host 127.0.0.1 --port 4173',
      port: 4173,
      reuseExistingServer: !process.env.CI,
    },
  ],
})
