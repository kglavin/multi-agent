//! Message types shared by the browser actor and the server actor.
//! They travel as JSON text frames over the WebSocket.
//! With the `ts` feature, the stream types also become TypeScript types in the
//! wasm-bindgen output. The browser crate passes them through `tsify::Ts`.

use serde::{Deserialize, Serialize};
#[cfg(feature = "ts")]
use tsify::Tsify;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Request {
    pub id: u32,
    pub text: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Reply {
    pub id: u32,
    pub text: String,
    pub chars: u32,
    pub served_by: String,
}

/// Asks the server for `count` chunks in reply to one request.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[cfg_attr(feature = "ts", derive(Tsify))]
pub struct StreamRequest {
    pub id: u32,
    pub count: u32,
    pub text: String,
}

/// One reply in a stream. `last` is true on the final chunk.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[cfg_attr(feature = "ts", derive(Tsify))]
pub struct Chunk {
    pub id: u32,
    pub seq: u32,
    pub text: String,
    pub last: bool,
}

/// What the browser side reports when a stream ends.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[cfg_attr(feature = "ts", derive(Tsify))]
pub struct StreamSummary {
    pub id: u32,
    pub received: u32,
}

/// Any frame the browser sends. Untagged so that a plain `Request` keeps the
/// wire format used by S5 and S6. `Stream` is tried first because it has more fields.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(untagged)]
pub enum ClientFrame {
    Stream(StreamRequest),
    Ask(Request),
}
