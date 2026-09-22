import { test, expect } from "@playwright/test";

test.describe("Dashboard shell", () => {
  test("loads the home page with the main navigation", async ({ page }) => {
    await page.goto("/");

    await expect(page).toHaveTitle(/EnerVision Dashboard/);
    await expect(page.getByRole("link", { name: "Dashboard" })).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Prédictions & Recommandations" }),
    ).toBeVisible();
  });

  test("navigates to the prediction page", async ({ page }) => {
    await page.goto("/");

    await page
      .getByRole("link", { name: "Prédictions & Recommandations" })
      .click();

    await expect(page).toHaveURL(/\/prediction$/);
  });
});
