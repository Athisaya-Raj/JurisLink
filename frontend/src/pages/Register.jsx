import { useNavigate } from 'react-router-dom'
import { UserRound, Briefcase, ArrowLeft } from 'lucide-react'
import '../styles/register.css'

/**
 * Register page - lets user choose between registering as User or Lawyer
 */
export default function Register() {
  const navigate = useNavigate()

  return (
    <div className="register-container">
      <div className="register-card">
        <div className="register-header">
          <h1>Create Your Account</h1>
          <p className="register-subtitle">
            Choose how you'd like to join JurisLink
          </p>
        </div>

        <div className="register-options">
          <button
            className="register-option register-option--user"
            onClick={() => navigate('/register/user')}
          >
            <div className="register-option__icon">
              <UserRound size={40} aria-hidden />
            </div>
            <div className="register-option__content">
              <h2>Register as User</h2>
              <p>I'm seeking legal assistance</p>
              <span className="register-option__cta">Get started →</span>
            </div>
          </button>

          <button
            className="register-option register-option--lawyer"
            onClick={() => navigate('/register/lawyer')}
          >
            <div className="register-option__icon">
              <Briefcase size={40} aria-hidden />
            </div>
            <div className="register-option__content">
              <h2>Register as Lawyer</h2>
              <p>I'm a legal professional</p>
              <span className="register-option__cta">Get started →</span>
            </div>
          </button>
        </div>

        <div className="register-footer">
          <button
            className="btn btn--ghost btn--sm"
            onClick={() => navigate('/login')}
          >
            <ArrowLeft size={15} aria-hidden /> Back to login
          </button>
        </div>
      </div>
    </div>
  )
}
