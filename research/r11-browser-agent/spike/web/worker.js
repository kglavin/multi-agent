// Q2: runs the wasm actor inside a module Web Worker.
import init, { local_ping, ask } from "../pkg-web/browser.js";

const ready = init();
self.onmessage = async (e) => {
  try {
    await ready;
    const isWorker = typeof WorkerGlobalScope !== "undefined" && self instanceof WorkerGlobalScope;
    const local = await local_ping("worker");
    const remote = JSON.parse(await ask(e.data.url, e.data.texts));
    self.postMessage({ in_worker: isWorker, local, remote });
  } catch (err) {
    self.postMessage({ error: String(err) });
  }
};
