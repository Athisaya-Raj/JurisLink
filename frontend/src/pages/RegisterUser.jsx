import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, AlertCircle, CheckCircle } from 'lucide-react'
import client, { apiErrorMessage } from '../api/client.js'
import { useToast } from '../context/ToastContext.jsx'
import '../styles/register-form.css'

/**
 * User registration form
 */
export default function RegisterUser() {
  const navigate = useNavigate()
  const { addToast } = useToast()

  const [formData, setFormData] = useState({
    username: '',
    email: '',
    full_name: '',
    phone: '',
    location: '',
    password: '',
    password_confirm: '',
  })

  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  const validateForm = () => {
    const newErrors = {}

    if (!formData.username.trim()) {
      newErrors.username = 'Username is required'
    } else if (formData.username.length < 3) {
      newErrors.username = 'Username must be at least 3 characters'
    }

    if (!formData.email.trim()) {
      newErrors.email = 'Email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address'
    }

    if (!formData.full_name.trim()) {
      newErrors.full_name = 'Full name is required'
    }

    if (!formData.password) {
      newErrors.password = 'Password is required'
    } else if (formData.password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters'
    } else if (!/[A-Z]/.test(formData.password)) {
      newErrors.password = 'Password must contain at least one uppercase letter'
    } else if (!/[0-9]/.test(formData.password)) {
      newErrors.password = 'Password must contain at least one digit'
    }

    if (!formData.password_confirm) {
      newErrors.password_confirm = 'Please confirm your password'
    } else if (formData.password !== formData.password_confirm) {
      newErrors.password_confirm = 'Passwords do not match'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
    // Clear error for this field when user starts typing
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }))
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    setLoading(true)
    try {
      await client.post('/auth/register/user', {
        username: formData.username.trim(),
        email: formData.email.trim().toLowerCase(),
        full_name: formData.full_name.trim(),
        phone: formData.phone.trim() || null,
        location: formData.location.trim() || null,
        password: formData.password,
      })

      setSuccess(true)
      addToast('Account created successfully! Redirecting to login...', 'success')

      setTimeout(() => {
        navigate('/login')
      }, 2000)
    } catch (err) {
      const message = apiErrorMessage(err, 'Registration failed')
      addToast(message, 'error')
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="register-form-container">
        <div className="register-form-card">
          <div className="success-state">
            <CheckCircle size={48} className="success-icon" aria-hidden />
            <h2>Registration Successful!</h2>
            <p>Your account has been created. You'll be redirected to login shortly.</p>
            <Link to="/login" className="btn btn--primary">
              Go to Login
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="register-form-container">
      <div className="register-form-card">
        <div className="register-form-header">
          <h1>Register as User</h1>
          <p>Create your account to start seeking legal assistance</p>
        </div>

        <form onSubmit={handleSubmit} className="register-form">
          <div className="form-field">
            <label htmlFor="username" className="form-label">
              Username *
            </label>
            <input
              id="username"
              type="text"
              name="username"
              className={`form-input ${errors.username ? 'is-error' : ''}`}
              placeholder="Choose a username"
              value={formData.username}
              onChange={handleChange}
              disabled={loading}
            />
            {errors.username && (
              <span className="form-error">
                <AlertCircle size={14} aria-hidden /> {errors.username}
              </span>
            )}
          </div>

          <div className="form-field">
            <label htmlFor="email" className="form-label">
              Email Address *
            </label>
            <input
              id="email"
              type="email"
              name="email"
              className={`form-input ${errors.email ? 'is-error' : ''}`}
              placeholder="your.email@example.com"
              value={formData.email}
              onChange={handleChange}
              disabled={loading}
            />
            {errors.email && (
              <span className="form-error">
                <AlertCircle size={14} aria-hidden /> {errors.email}
              </span>
            )}
          </div>

          <div className="form-field">
            <label htmlFor="full_name" className="form-label">
              Full Name *
            </label>
            <input
              id="full_name"
              type="text"
              name="full_name"
              className={`form-input ${errors.full_name ? 'is-error' : ''}`}
              placeholder="Your full name"
              value={formData.full_name}
              onChange={handleChange}
              disabled={loading}
            />
            {errors.full_name && (
              <span className="form-error">
                <AlertCircle size={14} aria-hidden /> {errors.full_name}
              </span>
            )}
          </div>

          <div className="form-field">
            <label htmlFor="phone" className="form-label">
              Phone Number
            </label>
            <input
              id="phone"
              type="tel"
              name="phone"
              className="form-input"
              placeholder="+1 (555) 123-4567"
              value={formData.phone}
              onChange={handleChange}
              disabled={loading}
            />
          </div>

          <div className="form-field">
            <label htmlFor="location" className="form-label">
              City or Location
            </label>
            <input
              id="location"
              type="text"
              name="location"
              className="form-input"
              placeholder="Your city or region"
              value={formData.location}
              onChange={handleChange}
              disabled={loading}
            />
          </div>

          <div className="form-field">
            <label htmlFor="password" className="form-label">
              Password *
            </label>
            <input
              id="password"
              type="password"
              name="password"
              className={`form-input ${errors.password ? 'is-error' : ''}`}
              placeholder="Create a strong password"
              value={formData.password}
              onChange={handleChange}
              disabled={loading}
            />
            {errors.password && (
              <span className="form-error">
                <AlertCircle size={14} aria-hidden /> {errors.password}
              </span>
            )}
            <p className="form-hint">
              At least 6 characters, including uppercase letter and number
            </p>
          </div>

          <div className="form-field">
            <label htmlFor="password_confirm" className="form-label">
              Confirm Password *
            </label>
            <input
              id="password_confirm"
              type="password"
              name="password_confirm"
              className={`form-input ${errors.password_confirm ? 'is-error' : ''}`}
              placeholder="Re-enter your password"
              value={formData.password_confirm}
              onChange={handleChange}
              disabled={loading}
            />
            {errors.password_confirm && (
              <span className="form-error">
                <AlertCircle size={14} aria-hidden /> {errors.password_confirm}
              </span>
            )}
          </div>

          <button
            type="submit"
            className="btn btn--primary btn--large"
            disabled={loading}
          >
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        <div className="register-form-footer">
          <p>
            Already have an account?{' '}
            <Link to="/login" className="link">
              Log in here
            </Link>
          </p>
          <button
            className="btn btn--ghost btn--sm"
            onClick={() => window.history.back()}
          >
            <ArrowLeft size={15} aria-hidden /> Go back
          </button>
        </div>
      </div>
    </div>
  )
}
