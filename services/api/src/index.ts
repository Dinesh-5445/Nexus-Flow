import express, {Request, Response} from "express";
import http from "http";
import { WebSocketServer, WebSocket as WsWebSocket } from "ws";
import { randomUUID } from "crypto";
import { spawn } from "child_process";
import path from "path";
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

// Client submits a task. Stubbed for now - no real gateway call yet
app.post("/execute", (req: Request, res: Response) => {
  const {request_id, messages, _session_id, _parameters} = req.body;

  if(!request_id || !Array.isArray(messages)) {
    return res.status(400).json({
      error: "Missing required fields: request_id, messages",
    });
  };

  executionStatus.set(request_id, "request_received");

  // Mocked Gateway Response
  const mockResponse: GatewayResponse = {
    request_id,
    status: "started",
    execution_time_ms: 0
  };

  res.status(202).json({
    ...mockResponse,
    stream_url: `/stream/${request_id}`
  });

  executeGatewayRequest(request_id, messages, _session_id || "default-session");
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

const executeGatewayRequest = (requestId: string, messages: any[], sessionId: string) => {
  // Spawn the Python Gateway script from the repository root
  const rootDir = path.resolve(__dirname, "../../..");
  const pyProcess = spawn("python", ["-m", "src.main"], {
    cwd: rootDir
  });

  const reqObj = {
    request_id: requestId,
    session_id: sessionId,
    messages: messages
  };

  pyProcess.stdin.write(JSON.stringify(reqObj) + "\n");
  pyProcess.stdin.end();

  pyProcess.stdout.on("data", (data: Buffer) => {
    const lines = data.toString().split("\n");
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        const parsed = JSON.parse(trimmed);
        if (parsed.__type__ === "GatewayResponse") {
          // Execution completed
          executionStatus.set(requestId, parsed.status);
        } else if (parsed.event_type) {
          // Real emitted event
          emitEvent(requestId, parsed.event_type as EventLifecycle, parsed.payload);
        }
      } catch (e) {
        console.error("Failed to parse python stdout:", trimmed);
      }
    }
  });

  pyProcess.stderr.on("data", (data: Buffer) => {
    console.error("Python stderr:", data.toString());
  });
};

const PORT = process.env.PORT || 3000;

server.listen(PORT, () => {
    console.log(`API service running on port ${PORT}`);
});