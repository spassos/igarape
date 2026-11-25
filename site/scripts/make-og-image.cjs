// Render og-image.html to site/public/og.png (1200x630, deviceScaleFactor 1).
// Maintainer tool, not a repository dependency: needs Node.js and Playwright with Chromium
// (`npm install --global playwright && npx playwright install chromium`, then run with
// NODE_PATH="$(npm root -g)"). See site/README.md.
"use strict";
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
    await page.goto(pathToFileURL(path.join(__dirname, "og-image.html")).href);
    await page.waitForLoadState("networkidle");
    const out = path.join(__dirname, "..", "public", "og.png");
    await page.screenshot({ path: out, fullPage: false });
    console.log(`Wrote ${out}`);
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
