import DashboardLayout from "./DashboardLayout";
import ExecutionControls from "./components/ExecutionControls";
import { useExecutionRun } from "./telemetry/useExecutionRun";
import {
  toSessionInfo,
  toExecutionEvents,
  toMetrics,
  toWatchdogAlerts,
} from "./telemetry/liveAdapters";

// Day 9: final V1 dashboard. Everything shown comes from the finalized
// REST/WebSocket surface (POST /execute, GET /status/:id, WS /stream/:id):
//  - execution status      <- GET /status/:id (authoritative)
//  - lifecycle events      <- WS /stream/:id (payloads now included)
//  - latency / activity    <- /status timestamps + event timestamps/payloads
//  - Watchdog alerts       <- `payload.watchdog_alert` on tool_execution events
// useExecutionRun opens the stream before submitting the request so no
// lifecycle events are missed.
export default function App() {
  const run = useExecutionRun();
  const { live } = run;

  return (
    <main className="app">
      <header className="app__header">
        <h1>Nexus-Flow Dashboard</h1>
      </header>
      <ExecutionControls
        busy={run.busy}
        startError={run.startError}
        connectionError={live.connectionError}
        statusError={live.statusError}
        onStart={run.start}
      />
      <DashboardLayout
        session={toSessionInfo(live, run.phase)}
        events={toExecutionEvents(live)}
        metrics={toMetrics(live)}
        alerts={toWatchdogAlerts(live)}
      />
    </main>
  );
}