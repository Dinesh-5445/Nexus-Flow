import express, {Request, Response} from "express";
import http from "http";
import { WebSocketServer, WebSocket as WsWebSocket } from "ws";
import { randomUUID } from "crypto";
import { GatewayRequest, GatewayResponse, ExecutionEvent, EventLifecycle, InternalExecutionState } from "./types";
import path from "path";
import { spawn } from "child_process";

const app = express();
app.use(express.json());

const executionStatus = new Map<string, InternalExecutionState>();
const streamClients = new Map<string, Set<WsWebSocket>>();

// -- REST --
app.get("/health", (req: Request, res: Response) => {
    res.json({status: "ok"});
});

// Client submits a task. Real integration point is
// forwardToGateway() below.
app.post("/execute", async (req: Request, res: Response) => {
  const { request_id, messages, session_id, parameters } = req.body;

  if (!request_id || !Array.isArray(messages)) {
    return res.status(400).json({
      error: "Missing required fields: request_id, messages",
    });
  }

  executionStatus.set(request_id, {
    request_id,
    status: "pending",
    start_time: Date.now() / 1000
  });

  res.status(202).json({
    request_id,
    status: "started",
    execution_time_ms: 0,
    stream_url: `/stream/${request_id}`,
  });

  // Local bookkeeping event, fires immediately before the Python
  // subprocess is even spawned. Python's own REQUEST_RECEIVED event
  // (via onEvent below) will arrive shortly after — harmless duplicate,
  // emitEvent's state update is idempotent.
  emitEvent(request_id, "request_received");

  try {
    const gatewayRequest: GatewayRequest = {
      request_id, 
      messages, 
      session_id,
      parameters,
    }

    // Real intermediate + terminal events (execution_started,
    // llm_execution, tool_execution, completed/failed) are published
    // by the Gateway/Orchestrator inside the Python process and
    // relayed here via onEvent as they happen — forwarded live by
    // src/main.py's stdout-writer subscriber. Do NOT manually emit completed/failed after this resolves
    // — Python already publishes those through onEvent.
    await forwardToGateway(gatewayRequest, (event) => {
      emitEvent(event.request_id, event.event_type, event.payload);
    });
  }
  catch (err) {
    emitEvent(request_id, "failed", {
      error: err instanceof Error ? err.message : "Gateway process error",
    });
  }
});

// Polling fallback for status (alternative to WS stream)
app.get("/status/:execution_id", (req: Request<{ execution_id : string }>, res: Response) => {
    const { execution_id } = req.params;
    const status = executionStatus.get(execution_id);

    if(!status) {
      return res.status(404).json({error: "Unknown execution_id"});
    };

    res.json(status);
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

// Maps internal EventLifecycle values to the real ExecutionState status
// vocabulary (src/state/manager.py): 'pending' | 'running' | 'completed' | 'failed'
const toExecutionStateStatus = (eventType: string) => {
  switch(eventType) {
    case "request_received":
      return "pending";
    
    case "execution_started":
    case "llm_execution":
    case "tool_execution" :
      return "running";
    
    case "completed" :
      return "completed";
    
    case "failed" :
      return "failed";
    
    default:
      return "pending";
  }
}

const emitEvent = (requestId: string, eventType: EventLifecycle, payload?: Record<string, unknown>) => {
  const event: ExecutionEvent = {
    event_type: eventType,
    request_id: requestId,
    timestamp: Date.now()/1000, //seconds, matching Python's time.time()
    ...(payload !== undefined && { payload })
  };

  const state = executionStatus.get(requestId);

  if(state) {
    state.status = toExecutionStateStatus(eventType);

    if(eventType === "completed" || eventType === "failed") {
      state.end_time = Date.now() / 1000;
    }
  }
  
  const clients = streamClients.get(requestId);
  if(!clients) return;

  const message = JSON.stringify(event);

  for(const client of clients) {
    if(client.readyState === WsWebSocket.OPEN) {
      client.send(message);
    }
  }
}

// Real Gateway integration point. Spawns one Python subprocess per
// request (`python -m src.main`), writes the request as JSON to stdin,
// and reads newline-delimited JSON from stdout. Two object shapes are
// expected on stdout, one per line:
//   {"__type__": "Event", event_type, request_id, timestamp, payload}
//   {"__type__": "GatewayResponse", request_id, status, ...}
// Events are relayed live via onEvent as each line arrives; the final
// GatewayResponse resolves the returned promise once the process exits.
// Requires main.py to stream Event lines as they're published (not yet
// built as of writing — see logs/log.md) — until then, only the
// final GatewayResponse line will appear, no intermediate Event lines
const forwardToGateway = async ( request: GatewayRequest, onEvent: (event: ExecutionEvent) => void): Promise<GatewayResponse> => {
  return new Promise((resolve, reject) => {
    const rootDir = path.resolve(__dirname, "../../..");
    const pyProcess = spawn("python", ["-m", "src.main"], { cwd: rootDir });

    pyProcess.stdin.write(JSON.stringify(request) + "\n");
    pyProcess.stdin.end();

    let buffer = "";
    let finalResponse: GatewayResponse | null = null;

    pyProcess.stdout.on("data", (data: Buffer) => {
      // Python may write partial lines across multiple 'data' chunks,
      // so buffer and only process complete (newline-terminated) lines.
      buffer += data.toString();
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? ""; // keep incomplete last line for next chunk

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
          const parsed = JSON.parse(trimmed);
          if (parsed.__type__ === "GatewayResponse") {
            finalResponse = parsed;
          } else if (parsed.__type__ === "Event") {
            onEvent(parsed as ExecutionEvent);
          }
        } catch (e) {
          console.error("Failed to parse Python stdout line:", trimmed);
        }
      }
    });

    pyProcess.stderr.on("data", (data: Buffer) => {
      console.error("Python stderr:", data.toString());
    });

    pyProcess.on("close", () => {
      if (finalResponse) {
        resolve(finalResponse);
      } else {
        reject(new Error("Gateway process exited without a final response"));
      }
    });
  });
}

const PORT = process.env.PORT || 3000;

server.listen(PORT, () => {
    console.log(`API service running on port ${PORT}`);
});