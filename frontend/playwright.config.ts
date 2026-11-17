import { defineConfig, devices } from '@playwright/test'

const port = Number(process.env.E2E_PORT ?? 8100)

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  timeout: 30_000,
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: 'off',
    locale: 'en-US',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'bash e2e/serve.sh',
    url: `http://127.0.0.1:${port}/readyz`,
    reuseExistingServer: false,
    timeout: 60_000,
  },
})
