import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { Scale, LogOut, Menu, X, LayoutDashboard, Plus, Calendar, Inbox } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const isLawyer = user?.role === 'lawyer'

  const links = isLawyer
    ? [
        { to: '/lawyer', label: 'Dashboard', icon: LayoutDashboard },
        { to: '/lawyer/invitations', label: 'Invitations', icon: Inbox },
        { to: '/lawyer/appointments', label: 'Appointments', icon: Calendar },
      ]
    : [
        { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
        { to: '/cases/new', label: 'New Case', icon: Plus },
        { to: '/appointments', label: 'Appointments', icon: Calendar },
      ]

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="app-shell">
      <nav className="navbar">
        <div className="navbar__inner">
          <Link to="/" className="navbar__brand">
            <span className="navbar__brand-icon">
              <Scale size={18} aria-hidden />
            </span>
            JurisLink
          </Link>

          <div className={`navbar__links ${open ? 'navbar__links--open' : ''}`}>
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                className={({ isActive }) =>
                  `navbar__link ${isActive ? 'navbar__link--active' : ''}`
                }
                onClick={() => setOpen(false)}
              >
                <l.icon size={16} aria-hidden />
                {l.label}
              </NavLink>
            ))}
          </div>

          <div className="navbar__right">
            <div className="navbar__user">
              <strong>{isLawyer ? 'Lawyer' : 'Client'}</strong>
              {user?.username}
            </div>
            <button
              className="btn btn--sm"
              style={{ background: 'rgba(255,255,255,0.12)', color: '#fff' }}
              onClick={handleLogout}
              title="Log out"
            >
              <LogOut size={15} aria-hidden /> Log out
            </button>
            <button
              className="navbar__menu-btn"
              onClick={() => setOpen((o) => !o)}
              aria-label="Toggle navigation"
            >
              {open ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        </div>
      </nav>

      <main className="main">{children}</main>

      <footer className="footer">
        JurisLink — AI-assisted legal case intake. Automated classification is not legal advice.
      </footer>
    </div>
  )
}
