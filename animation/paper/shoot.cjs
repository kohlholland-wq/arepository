// Render scene.html to PNG stills with headless Chromium.
// Usage: NODE_PATH=$(npm root -g) node shoot.cjs OUT.png ['{"pose":"down",...}'] [scale]
const path = require("path");
const { chromium } = require("playwright");

(async () => {
  const [out, state = "{}", scale = "1"] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: Number(scale) });
  const url = "file://" + path.resolve(__dirname, "scene.html") + "?state=" + encodeURIComponent(state);
  await page.goto(url);
  await page.evaluate(() => document.fonts.ready);
  await page.locator("#stage").screenshot({ path: out });
  await browser.close();
})();
