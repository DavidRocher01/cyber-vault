import path from 'path';
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false, // sequential: tests create real users in shared DB
  forbidOnly: !!process.env['CI'],
  retries: process.env['CI'] ? 2 : 2,
  workers: process.env['CI'] ? 1 : 1, // 1 worker to avoid overwhelming the local backend
  reporter: [['html'], ['line']],
  use: {
    baseURL: 'http://localhost:4200',
    trace: 'on-first-retry',
    // Give Angular lazy-loaded routes time to hydrate
    navigationTimeout: 15_000,
    actionTimeout: 10_000,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: [
    {
      // Angular dev server
      command: 'npm start',
      url: 'http://localhost:4200',
      reuseExistingServer: !process.env['CI'],
      timeout: 120_000,
    },
    {
      // FastAPI backend — use venv python directly with cwd set to backend/
      command: '.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8000',
      cwd: path.join(__dirname, '..', 'backend'),
      url: 'http://localhost:8000/health',
      reuseExistingServer: !process.env['CI'],
      timeout: 30_000,
    },
  ],
});
