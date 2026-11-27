// Render compose.html frame by frame with Chromium, then encode a 9:16 MP4.
//   node render.js <dir> [seconds=17.6] [fps=30] [audio.wav]
const { chromium } = require("playwright");
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

(async () => {
  const dir = path.resolve(process.argv[2] || ".");
  const secs = parseFloat(process.argv[3] || "17.6");
  const fps = parseInt(process.argv[4] || "30", 10);
  const audio = process.argv[5] ? path.resolve(process.argv[5]) : null;
  const frames = path.join(dir, "frames");
  fs.rmSync(frames, { recursive: true, force: true });
  fs.mkdirSync(frames);

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto("file://" + path.join(dir, "compose.html"));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => document.getElementById("prod").complete);

  const n = Math.round(secs * fps);
  for (let i = 0; i < n; i++) {
    await page.evaluate((t) => window.render(t), i / fps);
    await page.screenshot({ path: path.join(frames, String(i).padStart(5, "0") + ".jpg"), type: "jpeg", quality: 95 });
  }
  await browser.close();

  const out = path.join(dir, "reel.mp4");
  execFileSync("ffmpeg", ["-loglevel", "error", "-y",
    "-framerate", String(fps), "-i", path.join(frames, "%05d.jpg"),
    ...(audio ? ["-i", audio, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000"]
              : ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]),
    "-shortest", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
    "-profile:v", "high", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "128k", out]);
  console.log("wrote", out, n, "frames");
})();
