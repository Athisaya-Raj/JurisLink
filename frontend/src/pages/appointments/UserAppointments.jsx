import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Calendar, AlertCircle, ChevronRight } from 'lucide-react'
import client, { apiErrorMessage } from '../../api/client.js'
import StatusBadge from '../../components/StatusBadge.jsx'
import EmptyState from '../../components/EmptyState.jsx'
import Spinner from '../../components/Spinner.jsx'
import ConfirmModal from '../../components/ConfirmModal.jsx'
import { useToast } from '../../context/ToastContext.jsx'
import { formatSlot } from '../../utils/format.js'

export default function UserAppointments() {
  const { addToast } = useToast()
  const [appointments, setAppointments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [toCancel, setToCancel] = useState(null)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await client.get('/appointments/mine')
      setAppointments(data.appointments || [])
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const cancelAppointment = async () => {
    if (!toCancel) return
    try {
      await client.patch(`/appointments/${toCancel.appointment_id}/status`, { status: 'cancelled' })
      addToast('Appointment cancelled.', 'success')
      setToCancel(null)
      load()
    } catch (err) {
      addToast(apiErrorMessage(err), 'error')
      setToCancel(null)
    }
  }

  if (loading) return <Spinner label="Loading appointments…" />

  return (
    <>
      <div className="page-head">
        <div>
          <h1>My appointments</h1>
          <p className="page-head__sub">Appointments you have booked with your lawyers.</p>
        </div>
      </div>

      {error && (
        <div className="alert alert--error mb-16" role="alert">
          <AlertCircle size={18} aria-hidden /> {error}
        </div>
      )}

      {appointments.length === 0 ? (
        <EmptyState
          title="No appointments"
          description="Book a time slot from one of your case details to get started."
          icon={Calendar}
        />
      ) : (
        <div className="list">
          {appointments.map((a) => (
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
              <Link className="btn btn--secondary btn--sm" to={`/cases/${a.case_id}`}>
                View case
              </Link>
              {a.status !== 'cancelled' && a.status !== 'completed' && (
                <button className="btn btn--outline-danger btn--sm" onClick={() => setToCancel(a)}>
                  Cancel
                </button>
              )}
              <ChevronRight size={16} className="muted" aria-hidden />
            </div>
          ))}
        </div>
      )}

      <ConfirmModal
        open={!!toCancel}
        title="Cancel appointment?"
        message="This will free up the time slot. This action cannot be undone."
        confirmLabel="Cancel appointment"
        danger
        onConfirm={cancelAppointment}
        onCancel={() => setToCancel(null)}
      />
    </>
  )
}
