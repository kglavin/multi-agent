// Loads web/index.html in headless Chromium and prints what the page reports.
// Needs the native server running on ws://127.0.0.1:9001.
import { chromium } from "playwright-core";
import { serve } from "./serve.mjs";

const executablePath = process.env.CHROMIUM ?? `${process.env.HOME}/.cache/ms-playwright/chromium_headless_shell-1148/chrome-linux/headless_shell`;
const server = await serve(8080);
const browser = await chromium.launch({ executablePath });
try {
  const page = await browser.newPage();
  page.on("console", (m) => console.log("console:", m.text()));
  page.on("pageerror", (e) => console.log("pageerror:", e.message));
  await page.goto("http://127.0.0.1:8080/web/index.html");
  await page.waitForFunction(() => window.__result, null, { timeout: 15000 });
  console.log(JSON.stringify(await page.evaluate(() => window.__result), null, 2));
  console.log("browser:", browser.version());
} finally {
  await browser.close();
  server.close();
}
