import { defineConfig, devices } from "@playwright/test";

const baseURL = "http://127.0.0.1:3000";
const browserChannel = process.env.PLAYWRIGHT_CHANNEL;

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : [["html", { open: "never" }]],
  use: {
    ...devices["Desktop Chrome"],
    baseURL,
    ...(browserChannel ? { channel: browserChannel } : {}),
    trace: "on-first-retry",
  },
  webServer: {
    command: "npm run dev -- --hostname 127.0.0.1",
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
