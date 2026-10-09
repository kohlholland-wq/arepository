// Render the paper-cutout breakdown to MP4 (or stills) with headless Chromium.
//
//   NODE_PATH=$(npm root -g) node render.cjs SONG.m4a OUT.mp4
//   NODE_PATH=$(npm root -g) node render.cjs SONG.m4a OUT_PREFIX --still 181.5 184.2
//
// Timing (section times and detected drum hits) comes from timing.json.
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");
const { chromium } = require("playwright");

const FPS = 24;

(async () => {
  const [audio, out, ...rest] = process.argv.slice(2);
  const timing = JSON.parse(fs.readFileSync(path.join(__dirname, "timing.json"), "utf8"));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  await page.goto("file://" + path.resolve(__dirname, "scene.html"));
  await page.evaluate(t => window.setTiming(t), timing);
  await page.evaluate(() => document.fonts.load("20px Caveat").then(() => document.fonts.ready));
  const shot = async t => {
    await page.evaluate(t => window.renderAt(t), t);
    return page.locator("#stage").screenshot({ type: "png" });
  };

  if (rest[0] === "--still") {
    for (const t of rest.slice(1)) fs.writeFileSync(`${out}_${t}.png`, await shot(Number(t)));
    await browser.close();
    return;
  }

  const { T0, T_END, CUT } = timing;
  const dur = T_END - T0;
  const ff = spawn("ffmpeg", [
    "-v", "error", "-y",
    "-f", "image2pipe", "-framerate", String(FPS), "-i", "-",
    "-ss", String(T0), "-t", String(dur), "-i", audio,
    "-map", "0:v", "-map", "1:a",
    "-af", `afade=t=in:st=0:d=0.3,afade=t=out:st=${(CUT - T0).toFixed(3)}:d=1.4`,
    "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", out,
  ], { stdio: ["pipe", "inherit", "inherit"] });
  const n = Math.round(dur * FPS);
  for (let i = 0; i < n; i++) {
    const png = await shot(T0 + i / FPS);
    if (!ff.stdin.write(png)) await new Promise(r => ff.stdin.once("drain", r));
    if (i % 48 === 0) process.stderr.write(`frame ${i}/${n}\n`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on("close", r));
  await browser.close();
})();
