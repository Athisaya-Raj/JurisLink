import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Inbox,
  Briefcase,
  Calendar,
  CheckCircle2,
  AlertCircle,
  ChevronRight,
} from 'lucide-react'
import client, { apiErrorMessage } from '../../api/client.js'
import StatusBadge from '../../components/StatusBadge.jsx'
import EmptyState from '../../components/EmptyState.jsx'
import Spinner from '../../components/Spinner.jsx'
import { formatDate, formatSlot } from '../../utils/format.js'

export default function LawyerDashboard() {
  const [summary, setSummary] = useState(null)
  const [cases, setCases] = useState([])
  const [appointments, setAppointments] = useState([])
  const [slots, setSlots] = useState([])
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    const load = async () => {
      setLoading(true)
      setError('')
      try {
        const [s, c, a, me] = await Promise.all([
          client.get('/dashboard/lawyer'),
          client.get('/cases/assigned-to-me'),
          client.get('/appointments/for-me'),
          client.get('/lawyers/me/slots'),
        ])
        if (!active) return
        setSummary(s.data)
        setCases(c.data.cases || [])
        setAppointments(a.data.appointments || [])
        setSlots(me.data.slots || [])
        setProfile(me.data.lawyer)
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

  const pendingInvitations = (summary?.recent_invitations || []).filter(
    (i) => i.status === 'pending',
  )

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Lawyer dashboard</h1>
          <p className="page-head__sub">
            {profile?.name ? `${profile.name} · ` : ''}
            {profile?.specialization_names?.join(', ') || 'No specialization listed'}
          </p>
        </div>
      </div>

      {error && (
        <div className="alert alert--error mb-16" role="alert">
          <AlertCircle size={18} aria-hidden /> {error}
        </div>
      )}

      <div className="grid grid--stats mb-16">
        <div className="stat-tile">
          <Inbox size={20} className="stat-tile__icon" aria-hidden />
          <div className="stat-tile__label">Pending invitations</div>
          <div className="stat-tile__value">{summary?.pending_invitations ?? 0}</div>
        </div>
        <div className="stat-tile">
          <Briefcase size={20} className="stat-tile__icon" aria-hidden />
          <div className="stat-tile__label">Active cases</div>
          <div className="stat-tile__value">{summary?.accepted_cases ?? 0}</div>
        </div>
        <div className="stat-tile">
          <Calendar size={20} className="stat-tile__icon" aria-hidden />
          <div className="stat-tile__label">Upcoming appointments</div>
          <div className="stat-tile__value">{summary?.upcoming_appointments ?? 0}</div>
        </div>
        <div className="stat-tile">
          <CheckCircle2 size={20} className="stat-tile__icon" aria-hidden />
          <div className="stat-tile__label">Completed cases</div>
          <div className="stat-tile__value">{summary?.completed_cases ?? 0}</div>
        </div>
      </div>

      <div className="grid grid--2">
        <section>
          <div className="page-head">
            <h2>Case invitations</h2>
            <Link className="btn btn--secondary btn--sm" to="/lawyer/invitations">
              View all
            </Link>
          </div>
          {pendingInvitations.length === 0 ? (
            <EmptyState
              title="No pending invitations"
              description="New case invitations in your specialization will appear here."
              icon={Inbox}
            />
          ) : (
            <div className="list">
              {pendingInvitations.map((i) => (
                <Link key={i.invitation_id} className="list-item" to={`/lawyer/invitations/${i.invitation_id}`}>
                  <div className="list-item__main">
                    <div className="list-item__title">{i.case_title}</div>
                    <div className="list-item__meta">
                      <span>{i.case_id}</span>
                      <span>{i.predicted_category_name}</span>
                      <span>{formatDate(i.created_at)}</span>
                    </div>
                  </div>
                  <StatusBadge status={i.status} />
                  <ChevronRight size={18} className="muted" aria-hidden />
                </Link>
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="page-head">
            <h2>Upcoming appointments</h2>
            <Link className="btn btn--secondary btn--sm" to="/lawyer/appointments">
              View all
            </Link>
          </div>
          {appointments.length === 0 ? (
            <EmptyState title="No appointments" description="Client bookings will appear here." />
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

      <section className="mt-16">
        <div className="page-head">
          <h2>Active cases</h2>
        </div>
        {cases.length === 0 ? (
          <EmptyState
            title="No active cases"
            description="Accept an invitation to start working on a case."
            icon={Briefcase}
          />
        ) : (
          <div className="list">
            {cases.map((c) => (
              <Link key={c.case_id} className="list-item" to={`/lawyer/cases/${c.case_id}`}>
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

      <section className="mt-16">
        <div className="page-head">
          <h2>My availability</h2>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Time</th>
                <th>Status</th>
                <th>Booked by case</th>
              </tr>
            </thead>
            <tbody>
              {slots.map((slot) => (
                <tr key={slot.slot_id}>
                  <td>{formatDate(slot.date)}</td>
                  <td>
                    {slot.start_time}–{slot.end_time}
                  </td>
                  <td>
                    <StatusBadge status={slot.status} />
                  </td>
                  <td>{slot.appointment ? slot.appointment.case_id : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  )
}
