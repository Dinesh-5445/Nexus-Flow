import express, {Request, Response} from "express";
import http from "http";
import { WebSocketServer, WebSocket as WsWebSocket } from "ws";
import { randomUUID } from "crypto";
import { GatewayRequest, GatewayResponse, ExecutionEvent, EventLifecycle } from "./types";

const app = express();
app.use(express.json());

// In-memory placeholder state (foundation only, not for production)
const executionStatus = new Map<string, string>();
const streamClients = new Map<string, Set<WsWebSocket>>();

// -- REST --
app.get("/health", (req: Request, res: Response) => {
    res.json({status: "ok"});
});

// Client submits a task.  Uses simulateExecution() for now — kept as a
// minimal mock so the REST/WS layer can be tested independently of the
// real Gateway/Orchestrator process. Real integration point is
// forwardToGateway() below, not yet wired in (architecture not agreed).
app.post("/execute", (req: Request, res: Response) => {
  const { request_id, messages, session_id, parameters } = req.body;

  if (!request_id || !Array.isArray(messages)) {
    return res.status(400).json({
      error: "Missing required fields: request_id, messages",
    });
  }

  executionStatus.set(request_id, "request_received");

  // Mocked Gateway Response
  const mockResponse: GatewayResponse = {
    request_id,
    status: "started",
    execution_time_ms: 0,
  };

  res.status(202).json({
    ...mockResponse,
    stream_url: `/stream/${request_id}`,
  });

  simulateExecution(request_id);
});

// Polling fallback for status (alternative to WS stream)
app.get("/status/:execution_id", (req: Request<{ execution_id : string }>, res: Response) => {
    const { execution_id } = req.params;
    const status = executionStatus.get(execution_id);

    if(!status) {
      return res.status(404).json({error: "Unknown execution_id"});
    };

    res.json({request_id: execution_id, status});
});

// -- WebSocket --
const server = http.createServer(app);
const wss = new WebSocketServer({ noServer: true });

// Upgrades HTTP -> WS only for /stream/:execution_id, rejects everything else
server.on("upgrade", (req, socket, head) => {
  const match = req.url?.match(/^\/stream\/([^/]+)/);
  if(!match) {
    socket.destroy();
    return;
  }

  const executionId = match[1]!;
  
  wss.handleUpgrade(req, socket, head, (ws) => {
    if(!streamClients.has(executionId)) {
      streamClients.set(executionId, new Set());
    }

    streamClients.get(executionId)!.add(ws);

    ws.on("close", () => {
      streamClients.get(executionId)?.delete(ws);
    });
  });
});

const emitEvent = (requestId: string, eventType: EventLifecycle, payload?: Record<string, unknown>) => {
  const event: ExecutionEvent = {
    event_type: eventType,
    request_id: requestId,
    timestamp: Date.now()/1000, //seconds, matching Python's time.time()
    ...(payload !== undefined && { payload })
  };

  executionStatus.set(requestId, eventType);

  const clients = streamClients.get(requestId);

  if(!clients) return;

  const message = JSON.stringify(event);

  for(const client of clients) {
    if(client.readyState === WsWebSocket.OPEN) {
      client.send(message);
    }
  }
}

// Mocked event sequence standing in for real Gateway/Orchestrator events.
// Matches Dinesh's EventLifecycle enum exactly. Temporary testing
// mechanism only.
const simulateExecution = (requestId: string) => {
  const steps: EventLifecycle[] = [
    "request_received",
    "execution_started",
    "tool_execution",
    "completed",
  ];

  steps.forEach((eventType, i) => {
    setTimeout(() => emitEvent(requestId, eventType), (i + 1) * 500);
  });
};

// Placeholder for the real Gateway integration point.
// Transport/protocol (HTTP, gRPC, subprocess+stdio, queue, etc.) is not
// yet agreed as the official REST/WebSocket -> Gateway architecture —
// do not assume one here. Currently unused; /execute still uses
// simulateExecution() for mocked responses.
async function forwardToGateway(request: GatewayRequest): Promise<GatewayResponse> {
  throw new Error("Gateway integration not implemented yet");
}

const PORT = process.env.PORT || 3000;

server.listen(PORT, () => {
    console.log(`API service running on port ${PORT}`);
});