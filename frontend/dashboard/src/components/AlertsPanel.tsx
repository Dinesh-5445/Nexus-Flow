import type { WatchdogAlert } from "../types";

interface AlertsPanelProps {
  alerts: WatchdogAlert[];
}

export default function AlertsPanel({ alerts }: AlertsPanelProps) {
  return (
    <section className="panel alerts-panel">
      <h2>Watchdog Alerts</h2>
      {/* Alert shape depends on Koushik's watchdog alert format */}
      {alerts.length ? (
        <ul>
          {alerts.map((a) => (
            <li key={a.id}>{a.message}</li>
          ))}
        </ul>
      ) : (
        <p>No active alerts</p>
      )}
    </section>
  );
}