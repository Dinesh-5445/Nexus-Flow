import DashboardLayout from "./DashboardLayout";
import {
  placeholderSession,
  placeholderEvents,
  placeholderMetrics,
  placeholderAlerts,
} from "./data/placeholderData";

// Uses local placeholder data only. Real data source
// (REST/WebSocket) is a dependency on Sayan's API.
export default function App() {
  return (
    <DashboardLayout
      session={placeholderSession}
      events={placeholderEvents}
      metrics={placeholderMetrics}
      alerts={placeholderAlerts}
    />
  );
}