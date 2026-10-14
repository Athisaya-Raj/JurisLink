import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Scale, LogIn, AlertCircle } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'
import { apiErrorMessage } from '../api/client.js'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const user = await login(username, password)
      navigate(user.role === 'lawyer' ? '/lawyer' : '/dashboard', { replace: true })
    } catch (err) {
      setError(apiErrorMessage(err, 'Invalid username or password.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="login-card__brand">
          <span className="login-card__brand-icon">
            <Scale size={22} aria-hidden />
          </span>
        </div>
        <h1>JurisLink</h1>
        <p className="login-card__sub">AI-assisted legal case intake &amp; lawyer booking</p>

        {error && (
          <div className="alert alert--error mb-16" role="alert">
            <AlertCircle size={18} aria-hidden />
            <span>{error}</span>
          </div>
        )}

        <div className="form-field">
          <label className="form-label" htmlFor="username">
            Username
          </label>
          <input
            id="username"
            className="input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            className="input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </div>

        <button className="btn btn--primary btn--block" type="submit" disabled={loading}>
          {loading ? (
            <span className="spinner" aria-hidden />
          ) : (
            <LogIn size={16} aria-hidden />
          )}
          {loading ? 'Signing in…' : 'Sign in'}
        </button>

        <div className="demo-hint">
          Demo accounts: <code>user</code> / <code>user</code> · <code>lawyer</code> /{' '}
          <code>lawyer</code>
        </div>
      </form>
    </div>
  )
}
