#!/usr/bin/env bash
# Builds the server, the wasm actor, and its JavaScript bindings.
set -euo pipefail
cd "$(dirname "$0")"
. "$HOME/.cargo/env"
cargo build -p server
cargo build -p browser --target wasm32-unknown-unknown
wasm=target/wasm32-unknown-unknown/debug/browser.wasm
wasm-bindgen --target nodejs --out-dir pkg "$wasm"
# The spike's package.json says "type": "module", but the nodejs target is CommonJS.
echo '{ "type": "commonjs" }' > pkg/package.json
wasm-bindgen --target web --out-dir pkg-web "$wasm"
