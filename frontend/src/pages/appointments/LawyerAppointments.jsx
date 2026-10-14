import { useEffect, useState } from 'react'
import { Calendar, AlertCircle } from 'lucide-react'
import client, { apiErrorMessage } from '../../api/client.js'
import StatusBadge from '../../components/StatusBadge.jsx'
import EmptyState from '../../components/EmptyState.jsx'
import Spinner from '../../components/Spinner.jsx'
import ConfirmModal from '../../components/ConfirmModal.jsx'
import { useToast } from '../../context/ToastContext.jsx'
import { formatSlot } from '../../utils/format.js'

export default function LawyerAppointments() {
  const { addToast } = useToast()
  const [appointments, setAppointments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [toCancel, setToCancel] = useState(null)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await client.get('/appointments/for-me')
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

  const setStatus = async (appointmentId, status) => {
    try {
      await client.patch(`/appointments/${appointmentId}/status`, { status })
      addToast(`Appointment marked ${status}.`, 'success')
      load()
    } catch (err) {
      addToast(apiErrorMessage(err), 'error')
    }
  }

  const confirmCancel = async () => {
    if (!toCancel) return
    await setStatus(toCancel.appointment_id, 'cancelled')
    setToCancel(null)
  }

  if (loading) return <Spinner label="Loading appointments…" />

  return (
    <>
      <div className="page-head">
        <div>
          <h1>My appointments</h1>
          <p className="page-head__sub">Appointments clients have booked with you.</p>
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
          description="Client bookings will appear here."
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
              <div className="flex gap-8">
                {a.status === 'requested' && (
                  <button className="btn btn--secondary btn--sm" onClick={() => setStatus(a.appointment_id, 'booked')}>
                    Confirm
                  </button>
                )}
                {a.status === 'booked' && (
                  <button className="btn btn--secondary btn--sm" onClick={() => setStatus(a.appointment_id, 'completed')}>
                    Mark completed
                  </button>
                )}
                {(a.status === 'requested' || a.status === 'booked') && (
                  <button className="btn btn--outline-danger btn--sm" onClick={() => setToCancel(a)}>
                    Cancel
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <ConfirmModal
        open={!!toCancel}
        title="Cancel appointment?"
        message="This will free up the time slot for the client to rebook. This action cannot be undone."
        confirmLabel="Cancel appointment"
        danger
        onConfirm={confirmCancel}
        onCancel={() => setToCancel(null)}
      />
    </>
  )
}
