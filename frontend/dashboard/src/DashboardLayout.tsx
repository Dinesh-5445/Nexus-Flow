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

// Day 9: all four props are populated from live REST/WebSocket data by
// App.tsx (telemetry/useExecutionRun + telemetry/liveAdapters). Alerts are the
// Watchdog annotations carried on tool_execution event payloads.
export default function DashboardLayout({
  session,
  events,
  metrics,
  alerts,
}: DashboardLayoutProps) {
  return (
    <div className="dashboard-layout">
      <SessionPanel session={session} />
      <MetricsPanel metrics={metrics} />
      <AlertsPanel alerts={alerts} />
      <EventStreamPanel events={events} />
    </div>
  );
}