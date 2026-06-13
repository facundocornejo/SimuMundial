import { expect, test, type Page } from "@playwright/test";
import { resolve } from "node:path";

const facuProdePath = resolve(__dirname, "../../prode/prode_facu.json");

async function importFacuAndConfirm(page: Page) {
  await page.goto("/prode?new=1");
  await page.locator('input[type="file"]').setInputFiles(facuProdePath);
  await expect(page.locator(".import-message")).toContainText("Importado: 72/72 partidos.");
  await expect(page.getByPlaceholder("facu")).toHaveValue("facu");
  const confirmButton = page.getByRole("button", { name: "Confirmar y revelar" });
  await expect(confirmButton).toBeEnabled();
  await confirmButton.click();
  await page.waitForURL(/\/mundial\?p=/);
  return new URL(page.url()).searchParams.get("p") ?? "";
}

async function skipToChampion(page: Page) {
  await page.getByRole("button", { name: "Saltear todo" }).click();
  const champion = page.locator(".champion-mark strong");
  await expect(champion).toBeVisible();
  return (await champion.textContent())?.trim() ?? "";
}

test("la landing carga y lleva a /prode", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Armá tu Mundial");
  await page.locator('a.button--primary[href="/prode"]').click();
  await page.waitForURL(/\/prode/);
  await expect(page.getByRole("button", { name: "Confirmar y revelar" })).toBeVisible();
});

test("flujo completo: importar facu, 72/72, confirmar y revelar campeón", async ({ page }, testInfo) => {
  const code = await importFacuAndConfirm(page);
  expect(code.length).toBeGreaterThan(0);

  const champion = await skipToChampion(page);
  expect(champion.length).toBeGreaterThan(0);

  await expect(page.getByRole("button", { name: "Reproducir desde el grupo A" })).toBeVisible();
  await testInfo.attach(`final-${testInfo.project.name}`, {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });
});

test("el mismo ?p= da siempre el mismo campeón", async ({ page }) => {
  const code = await importFacuAndConfirm(page);
  const firstChampion = await skipToChampion(page);

  await page.goto(`/mundial?p=${code}`);
  const secondChampion = await skipToChampion(page);

  expect(secondChampion).toBe(firstChampion);
});

test("autosave: el draft sobrevive una recarga", async ({ page }) => {
  await page.goto("/prode?new=1");
  await page.getByPlaceholder("facu").fill("TestAutosave");
  await page.locator(".quick-grid button", { hasText: "2-1" }).click();

  await page.goto("/prode");
  await expect(page.getByPlaceholder("facu")).toHaveValue("TestAutosave");
  await expect(page.locator(".source-summary")).toContainText("1/72");
});

test("un código inválido en /mundial redirige a /prode", async ({ page }) => {
  await page.goto("/mundial?p=codigo-invalido-123");
  await page.waitForURL(/\/prode/);
});

test("/mundial sin código redirige a /prode", async ({ page }) => {
  await page.goto("/mundial");
  await page.waitForURL(/\/prode/);
});

test("/api/og responde un PNG, con y sin código", async ({ page, request }) => {
  const generic = await request.get("/api/og");
  expect(generic.status()).toBe(200);
  expect(generic.headers()["content-type"]).toContain("image/png");

  const code = await importFacuAndConfirm(page);
  const withCode = await request.get(`/api/og?p=${code}`);
  expect(withCode.status()).toBe(200);
  expect(withCode.headers()["content-type"]).toContain("image/png");
});
