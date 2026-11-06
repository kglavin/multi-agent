// Q3: loads the built React app (app/dist) in headless Chromium in each mode and
// measures main-thread responsiveness while the stream arrives.
// Needs the native server running on ws://127.0.0.1:9001.
//
//   node browser-q3.mjs [chunks...]     default 5000 20000, 3 runs each
import { chromium } from "playwright-core";
import { serve } from "./serve.mjs";

const executablePath = process.env.CHROMIUM ?? `${process.env.HOME}/.cache/ms-playwright/chromium_headless_shell-1148/chrome-linux/headless_shell`;
const sizes = process.argv.slice(2).map(Number);
const counts = sizes.length ? sizes : [5000, 20000];
const runs = 3;

// Records every animation frame and every long task (over 50 ms) on the main thread.
const probe = () => {
  window.__frames = [];
  const loop = (t) => { window.__frames.push(t); requestAnimationFrame(loop); };
  requestAnimationFrame(loop);
  window.__longtasks = [];
  new PerformanceObserver((list) => {
    for (const e of list.getEntries()) window.__longtasks.push({ start: e.startTime, duration: e.duration });
  }).observe({ type: "longtask", buffered: true });
};

const median = (xs) => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)];

function measure({ q3, frames, longtasks }) {
  const { first, end } = q3;
  const inWindow = frames.filter((t) => t >= first && t <= end);
  const before = frames.filter((t) => t < first).at(-1);
  const after = frames.find((t) => t > end);
  const ts = [before, ...inWindow, after].filter((t) => t !== undefined);
  const gaps = ts.slice(1).map((t, i) => t - ts[i]).sort((a, b) => a - b);
  const tasks = longtasks.filter((l) => l.start < end && l.start + l.duration > first);
  return {
    received: q3.received,
    first_chunk_ms: q3.first - q3.start,
    stream_ms: end - first,
    frames: inWindow.length,
    max_gap_ms: gaps.at(-1) ?? 0,
    p95_gap_ms: gaps[Math.floor(gaps.length * 0.95)] ?? 0,
    long_tasks: tasks.length,
    long_task_ms: tasks.reduce((s, l) => s + l.duration, 0),
    commits: q3.commits,
    messages: q3.messages,
  };
}

const server = await serve(8080);
const browser = await chromium.launch({ executablePath });
const rows = [];
try {
  for (const n of counts) {
    for (const mode of ["worker", "batch", "main"]) {
      const results = [];
      for (let i = 0; i < runs; i++) {
        const page = await browser.newPage();
        page.on("pageerror", (e) => console.log("pageerror:", e.message));
        await page.addInitScript(probe);
        await page.goto(`http://127.0.0.1:8080/app/dist/index.html?mode=${mode}&n=${n}`);
        await page.waitForFunction(() => window.__q3?.end > 0 || window.__q3?.error, null, { timeout: 120000 });
        await page.waitForTimeout(100);
        const raw = await page.evaluate(() => ({ q3: window.__q3, frames: window.__frames, longtasks: window.__longtasks }));
        if (raw.q3.error) throw new Error(`${mode} ${n}: ${raw.q3.error}`);
        results.push(measure(raw));
        await page.close();
      }
      const row = { mode, n };
      for (const key of Object.keys(results[0])) row[key] = Math.round(median(results.map((r) => r[key])));
      row.max_gap_range = results.map((r) => Math.round(r.max_gap_ms)).join("/");
      rows.push(row);
      console.log(JSON.stringify(row));
    }
  }
  console.table(rows);
  console.log("browser:", browser.version());
} finally {
  await browser.close();
  server.close();
}
