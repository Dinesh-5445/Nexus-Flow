import type { WatchdogAlert } from "../types";
import { formatClock } from "../format";

interface AlertsPanelProps {
  alerts: WatchdogAlert[];
}

export default function AlertsPanel({ alerts }: AlertsPanelProps) {
  return (
    <section className="panel alerts-panel">
      <h2>Watchdog Alerts</h2>
      {alerts.length ? (
        <ul className="alerts">
          {alerts.map((a) => (
            <li key={a.id} className="alert">
              <p className="alert__message">{a.message}</p>
              <p className="alert__meta">
                <span className="mono">{a.anomalyType}</span> · {formatClock(a.detectedAt)}
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="empty">No active alerts</p>
      )}
    </section>
  );
}