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

// Day 8: session/events/metrics are now populated from live REST/WebSocket
// data by App.tsx (via telemetry/useLiveExecution + telemetry/liveAdapters),
// not data/placeholderData.ts. `alerts` is still placeholder ([]) — no
// Watchdog alert endpoint exists on the API boundary yet.
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