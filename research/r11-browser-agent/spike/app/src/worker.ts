// Runs the wasm streaming actor in a Web Worker and forwards typed chunks to
// the page. With batch set, chunks are sent at most every 16 ms.
import init, { stream } from "../../pkg-web/browser.js";
import type { Chunk, FromWorker, ToWorker } from "./messages";

const ready = init();
const post = (m: FromWorker) => self.postMessage(m);

self.onmessage = async (e: MessageEvent<ToWorker>) => {
  const { url, req, batch } = e.data;
  let pending: Chunk[] = [];
  let timer: ReturnType<typeof setTimeout> | undefined;
  const flush = () => {
    timer = undefined;
    if (pending.length) post({ kind: "chunks", chunks: pending });
    pending = [];
  };
  try {
    await ready;
    const summary = await stream(url, req, (chunk) => {
      if (!batch) return post({ kind: "chunks", chunks: [chunk] });
      pending.push(chunk);
      timer ??= setTimeout(flush, 16);
    });
    clearTimeout(timer);
    flush();
    post({ kind: "done", summary });
  } catch (err) {
    post({ kind: "error", error: String(err) });
  }
};
