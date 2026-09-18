import { test, expect } from "@playwright/test";

test.describe("Login", () => {
  test("shows the login button when logged out, and the profile button after logging in", async ({
    page,
  }) => {
    await page.goto("/");

    await expect(page.getByRole("button", { name: "Se connecter" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Menu utilisateur" })).toHaveCount(0);

    await page.getByRole("button", { name: "Se connecter" }).click();
    await page.getByLabel("Email").fill("alice@example.com");
    await page.getByLabel("Mot de passe").fill("testpass123");
    await page.getByRole("button", { name: "Se connecter" }).last().click();

    await expect(page.getByRole("button", { name: "Menu utilisateur" })).toBeVisible();
    await expect(page.getByText("alice@example.com")).toBeVisible();
    await expect(page.getByRole("button", { name: "Se connecter" })).toHaveCount(0);

    await page.getByRole("button", { name: "Se déconnecter" }).click();

    await expect(page.getByRole("button", { name: "Se connecter" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Menu utilisateur" })).toHaveCount(0);
  });

  test("logs out via the profile menu dropdown", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("button", { name: "Se connecter" }).click();
    await page.getByLabel("Email").fill("alice@example.com");
    await page.getByLabel("Mot de passe").fill("testpass123");
    await page.getByRole("button", { name: "Se connecter" }).last().click();

    await page.getByRole("button", { name: "Menu utilisateur" }).click();
    await page.getByRole("menuitem", { name: "Se déconnecter" }).click();

    await expect(page.getByRole("button", { name: "Se connecter" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Menu utilisateur" })).toHaveCount(0);
  });

  test("shows an error on invalid credentials and keeps the login button", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("button", { name: "Se connecter" }).click();
    await page.getByLabel("Email").fill("alice@example.com");
    await page.getByLabel("Mot de passe").fill("wrong-password");
    await page.getByRole("button", { name: "Se connecter" }).last().click();

    await expect(page.getByText("Identifiants invalides")).toBeVisible();
    await page.getByRole("button", { name: "Annuler" }).click();
    await expect(page.getByRole("button", { name: "Se connecter" })).toBeVisible();
  });
});
