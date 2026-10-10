import type { SessionInfo } from "../types";
import { formatClock } from "../format";

interface SessionPanelProps {
  session: SessionInfo;
}

const STATUS_LABEL: Record<SessionInfo["status"], string> = {
  idle: "Idle",
  starting: "Starting",
  pending: "Pending",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
};

const STREAM_LABEL: Record<SessionInfo["stream"], string> = {
  idle: "Not connected",
  connecting: "Connecting",
  open: "Live",
  closed: "Closed",
  error: "Error",
};

export default function SessionPanel({ session }: SessionPanelProps) {
  return (
    <section className="panel session-panel">
      <h2>Execution</h2>
      <p className="session-status">
        <span
          className={`badge badge--status-${session.status}`}
          role="status"
          aria-live="polite"
        >
          {STATUS_LABEL[session.status]}
        </span>
        <span className={`badge badge--stream-${session.stream}`}>
          Stream: {STREAM_LABEL[session.stream]}
        </span>
      </p>
      <dl className="kv">
        <dt>Execution ID</dt>
        <dd className="mono">{session.executionId ?? "—"}</dd>
        <dt>Started</dt>
        <dd>{formatClock(session.startedAt)}</dd>
        <dt>Ended</dt>
        <dd>{formatClock(session.endedAt)}</dd>
      </dl>
      {session.status === "failed" && (
        <p role="alert" className="notice notice--error">
          {session.error ?? "Execution failed (no error detail provided)"}
        </p>
      )}
    </section>
  );
}