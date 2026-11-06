//! Native side: a WebSocket listener that hands each request to a ractor actor
//! and writes the actor's reply back as JSON. A stream request gets `count`
//! chunks, each made by the actor and sent as soon as it is ready.

use futures_util::{SinkExt, StreamExt};
use proto::{Chunk, ClientFrame, Reply, Request, StreamRequest};
use ractor::{call, Actor, ActorProcessingErr, ActorRef, RpcReplyPort};
use tokio::net::TcpListener;
use tokio_tungstenite::tungstenite::Message;

struct Upper;

enum UpperMsg {
    Handle(Request, RpcReplyPort<Reply>),
    MakeChunk(StreamRequest, u32, RpcReplyPort<Chunk>),
}

impl Actor for Upper {
    type Msg = UpperMsg;
    type State = ();
    type Arguments = ();

    async fn pre_start(&self, _: ActorRef<Self::Msg>, _: ()) -> Result<(), ActorProcessingErr> {
        Ok(())
    }

    async fn handle(&self, _: ActorRef<Self::Msg>, msg: Self::Msg, _: &mut ()) -> Result<(), ActorProcessingErr> {
        match msg {
            UpperMsg::Handle(req, port) => {
                let reply = Reply {
                    id: req.id,
                    chars: req.text.chars().count() as u32,
                    text: req.text.to_uppercase(),
                    served_by: "server-actor".into(),
                };
                let _ = port.send(reply);
            }
            UpperMsg::MakeChunk(req, seq, port) => {
                let chunk = Chunk {
                    id: req.id,
                    seq,
                    text: format!("{} {seq}", req.text.to_uppercase()),
                    last: seq + 1 == req.count,
                };
                let _ = port.send(chunk);
            }
        }
        Ok(())
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let addr = std::env::args().nth(1).unwrap_or_else(|| "127.0.0.1:9001".into());
    let (actor, _) = Actor::spawn(Some("upper".into()), Upper, ()).await?;
    let listener = TcpListener::bind(&addr).await?;
    println!("listening on ws://{addr}");
    loop {
        let (stream, peer) = listener.accept().await?;
        let actor = actor.clone();
        tokio::spawn(async move {
            let mut ws = match tokio_tungstenite::accept_async(stream).await {
                Ok(ws) => ws,
                Err(e) => return eprintln!("handshake with {peer} failed: {e}"),
            };
            while let Some(Ok(frame)) = ws.next().await {
                let Message::Text(text) = frame else { continue };
                let frame: ClientFrame = match serde_json::from_str(&text) {
                    Ok(f) => f,
                    Err(e) => return eprintln!("bad request from {peer}: {e}"),
                };
                match frame {
                    ClientFrame::Ask(req) => {
                        println!("request {} from {peer}: {:?}", req.id, req.text);
                        let reply = call!(actor, UpperMsg::Handle, req).expect("actor call failed");
                        if ws.send(Message::text(serde_json::to_string(&reply).unwrap())).await.is_err() {
                            return;
                        }
                    }
                    ClientFrame::Stream(req) => {
                        println!("stream {} from {peer}: {} chunks", req.id, req.count);
                        for seq in 0..req.count {
                            let chunk = call!(actor, UpperMsg::MakeChunk, req.clone(), seq).expect("actor call failed");
                            if ws.send(Message::text(serde_json::to_string(&chunk).unwrap())).await.is_err() {
                                return;
                            }
                        }
                    }
                }
            }
        });
    }
}
