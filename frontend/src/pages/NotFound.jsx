import { Link } from 'react-router-dom'
import { FileQuestion } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="login-page">
      <div className="login-card" style={{ textAlign: 'center' }}>
        <FileQuestion size={44} style={{ color: 'var(--blue-600)' }} aria-hidden />
        <h1 className="mt-16">Page not found</h1>
        <p className="login-card__sub">The page you are looking for does not exist.</p>
        <Link className="btn btn--primary btn--block" to="/">
          Back to home
        </Link>
      </div>
    </div>
  )
}
