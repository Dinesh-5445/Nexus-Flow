import SessionPanel from "./components/SessionPanel";
import EventStreamPanel from "./components/EventStreamPanel";
import MetricsPanel from "./components/MetricsPanel";
import AlertsPanel from "./components/AlertsPanel";
import type { SessionInfo, ExecutionEvent, Metrics, WatchdogAlert } from "./types";

interface DashboardLayoutProps {
  session: SessionInfo;
  events: ExecutionEvent[];
  metrics: Metrics;
  alerts: WatchdogAlert[];
}

// Foundation only — not wired to real data yet.
// Will be replaced with live WebSocket/REST data once
// Sayan's API and the shared event schema are available.
export default function DashboardLayout({
  session,
  events,
  metrics,
  alerts,
}: DashboardLayoutProps) {
  return (
    <div className="dashboard-layout">
      <SessionPanel session={session} />
      <EventStreamPanel events={events} />
      <MetricsPanel metrics={metrics} />
      <AlertsPanel alerts={alerts} />
    </div>
  );
}