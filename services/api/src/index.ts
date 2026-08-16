import express, {Request, Response} from "express";
import http from "http";
import { WebSocketServer } from "ws";

const app = express();
app.use(express.json());

// -- REST --
app.get("/health", (req: Request, res: Response) => {
    res.json({status: "ok"});
});

// Client submits a task. Stubbed for now - no real gateway call yet
app.post("/execute", (req: Request, res: Response) => {
    // TODO: validate payload, forward to gateway, return execution_id
});

// Polling fallback for status (alternative to WS stream)
app.get("/status/:execution_id", (req: Request, res: Response) => {
    // TODO: look up execution status
});

// -- WebSocket --
const server = http.createServer(app);
const wss = new WebSocketServer({ noServer: true });

// Upgrades HTTP -> WS only for /stream/:execution_id, rejects everything else
server.on("upgrade", (req, socket, head) => {
  const match = req.url?.match(/^\/stream\/([^/]+)/);
  if (!match) {
    socket.destroy();
    return;
  }
  
  wss.handleUpgrade(req, socket, head, (ws) => {
    console.log(`WS client connected for execution: ${match[1]}`);
    // TODO: register client, emit real events later
  });
});

const PORT = process.env.PORT || 3000;

server.listen(PORT, () => {
    console.log(`API service running on port ${PORT}`);
});