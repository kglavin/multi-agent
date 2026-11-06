// Sends one typed stream request and renders the typed replies.
// Query parameters: mode = worker (one message per chunk), batch (worker, batched
// every 16 ms), or main (actor on the main thread). n = chunks. ws = server URL.
import { useEffect, useRef, useState } from "react";
import init, { stream } from "../../pkg-web/browser.js";
import type { Chunk, FromWorker, StreamRequest, ToWorker } from "./messages";

type Mode = "worker" | "batch" | "main";
type View = { received: number; recent: Chunk[]; done: boolean; error?: string };

const params = new URLSearchParams(location.search);
const mode = (params.get("mode") ?? "worker") as Mode;
const count = Number(params.get("n") ?? 5000);
const url = params.get("ws") ?? "ws://127.0.0.1:9001";

// Read by browser-q3.mjs.
// commits counts React commits that changed the view. messages counts worker messages.
const stats = { mode, count, start: 0, first: 0, end: 0, received: 0, commits: 0, messages: 0, error: "" };
declare global {
  interface Window { __q3: typeof stats; }
}
window.__q3 = stats;

export function App() {
  const [view, setView] = useState<View>({ received: 0, recent: [], done: false });
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const add = (chunks: Chunk[]) => {
      if (!stats.first) stats.first = performance.now();
      setView((v) => ({
        received: v.received + chunks.length,
        recent: [...v.recent, ...chunks].slice(-20),
        done: v.done || chunks.some((c) => c.last),
      }));
    };
    const fail = (error: string) => setView((v) => ({ ...v, error }));
    const req: StreamRequest = { id: 1, count, text: "chunk" };
    stats.start = performance.now();
    if (mode === "main") {
      init().then(() => stream(url, req, (c) => add([c]))).catch((e) => fail(String(e)));
    } else {
      const worker = new Worker(new URL("./worker.ts", import.meta.url), { type: "module" });
      worker.onmessage = (e: MessageEvent<FromWorker>) => {
        const m = e.data;
        stats.messages += 1;
        if (m.kind === "chunks") add(m.chunks);
        else if (m.kind === "error") fail(m.error);
      };
      worker.postMessage({ url, req, batch: mode === "batch" } satisfies ToWorker);
    }
  }, []);

  useEffect(() => {
    stats.commits += 1;
    stats.received = view.received;
    stats.error = view.error ?? "";
    if (view.done && !stats.end) stats.end = performance.now();
  }, [view]);

  return (
    <>
      <h1>R11 Q3: {mode}</h1>
      <p>
        {view.received} of {count} chunks{view.done ? ", done" : ""}{view.error ? `, error: ${view.error}` : ""}
      </p>
      <ol>
        {view.recent.map((c) => (
          <li key={c.seq}>{c.seq}: {c.text}</li>
        ))}
      </ol>
    </>
  );
}
