// Types aligned with Dinesh's Gateway contracts
// Mocked/stubbed usage only for now - no real Gateway integration yet

export type EventLifecycle = 
| "request_received"
| "execution_started"
| "tool_execution"
| "completed"
| "failed";

// Mirrors Dinesh's Event dataclass
export interface ExecutionEvent {
    event_type: EventLifecycle;
    request_id: string;
    timestamp: number; // Unix timestamp (seconds) - matches Python's time.time()
    payload?: Record<string, unknown>;
}

// Mirrors Dinesh's 'Gateway Request' dataclass
export interface GatewayRequest {
    request_id: string;
    messages: Record<string, unknown>[];
    session_id?: string;
    parameters?: Record<string, unknown>[];
}

// Mirrors Dinesh's 'Gateway Response' dataclass
export interface GatewayResponse {
    request_id: string;
    status: string;
    result?: unknown;
    error?: string; 
    execution_time_ms: number;
}

