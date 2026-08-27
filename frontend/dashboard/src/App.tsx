import DashboardLayout from "./DashboardLayout";
import ExecutionMonitor from "./components/ExecutionMonitor";
import {
  placeholderSession,
  placeholderEvents,
  placeholderMetrics,
  placeholderAlerts,
} from "./data/placeholderData";

// DashboardLayout below still renders local placeholder data only —
// reconciling it with real data is a follow-up (see telemetry/README.md).
//
// Day 3: ExecutionMonitor is a new, separately-rendered minimal view wired
// directly to Sayan's real REST/WebSocket stream via the telemetry module.
// It is intentionally NOT merged into DashboardLayout's panels yet — that
// would mean reconciling ../types.ts (loose placeholders) with
// telemetry/types.ts (schema-accurate) and telemetry/liveTypes.ts (the
// live wire shape, which currently omits payload), which is out of scope
// for today's task.
export default function App() {
  return (
    <>
      <DashboardLayout
        session={placeholderSession}
        events={placeholderEvents}
        metrics={placeholderMetrics}
        alerts={placeholderAlerts}
      />
      <ExecutionMonitor />
    </>
  );
}