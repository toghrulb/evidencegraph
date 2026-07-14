import { expect, test } from "@playwright/test";

test("renders the Phase 0 landing page", async ({ page }) => {
  const response = await page.goto("/");

  expect(response?.ok()).toBe(true);
  await expect(page).toHaveTitle("EvidenceGraph");
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Research answers should be easy to verify.",
    }),
  ).toBeVisible();
  await expect(
    page.getByText("Foundation ready", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Skip to content" }),
  ).toHaveAttribute("href", "#main-content");
});
