import { chromium } from "@playwright/test";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
process.env.PLAYWRIGHT_BROWSERS_PATH ??= resolve(here, "../../.playwright-browsers");
const outDir = resolve(here, "../../.tmp");
const prodeJson = resolve(here, "../../prode/prode_facu.json");

const browser = await chromium.launch();

async function flowToKnockout(page) {
  await page.goto("http://localhost:3000/prode?new=1");
  await page.locator('input[type="file"]').setInputFiles(prodeJson);
  await page.getByRole("button", { name: "Confirmar y revelar" }).click();
  await page.waitForURL(/\/mundial\?p=/);
  await page.getByRole("button", { name: "Saltear fase" }).click(); // -> 16avos
}

// Desktop
const desktop = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await flowToKnockout(desktop);
await desktop.waitForTimeout(1800);
await desktop.screenshot({ path: `${outDir}/bracket-r32-desktop.png` });
await desktop.getByRole("button", { name: "Siguiente" }).click(); // -> 8vos
await desktop.waitForTimeout(1600);
await desktop.screenshot({ path: `${outDir}/bracket-r16-desktop.png` });
await desktop.getByRole("button", { name: "Saltear todo" }).click();
await desktop.waitForTimeout(1800);
await desktop.screenshot({ path: `${outDir}/bracket-final-desktop.png` });
await desktop.close();

// Mobile 390
const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
await flowToKnockout(mobile);
await mobile.waitForTimeout(1600);
await mobile.screenshot({ path: `${outDir}/bracket-r32-mobile.png`, fullPage: true });
await mobile.getByRole("button", { name: "Saltear todo" }).click();
await mobile.waitForTimeout(1800);
await mobile.screenshot({ path: `${outDir}/bracket-final-mobile.png`, fullPage: true });
await mobile.close();

await browser.close();
console.log("OK screenshots en", outDir);
