// Small presentation helpers shared by the dashboard panels.

/** HH:MM:SS.mmm in the viewer's local time, or "—" for empty/invalid input. */
export function formatClock(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const ms = String(d.getMilliseconds()).padStart(3, "0");
  return `${d.toLocaleTimeString([], { hour12: false })}.${ms}`;
}

export function formatMs(value: number | null): string {
  return value === null ? "—" : `${value} ms`;
}