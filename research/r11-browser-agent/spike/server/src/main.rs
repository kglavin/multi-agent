//! Native side: a WebSocket listener that hands each request to a ractor actor
//! and writes the actor's reply back as JSON.

use futures_util::{SinkExt, StreamExt};
use proto::{Reply, Request};
use ractor::{call, Actor, ActorProcessingErr, ActorRef, RpcReplyPort};
use tokio::net::TcpListener;
use tokio_tungstenite::tungstenite::Message;

struct Upper;

enum UpperMsg {
    Handle(Request, RpcReplyPort<Reply>),
}

impl Actor for Upper {
    type Msg = UpperMsg;
    type State = ();
    type Arguments = ();

    async fn pre_start(&self, _: ActorRef<Self::Msg>, _: ()) -> Result<(), ActorProcessingErr> {
        Ok(())
    }

    async fn handle(&self, _: ActorRef<Self::Msg>, msg: Self::Msg, _: &mut ()) -> Result<(), ActorProcessingErr> {
        let UpperMsg::Handle(req, port) = msg;
        let reply = Reply {
            id: req.id,
            chars: req.text.chars().count() as u32,
            text: req.text.to_uppercase(),
            served_by: "server-actor".into(),
        };
        let _ = port.send(reply);
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
                let req: Request = match serde_json::from_str(&text) {
                    Ok(r) => r,
                    Err(e) => return eprintln!("bad request from {peer}: {e}"),
                };
                println!("request {} from {peer}: {:?}", req.id, req.text);
                let reply = call!(actor, UpperMsg::Handle, req).expect("actor call failed");
                if ws.send(Message::text(serde_json::to_string(&reply).unwrap())).await.is_err() {
                    return;
                }
            }
        });
    }
}
