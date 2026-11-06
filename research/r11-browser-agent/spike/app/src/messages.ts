// Messages between the React app and the worker. The payload types come from
// the Rust structs through tsify, in the wasm-bindgen output.
import type { Chunk, StreamRequest, StreamSummary } from "../../pkg-web/browser.js";

export type { Chunk, StreamRequest, StreamSummary };

export type ToWorker = { url: string; req: StreamRequest; batch: boolean };

export type FromWorker =
  | { kind: "chunks"; chunks: Chunk[] }
  | { kind: "done"; summary: StreamSummary }
  | { kind: "error"; error: string };
