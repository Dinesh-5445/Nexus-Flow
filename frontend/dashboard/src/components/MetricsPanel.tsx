import type { Metrics } from "../types";
import { formatMs } from "../format";

interface MetricsPanelProps {
  metrics: Metrics;
}

export default function MetricsPanel({ metrics }: MetricsPanelProps) {
  return (
    <section className="panel metrics-panel">
      <h2>Telemetry</h2>
      <dl className="kv">
        <dt title="API-side: /status end_time − start_time. Includes gateway process startup.">
          Request latency
        </dt>
        <dd>{formatMs(metrics.endToEndMs)}</dd>
        <dt title="Span between the first and last lifecycle event.">Pipeline time</dt>
        <dd>{formatMs(metrics.pipelineMs)}</dd>
        <dt>Events received</dt>
        <dd>{metrics.eventCount}</dd>
        <dt>Tool calls</dt>
        <dd>{metrics.toolCalls}</dd>
        <dt title="Sum of execution_time_ms reported by tool_execution events.">Tool time</dt>
        <dd>{formatMs(metrics.toolTimeMs)}</dd>
      </dl>
      {metrics.eventCounts.length > 0 && (
        <ul className="chips" aria-label="Events by type">
          {metrics.eventCounts.map((c) => (
            <li key={c.type} className="chip mono">
              {c.type} ×{c.count}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}