import type { ExecutionEvent } from "../types";

interface EventStreamPanelProps {
  events: ExecutionEvent[];
}

export default function EventStreamPanel({ events }: EventStreamPanelProps) {
  return (
    <section className="panel event-stream-panel">
      <h2>Live Event Activity</h2>
      {/* Event item shape depends on Dinesh's shared event schema */}
      <ul>
        {events.length ? (
          events.map((e) => <li key={e.id}>{e.type}</li>)
        ) : (
          <li>No events yet</li>
        )}
      </ul>
    </section>
  );
}