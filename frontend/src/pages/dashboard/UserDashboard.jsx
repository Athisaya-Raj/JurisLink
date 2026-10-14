import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Plus,
  FileText,
  Calendar,
  Clock,
  AlertCircle,
  ChevronRight,
  UserRound,
} from 'lucide-react'
import client, { apiErrorMessage } from '../../api/client.js'
import StatusBadge from '../../components/StatusBadge.jsx'
import EmptyState from '../../components/EmptyState.jsx'
import Spinner from '../../components/Spinner.jsx'
import { formatDate, formatSlot } from '../../utils/format.js'

export default function UserDashboard() {
  const [summary, setSummary] = useState(null)
  const [cases, setCases] = useState([])
  const [appointments, setAppointments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    const load = async () => {
      setLoading(true)
      setError('')
      try {
        const [s, c, a] = await Promise.all([
          client.get('/dashboard/user'),
          client.get('/cases/mine'),
          client.get('/appointments/mine'),
        ])
        if (!active) return
        setSummary(s.data)
        setCases(c.data.cases || [])
        setAppointments(a.data.appointments || [])
      } catch (err) {
        if (active) setError(apiErrorMessage(err))
      } finally {
        if (active) setLoading(false)
      }
    }
    load()
    return () => {
      active = false
    }
  }, [])

  if (loading) return <Spinner label="Loading your dashboard…" />

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Welcome back</h1>
          <p className="page-head__sub">Track your legal cases and appointments.</p>
        </div>
        <div className="page-head__actions">
          <Link className="btn btn--primary" to="/cases/new">
            <Plus size={16} aria-hidden /> New case
          </Link>
        </div>
      </div>

      {error && (
        <div className="alert alert--error mb-16" role="alert">
          <AlertCircle size={18} aria-hidden /> {error}
        </div>
      )}

      <div className="grid grid--stats mb-16">
        <div className="stat-tile">
          <FileText size={20} className="stat-tile__icon" aria-hidden />
          <div className="stat-tile__label">Total cases</div>
          <div className="stat-tile__value">{summary?.total_cases ?? 0}</div>
        </div>
        <div className="stat-tile">
          <Clock size={20} className="stat-tile__icon" aria-hidden />
          <div className="stat-tile__label">Awaiting assignment</div>
          <div className="stat-tile__value">{summary?.awaiting_assignment ?? 0}</div>
        </div>
        <div className="stat-tile">
          <UserRound size={20} className="stat-tile__icon" aria-hidden />
          <div className="stat-tile__label">With a lawyer</div>
          <div className="stat-tile__value">{summary?.assigned_cases ?? 0}</div>
        </div>
        <div className="stat-tile">
          <Calendar size={20} className="stat-tile__icon" aria-hidden />
          <div className="stat-tile__label">Upcoming appointments</div>
          <div className="stat-tile__value">{summary?.upcoming_appointments ?? 0}</div>
        </div>
      </div>

      <div className="grid grid--2">
        <section>
          <div className="page-head">
            <h2>My cases</h2>
          </div>
          {cases.length === 0 ? (
            <EmptyState
              title="No cases yet"
              description="Submit your first legal issue and we will classify it and find a lawyer."
              action={
                <Link className="btn btn--primary" to="/cases/new">
                  <Plus size={16} aria-hidden /> Submit a case
                </Link>
              }
            />
          ) : (
            <div className="list">
              {cases.map((c) => (
                <Link key={c.case_id} className="list-item" to={`/cases/${c.case_id}`}>
                  <div className="list-item__main">
                    <div className="list-item__title">{c.title}</div>
                    <div className="list-item__meta">
                      <span>{c.case_id}</span>
                      <span>{c.predicted_category_name}</span>
                      <span>{formatDate(c.created_at)}</span>
                    </div>
                  </div>
                  <StatusBadge status={c.status} />
                  <ChevronRight size={18} className="muted" aria-hidden />
                </Link>
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="page-head">
            <h2>My appointments</h2>
            <Link className="btn btn--secondary btn--sm" to="/appointments">
              View all
            </Link>
          </div>
          {appointments.length === 0 ? (
            <EmptyState
              title="No appointments"
              description="Book a time slot with your assigned lawyer from a case's details."
            />
          ) : (
            <div className="list">
              {appointments.slice(0, 5).map((a) => (
                <div key={a.appointment_id} className="list-item">
                  <div className="list-item__main">
                    <div className="list-item__title">
                      {formatSlot(a.date, a.start_time, a.end_time)}
                    </div>
                    <div className="list-item__meta">
                      <span>{a.appointment_id}</span>
                      <span>Case {a.case_id}</span>
                    </div>
                  </div>
                  <StatusBadge status={a.status} />
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </>
  )
}
