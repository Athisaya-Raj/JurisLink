export default function Spinner({ label = 'Loading…' }) {
  return (
    <div className="loading-block">
      <span className="spinner" aria-hidden />
      <span>{label}</span>
    </div>
  )
}
