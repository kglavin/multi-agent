//! Browser side: a ractor thread-local actor compiled to wasm32-unknown-unknown.
//! Its state owns a WebSocket, which is not Send, so it uses ThreadLocalActor.

use futures::stream::{SplitSink, SplitStream};
use futures::{SinkExt, StreamExt};
use gloo_net::websocket::{futures::WebSocket, Message};
use futures::channel::mpsc;
use proto::{Chunk, Reply, Request, StreamRequest, StreamSummary};
use ractor::thread_local::{ThreadLocalActor, ThreadLocalActorSpawner};
use ractor::{call, ActorProcessingErr, ActorRef, RpcReplyPort};
use tsify::Ts;
use wasm_bindgen::prelude::*;

/// An actor with no network, to check that ractor runs in wasm at all.
#[derive(Default)]
struct Local;

enum LocalMsg {
    Ping(String, RpcReplyPort<String>),
}

impl ThreadLocalActor for Local {
    type Msg = LocalMsg;
    type State = u32;
    type Arguments = ();

    async fn pre_start(&self, _: ActorRef<Self::Msg>, _: ()) -> Result<u32, ActorProcessingErr> {
        Ok(0)
    }

    async fn handle(&self, _: ActorRef<Self::Msg>, msg: Self::Msg, count: &mut u32) -> Result<(), ActorProcessingErr> {
        let LocalMsg::Ping(text, port) = msg;
        *count += 1;
        let _ = port.send(format!("pong {count}: {text}"));
        Ok(())
    }
}

/// An actor that forwards requests to the server actor over a WebSocket.
#[derive(Default)]
struct Bridge;

enum BridgeMsg {
    Ask(String, RpcReplyPort<Reply>),
}

struct BridgeState {
    next_id: u32,
    tx: SplitSink<WebSocket, Message>,
    rx: SplitStream<WebSocket>,
}

impl ThreadLocalActor for Bridge {
    type Msg = BridgeMsg;
    type State = BridgeState;
    type Arguments = String;

    async fn pre_start(&self, _: ActorRef<Self::Msg>, url: String) -> Result<BridgeState, ActorProcessingErr> {
        let ws = WebSocket::open(&url).map_err(|e| format!("open {url}: {e}"))?;
        let (tx, rx) = ws.split();
        Ok(BridgeState { next_id: 1, tx, rx })
    }

    async fn handle(&self, _: ActorRef<Self::Msg>, msg: Self::Msg, s: &mut BridgeState) -> Result<(), ActorProcessingErr> {
        let BridgeMsg::Ask(text, port) = msg;
        let req = Request { id: s.next_id, text };
        s.next_id += 1;
        s.tx.send(Message::Text(serde_json::to_string(&req)?)).await?;
        let reply = match s.rx.next().await {
            Some(Ok(Message::Text(t))) => serde_json::from_str::<Reply>(&t)?,
            other => return Err(format!("unexpected frame: {other:?}").into()),
        };
        if reply.id != req.id {
            return Err(format!("reply id {} for request {}", reply.id, req.id).into());
        }
        let _ = port.send(reply);
        Ok(())
    }
}

fn js_err(e: impl std::fmt::Display) -> JsValue {
    JsValue::from_str(&e.to_string())
}

/// Spawns the local actor, sends it two pings, and returns the replies.
#[wasm_bindgen]
pub async fn local_ping(text: String) -> Result<String, JsValue> {
    let spawner = ThreadLocalActorSpawner::new();
    let (actor, handle) = Local::spawn(None, (), spawner).await.map_err(js_err)?;
    let a = call!(actor, LocalMsg::Ping, text.clone()).map_err(js_err)?;
    let b = call!(actor, LocalMsg::Ping, text).map_err(js_err)?;
    actor.stop(None);
    handle.await.map_err(js_err)?;
    Ok(format!("{a} | {b}"))
}

/// Spawns the bridge actor, asks the server actor once per text, and returns
/// the typed replies as a JSON array.
#[wasm_bindgen]
pub async fn ask(url: String, texts: Vec<String>) -> Result<String, JsValue> {
    let spawner = ThreadLocalActorSpawner::new();
    let (actor, handle) = Bridge::spawn(None, url, spawner).await.map_err(js_err)?;
    let mut replies = Vec::new();
    for text in texts {
        replies.push(call!(actor, BridgeMsg::Ask, text).map_err(js_err)?);
    }
    actor.stop(None);
    handle.await.map_err(js_err)?;
    serde_json::to_string(&replies).map_err(js_err)
}

/// An actor that sends one stream request and forwards each chunk to a channel
/// until the last one. The channel sender is Send, so it can travel in a message.
#[derive(Default)]
struct Streamer;

enum StreamerMsg {
    Stream(StreamRequest, mpsc::UnboundedSender<Chunk>, RpcReplyPort<u32>),
}

impl ThreadLocalActor for Streamer {
    type Msg = StreamerMsg;
    type State = BridgeState;
    type Arguments = String;

    async fn pre_start(&self, _: ActorRef<Self::Msg>, url: String) -> Result<BridgeState, ActorProcessingErr> {
        let ws = WebSocket::open(&url).map_err(|e| format!("open {url}: {e}"))?;
        let (tx, rx) = ws.split();
        Ok(BridgeState { next_id: 1, tx, rx })
    }

    async fn handle(&self, _: ActorRef<Self::Msg>, msg: Self::Msg, s: &mut BridgeState) -> Result<(), ActorProcessingErr> {
        let StreamerMsg::Stream(req, out, port) = msg;
        s.tx.send(Message::Text(serde_json::to_string(&req)?)).await?;
        let mut received = 0;
        loop {
            let chunk = match s.rx.next().await {
                Some(Ok(Message::Text(t))) => serde_json::from_str::<Chunk>(&t)?,
                other => return Err(format!("unexpected frame: {other:?}").into()),
            };
            if chunk.id != req.id || chunk.seq != received {
                return Err(format!("chunk {}/{} out of order, expected {}/{received}", chunk.id, chunk.seq, req.id).into());
            }
            received += 1;
            let last = chunk.last;
            let _ = out.unbounded_send(chunk);
            if last {
                break;
            }
        }
        let _ = port.send(received);
        Ok(())
    }
}

/// Spawns the streaming actor, sends one stream request, and calls `on_chunk`
/// with each typed chunk as it arrives. Resolves when the last chunk is in.
#[wasm_bindgen]
pub async fn stream(
    url: String,
    req: Ts<StreamRequest>,
    #[wasm_bindgen(unchecked_param_type = "(chunk: Chunk) => void")] on_chunk: js_sys::Function,
) -> Result<Ts<StreamSummary>, JsValue> {
    let req = req.to_rust().map_err(js_err)?;
    let id = req.id;
    let spawner = ThreadLocalActorSpawner::new();
    let (actor, handle) = Streamer::spawn(None, url, spawner).await.map_err(js_err)?;
    let (tx, mut rx) = mpsc::unbounded();
    let deliver = async {
        while let Some(chunk) = rx.next().await {
            let value = Ts::from_rust(&chunk).map_err(js_err)?;
            on_chunk.call1(&JsValue::NULL, &value.js_value())?;
        }
        Ok::<(), JsValue>(())
    };
    let ask = actor.call(|port| StreamerMsg::Stream(req, tx, port), None);
    let (result, delivered) = futures::join!(ask, deliver);
    delivered?;
    let received = result.map_err(js_err)?.success_or(()).map_err(|_| js_err("stream call failed"))?;
    actor.stop(None);
    handle.await.map_err(js_err)?;
    Ts::from_rust(&StreamSummary { id, received }).map_err(js_err)
}
