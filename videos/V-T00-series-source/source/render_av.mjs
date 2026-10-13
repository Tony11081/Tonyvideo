// Final renderer with adaptive motion blur.
//   node render_av.mjs <w> <h> <out.mp4>        (T0/T1 env vars: render part of the film)
// Each output frame averages K subframes spread over a 180° shutter, where K
// grows with on-screen motion (4 when calm, up to 16 in fast pans).
import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
// sharp: from this folder's node_modules if installed (npm i sharp), else from a sibling project.
let sharp;
try { sharp = createRequire(import.meta.url)("sharp"); } catch { sharp = createRequire("/home/claude/openaigrowth/package.json")("sharp"); }
const [w, h, out] = process.argv.slice(2);
const W = +w, H = +h;
const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium", args: ["--font-render-hinting=none", "--disable-gpu", "--force-color-profile=srgb"] });
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
await page.goto(`file://${process.cwd()}/${process.env.FILM || "film.html"}${(process.env.FILM || "").includes("?") ? "&" : "?"}w=${W}&h=${H}`);
const info = await page.evaluate(() => window.ready);
const cdp = await page.context().newCDPSession(page);
const fps = info.fps;
const F0 = Math.round((+process.env.T0 || 0) * fps), F1 = Math.round((+process.env.T1 || info.duration) * fps);
const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", `${W}x${H}`, "-r", String(fps), "-i", "-",
  "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart", out], { stdio: ["pipe", "inherit", "inherit"] });
const px = W * H * 3;
const acc = new Float32Array(px);
const frame = Buffer.alloc(px);
const t0 = Date.now(); let shots = 0;
for (let f = F0; f < F1; f++) {
  const t = f / fps;
  const d = await page.evaluate((t) => window.motion(t), t);
  const K = Math.min(16, Math.max(+(process.env.KMIN || 4), Math.ceil(d / 5)));
  acc.fill(0);
  for (let s = 0; s < K; s++) {
    await page.evaluate((t) => window.seek(t), t + (s / K) * 0.5 / fps);
    const r = await cdp.send("Page.captureScreenshot", { format: "png", optimizeForSpeed: true });
    const raw = await sharp(Buffer.from(r.data, "base64")).removeAlpha().raw().toBuffer();
    for (let i = 0; i < px; i++) acc[i] += raw[i];
    shots++;
  }
  for (let i = 0; i < px; i++) frame[i] = Math.round(acc[i] / K);
  if (!ff.stdin.write(frame)) await new Promise((r) => ff.stdin.once("drain", r));
  if ((f - F0) % 120 === 0) console.log(`frame ${f}/${F1}  shots ${shots}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
}
ff.stdin.end();
await new Promise((r) => ff.on("exit", r));
if (errors.length) console.log("PAGE ERRORS:\n" + errors.join("\n"));
console.log(`done: ${F1 - F0} frames, ${shots} shots, ${((Date.now() - t0) / 1000).toFixed(0)}s`);
await browser.close();
