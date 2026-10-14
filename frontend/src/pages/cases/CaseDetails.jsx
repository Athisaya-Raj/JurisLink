import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  FileText,
  Sparkles,
  AlertCircle,
  Calendar,
  Clock,
  ShieldAlert,
  UserRound,
  ArrowLeft,
} from 'lucide-react'
import client, { apiErrorMessage } from '../../api/client.js'
import StatusBadge from '../../components/StatusBadge.jsx'
import CaseTimeline from '../../components/CaseTimeline.jsx'
import Spinner from '../../components/Spinner.jsx'
import EmptyState from '../../components/EmptyState.jsx'
import { formatDate, formatDateTime, formatConfidence, formatSlot } from '../../utils/format.js'

export default function CaseDetails() {
  const { id } = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [progressNotes, setProgressNotes] = useState([])
  const [notesLoading, setNotesLoading] = useState(false)

  useEffect(() => {
    let active = true
    const loadCaseData = async () => {
      setLoading(true)
      setError('')
      try {
        const res = await client.get(`/cases/${id}`)
        if (active) setData(res.data)
        
        // Note: Progress notes are lawyer-only, so we won't fetch them here
        // They'll be displayed in the timeline if they exist
      } catch (err) {
        if (active) setError(apiErrorMessage(err, 'Could not load this case.'))
      } finally {
        if (active) setLoading(false)
      }
    }
    loadCaseData()
    return () => {
      active = false
    }
  }, [id])

  if (loading) return <Spinner label="Loading case…" />

  if (error) {
    return (
      <>
        <Link className="btn btn--ghost btn--sm mb-16" to="/dashboard">
          <ArrowLeft size={15} aria-hidden /> Back
        </Link>
        <div className="alert alert--error" role="alert">
          <AlertCircle size={18} aria-hidden /> {error}
        </div>
      </>
    )
  }

  const { case: c, prediction, lawyer, appointments, invitation } = data

  return (
    <>
      <div className="page-head">
        <div>
          <Link className="btn btn--ghost btn--sm" to="/dashboard" style={{ marginBottom: 8 }}>
            <ArrowLeft size={15} aria-hidden /> Back to dashboard
          </Link>
          <h1>{c.title}</h1>
          <p className="page-head__sub">{c.case_id}</p>
        </div>
        <StatusBadge status={c.status} />
      </div>

      <div className="grid grid--2">
        <div>
          <div className="card">
            <div className="card__title">
              <FileText size={18} aria-hidden />
              <h3>Case details</h3>
            </div>
            <div className="detail-row">
              <span className="detail-row__label">Submitted</span>
              <span className="detail-row__value">{formatDateTime(c.created_at)}</span>
            </div>
            <div className="detail-row">
              <span className="detail-row__label">Description</span>
              <span className="detail-row__value">{c.description}</span>
            </div>
            {c.supporting_info && (
              <div className="detail-row">
                <span className="detail-row__label">Supporting info</span>
                <span className="detail-row__value">{c.supporting_info}</span>
              </div>
            )}
            {c.preferred_date && (
              <div className="detail-row">
                <span className="detail-row__label">Preferred date</span>
                <span className="detail-row__value">{formatDate(c.preferred_date)}</span>
              </div>
            )}
          </div>

          <div className="card">
            <div className="card__title">
              <Sparkles size={18} aria-hidden />
              <h3>Classification</h3>
            </div>
            <div className="detail-row">
              <span className="detail-row__label">Category</span>
              <span className="detail-row__value">
                <strong>{prediction?.category_name || c.predicted_category_name}</strong>{' '}
                <span className="muted">({prediction?.category_id || c.predicted_category_id})</span>
              </span>
            </div>
            <div className="detail-row">
              <span className="detail-row__label">Confidence</span>
              <span className="detail-row__value">
                {formatConfidence(prediction?.confidence ?? c.prediction_confidence)}
              </span>
            </div>
            {prediction?.explanation && (
              <div className="alert alert--disclaimer mt-16">
                <ShieldAlert size={16} aria-hidden />
                <span>{prediction.explanation}</span>
              </div>
            )}
          </div>
        </div>

        <div>
          <div className="card">
            <div className="card__title">
              <UserRound size={18} aria-hidden />
              <h3>Assigned lawyer</h3>
            </div>
            {lawyer ? (
              <>
                <div className="detail-row">
                  <span className="detail-row__label">Name</span>
                  <span className="detail-row__value">
                    <strong>{lawyer.name}</strong>
                  </span>
                </div>
                <div className="detail-row">
                  <span className="detail-row__label">Specialization</span>
                  <span className="detail-row__value">{lawyer.specialization_names?.join(', ')}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-row__label">Experience</span>
                  <span className="detail-row__value">{lawyer.years_experience} years</span>
                </div>
                {lawyer.profile_summary && (
                  <div className="detail-row">
                    <span className="detail-row__label">Profile</span>
                    <span className="detail-row__value muted">{lawyer.profile_summary}</span>
                  </div>
                )}
                <div className="mt-16">
                  <Link className="btn btn--primary" to={`/cases/${c.case_id}/book`}>
                    <Calendar size={16} aria-hidden /> Book an appointment
                  </Link>
                </div>
              </>
            ) : invitation?.status === 'pending' ? (
              <div className="alert alert--info">
                <Clock size={16} aria-hidden />
                <span>
                  Invitation sent to {invitation.lawyer_name || 'a lawyer'} — awaiting their
                  response.
                </span>
              </div>
            ) : invitation?.status === 'declined' ? (
              <div className="alert alert--warning">
                <AlertCircle size={16} aria-hidden />
                <span>
                  The invitation was declined — the case is being re-offered to another lawyer.
                </span>
              </div>
            ) : (
              <div className="alert alert--warning">
                <AlertCircle size={16} aria-hidden />
                <span>This case is pending assignment — no lawyer is currently available.</span>
              </div>
            )}
          </div>

          <div className="card">
            <div className="card__title">
              <Calendar size={18} aria-hidden />
              <h3>Appointments</h3>
            </div>
            {appointments.length === 0 ? (
              <EmptyState title="No appointments" description="Book a time slot to speak with your lawyer." />
            ) : (
              <div className="list">
                {appointments.map((a) => (
                  <div key={a.appointment_id} className="list-item">
                    <div className="list-item__main">
                      <div className="list-item__title">
                        {formatSlot(a.date, a.start_time, a.end_time)}
                      </div>
                      <div className="list-item__meta">{a.appointment_id}</div>
                    </div>
                    <StatusBadge status={a.status} />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <section className="mt-16">
        <div className="card">
          <div className="card__title">
            <Calendar size={18} aria-hidden />
            <h3>Case Timeline</h3>
          </div>
          <CaseTimeline caseData={data} isLawyerView={false} />
        </div>
      </section>
    </>
  )
}
