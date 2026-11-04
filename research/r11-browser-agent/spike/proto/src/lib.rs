//! Message types shared by the browser actor and the server actor.
//! They travel as JSON text frames over the WebSocket.

use serde::{Deserialize, Serialize};

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
