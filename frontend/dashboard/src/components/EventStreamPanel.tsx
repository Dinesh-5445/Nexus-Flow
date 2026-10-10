import type { ExecutionEvent } from "../types";
import { formatClock } from "../format";

interface EventStreamPanelProps {
  events: ExecutionEvent[];
}

type StageState = "done" | "waiting" | "failed" | "none";

interface Stage {
  key: string;
  label: string;
  state: StageState;
  detail?: string;
}

// Observed-lifecycle strip: which lifecycle events have been seen so far.
// Derived from the events on screen only; the execution's authoritative
// status is shown in the Execution panel (from GET /status).
function buildStages(events: ExecutionEvent[]): Stage[] {
  const seen = (type: string) => events.some((e) => e.type === type);
  const toolCount = events.filter((e) => e.type === "tool_execution").length;
  const completed = seen("completed");
  const failed = seen("failed");
  const terminal = completed || failed;

  const stage = (key: string, label: string): Stage => ({
    key,
    label,
    state: seen(key) ? "done" : "waiting",
  });

  return [
    stage("request_received", "Received"),
    stage("execution_started", "Started"),
    stage("llm_execution", "LLM"),
    {
      key: "tool_execution",
      label: "Tools",
      state: toolCount > 0 ? "done" : terminal ? "none" : "waiting",
      detail: toolCount > 0 ? `×${toolCount}` : terminal ? "none" : undefined,
    },
    {
      key: "terminal",
      label: failed ? "Failed" : "Completed",
      state: failed ? "failed" : completed ? "done" : "waiting",
    },
  ];
}

export default function EventStreamPanel({ events }: EventStreamPanelProps) {
  const stages = buildStages(events);

  return (
    <section className="panel event-stream-panel">
      <h2>Live Event Activity</h2>
      <ol className="stages" aria-label="Observed lifecycle">
        {stages.map((s) => (
          <li key={s.key} className={`stage stage--${s.state}`}>
            {s.label}
            {s.detail ? ` ${s.detail}` : ""}
          </li>
        ))}
      </ol>
      {events.length ? (
        <ol className="events">
          {events.map((e) => (
            <li key={e.id} className={`event event--${e.tone}`}>
              <div className="event__head">
                <span className="event__type mono">{e.type}</span>
                {e.hasAlert && <span className="badge badge--alert">Watchdog alert</span>}
                <span className="event__offset">+{e.offsetMs} ms</span>
                <span className="event__time">{formatClock(e.timestamp)}</span>
              </div>
              {e.summary && <p className="event__summary">{e.summary}</p>}
              {e.payload !== undefined && (
                <details>
                  <summary>Payload</summary>
                  <pre>{JSON.stringify(e.payload, null, 2)}</pre>
                </details>
              )}
            </li>
          ))}
        </ol>
      ) : (
        <p className="empty">No events yet</p>
      )}
    </section>
  );
}