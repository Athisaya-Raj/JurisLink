export default function StatusBadge({ status }) {
  if (!status) return <span className="muted">—</span>
  const label = String(status).replace(/_/g, ' ')
  return <span className={`badge badge--${status}`}>{label}</span>
}
