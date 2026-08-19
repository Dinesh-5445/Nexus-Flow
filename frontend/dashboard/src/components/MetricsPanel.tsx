import type { Metrics } from "../types";

interface MetricsPanelProps {
  metrics: Metrics;
}

export default function MetricsPanel({ metrics }: MetricsPanelProps) {
  return (
    <section className="panel metrics-panel">
      <h2>Metrics</h2>
      <p>Latency: {metrics.latencyMs ?? "—"} ms</p>
      <p>Throughput: {metrics.throughputPerSec ?? "—"} /s</p>
    </section>
  );
}