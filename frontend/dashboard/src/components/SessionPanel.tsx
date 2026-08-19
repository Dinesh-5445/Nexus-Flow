import type { SessionInfo } from "../types";

interface SessionPanelProps {
  session: SessionInfo;
}

export default function SessionPanel({ session }: SessionPanelProps) {
  return (
    <section className="panel session-panel">
      <h2>Execution / Session</h2>
      {/* Real fields depend on Sayan's API + Dinesh's event schema */}
      <p>Session ID: {session.sessionId}</p>
      <p>Status: {session.status}</p>
    </section>
  );
}