// Runs the wasm actor under Node 22, as a stand-in for a browser.
// Node 22 provides setTimeout and WebSocket on globalThis, which the wasm glue uses.
//
// Node 22 has no global CloseEvent. gloo-net dispatches a synthetic CloseEvent when
// its WebSocket is dropped, to use up its one-shot close listener. Without CloseEvent
// that fails silently, and the real close event later calls a dropped callback.
// Browsers have CloseEvent, so this stand-in is needed only under Node.
globalThis.CloseEvent ??= class CloseEvent extends Event {
  constructor(type, init = {}) {
    super(type, init);
    this.code = init.code ?? 0;
    this.reason = init.reason ?? "";
    this.wasClean = init.wasClean ?? false;
  }
};

const { local_ping, ask } = await import("./pkg/browser.js");

const url = process.argv[2] ?? "ws://127.0.0.1:9001";
console.log("local:", await local_ping("hello"));
console.log("remote:", await ask(url, ["hello from wasm", "second request"]));
