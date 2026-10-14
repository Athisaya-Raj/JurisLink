import { Link } from 'react-router-dom'
import { ShieldAlert } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'

export default function Unauthorized() {
  const { user } = useAuth()
  const home = user?.role === 'lawyer' ? '/lawyer' : '/dashboard'
  return (
    <div className="login-page">
      <div className="login-card" style={{ textAlign: 'center' }}>
        <ShieldAlert size={44} style={{ color: 'var(--danger-600)' }} aria-hidden />
        <h1 className="mt-16">Access denied</h1>
        <p className="login-card__sub">
          You do not have permission to view this page with your current account.
        </p>
        <Link className="btn btn--primary btn--block" to={home}>
          Go to my dashboard
        </Link>
      </div>
    </div>
  )
}
