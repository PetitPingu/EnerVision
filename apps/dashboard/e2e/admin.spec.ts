import { test, expect } from "@playwright/test";

async function loginAs(page: import("@playwright/test").Page, email: string, password: string) {
  await page.goto("/");
  await page.getByRole("button", { name: "Se connecter" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Mot de passe").fill(password);
  await page.getByRole("button", { name: "Se connecter" }).last().click();
  await expect(page.getByRole("button", { name: "Menu utilisateur" })).toBeVisible();
}

test.describe("Admin", () => {
  test("a non-admin does not see the Administration nav item", async ({ page }) => {
    await loginAs(page, "bob@example.com", "bobpass456");

    await expect(page.getByRole("link", { name: "Administration" })).toHaveCount(0);
  });

  test("an admin can create a user with site access, and it appears in the list", async ({
    page,
  }) => {
    await loginAs(page, "admin@enervision.com", "changeme1234");

    await page.getByRole("link", { name: "Administration" }).click();
    await expect(page.getByRole("heading", { name: "Utilisateurs" })).toBeVisible();

    await page.getByRole("button", { name: "Ajouter un utilisateur" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.locator("#user-email").fill("e2e-viewer@example.com");
    await dialog.locator("#user-password").fill("e2eviewerpass1");
    await dialog.getByText("Bureau Paris La Défense").click();
    await dialog.getByRole("button", { name: "Enregistrer" }).click();

    const row = page.getByRole("row", { name: /e2e-viewer@example.com/ });
    await expect(row).toBeVisible();
    await expect(row.getByText("Bureau Paris La Défense")).toBeVisible();

    // Nettoyage : ce compte ne doit pas survivre au test.
    page.once("dialog", (confirmDialog) => confirmDialog.accept());
    await row.getByRole("button", { name: "Supprimer" }).click();
    await expect(row).toHaveCount(0);
  });
});
