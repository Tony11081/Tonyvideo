// Usage:
//   node render.mjs stills  <w> <h> <t1,t2,...> <outdir>       PNG stills at given seconds
//   node render.mjs sheet   <w> <h> <step> <out.png>            contact sheet, one frame every <step> s
//   node render.mjs video   <w> <h> <out.mp4> [subframes]       silent 60fps video (subframes>1 = motion blur)
import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync, rmSync } from "node:fs";
const [mode, w, h, a, b] = process.argv.slice(2);
const W = +w, H = +h;
const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium", args: ["--font-render-hinting=none", "--disable-gpu", "--force-color-profile=srgb"] });
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
await page.goto(`file://${process.cwd()}/${process.env.FILM || "film.html"}?w=${W}&h=${H}`);
const info = await page.evaluate(() => window.ready);
const cdp = await page.context().newCDPSession(page);
async function shot(t, fmt = "png") {
  await page.evaluate((t) => window.seek(t), t);
  const r = await cdp.send("Page.captureScreenshot", { format: fmt, optimizeForSpeed: true, captureBeyondViewport: false });
  return Buffer.from(r.data, "base64");
}
if (mode === "stills") {
  mkdirSync(b, { recursive: true });
  for (const t of a.split(",").map(Number)) writeFileSync(`${b}/t${t.toFixed(2).padStart(6, "0")}.png`, await shot(t));
} else if (mode === "sheet") {
  const step = +a; const ts = []; for (let t = 0; t < info.duration - 1e-6; t += step) ts.push(+t.toFixed(3));
  rmSync("/tmp/claude-0/sheet", { recursive: true, force: true }); mkdirSync("/tmp/claude-0/sheet", { recursive: true });
  const files = [];
  for (const t of ts) { const f = `/tmp/claude-0/sheet/${String(files.length).padStart(3, "0")}.png`; writeFileSync(f, await shot(t)); files.push(f); }
  const cols = W > H ? 6 : 8;
  await new Promise((res, rej) => { const p = spawn("ffmpeg", ["-y", "-loglevel", "error", "-framerate", "1", "-i", "/tmp/claude-0/sheet/%03d.png",
    "-vf", `scale=${W > H ? 320 : 216}:-1,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='%{eif\\:n*${step}\\:d}.%{eif\\:mod(n*${step * 10}\\,10)\\:d}s':x=6:y=6:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.6,tile=${cols}x${Math.ceil(files.length / cols)}:padding=4:color=0x222222`,
    "-frames:v", "1", b], { stdio: "inherit" }); p.on("exit", (c) => (c ? rej(new Error("ffmpeg " + c)) : res())); });
} else if (mode === "video") {
  const sub = +(b || 1), fps = info.fps;
  // Optional T0/T1 (seconds) render only part of the film, for checking fast moments.
  const F0 = Math.round((+process.env.T0 || 0) * fps), F1 = Math.round((+process.env.T1 || info.duration) * fps), N = F1;
  const vf = sub > 1 ? [`tmix=frames=${sub}`, `framestep=${sub}`] : [];
  const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps * sub), "-c:v", "png", "-i", "-",
    ...(vf.length ? ["-vf", vf.join(",")] : []), "-r", String(fps), "-c:v", "libx264", "-preset", "slow", "-crf", "16",
    "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart", a], { stdio: ["pipe", "inherit", "inherit"] });
  const t0 = Date.now();
  for (let f = F0; f < N; f++) {
    for (let s = 0; s < sub; s++) {
      // 180° shutter: subframes spread over the first half of the frame interval.
      const t = (f + (sub > 1 ? (s / sub) * 0.5 : 0)) / fps;
      const buf = await shot(t);
      if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
    }
    if (f % 120 === 0) console.log(`frame ${f}/${N}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on("exit", r));
}
if (errors.length) console.log("PAGE ERRORS:\n" + errors.join("\n"));
await browser.close();
