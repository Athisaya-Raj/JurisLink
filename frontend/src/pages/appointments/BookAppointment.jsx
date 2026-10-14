import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { Calendar, AlertCircle, CheckCircle2, ArrowLeft, UserRound } from 'lucide-react'
import client, { apiErrorMessage } from '../../api/client.js'
import Spinner from '../../components/Spinner.jsx'
import EmptyState from '../../components/EmptyState.jsx'
import { useToast } from '../../context/ToastContext.jsx'
import { formatSlot } from '../../utils/format.js'

export default function BookAppointment() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { addToast } = useToast()
  const [slots, setSlots] = useState([])
  const [lawyer, setLawyer] = useState(null)
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [booking, setBooking] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    client
      .get(`/cases/${id}/slots`)
      .then((res) => {
        if (!active) return
        setSlots(res.data.slots || [])
        setLawyer(res.data.lawyer)
      })
      .catch((err) => {
        if (active) setError(apiErrorMessage(err, 'Could not load available slots.'))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [id])

  const confirmBooking = async () => {
    if (!selected) return
    setBooking(true)
    setError('')
    try {
      const { data } = await client.post('/appointments', {
        case_id: id,
        slot_id: selected,
      })
      addToast(`Appointment ${data.appointment.appointment_id} booked.`, 'success')
      navigate(`/cases/${id}`, { replace: true })
    } catch (err) {
      setError(apiErrorMessage(err))
      setBooking(false)
    }
  }

  if (loading) return <Spinner label="Loading available slots…" />

  return (
    <>
      <div className="page-head">
        <div>
          <Link className="btn btn--ghost btn--sm" to={`/cases/${id}`} style={{ marginBottom: 8 }}>
            <ArrowLeft size={15} aria-hidden /> Back to case
          </Link>
          <h1>Book an appointment</h1>
          <p className="page-head__sub">Choose an available time slot with your assigned lawyer.</p>
        </div>
      </div>

      {error && (
        <div className="alert alert--error mb-16" role="alert">
          <AlertCircle size={18} aria-hidden /> {error}
        </div>
      )}

      {lawyer && (
        <div className="card mb-16">
          <div className="card__title">
            <UserRound size={18} aria-hidden />
            <h3>{lawyer.name}</h3>
          </div>
          <p className="muted small">{lawyer.specialization_names?.join(', ')}</p>
        </div>
      )}

      {slots.length === 0 ? (
        <EmptyState
          title="No available slots"
          description="Your lawyer has no open time slots right now. Please check back later."
          icon={Calendar}
        />
      ) : (
        <>
          <h2 className="mb-16">Available slots</h2>
          <div className="slot-grid">
            {slots.map((slot) => {
              const isSelected = selected === slot.slot_id
              return (
                <button
                  key={slot.slot_id}
                  type="button"
                  className={`slot-option ${isSelected ? 'slot-option--selected' : ''}`}
                  onClick={() => setSelected(slot.slot_id)}
                >
                  <div className="slot-option__date">{formatSlot(slot.date, slot.start_time, slot.end_time)}</div>
                </button>
              )
            })}
          </div>

          <div className="card mt-16">
            <div className="flex flex--between">
              <div>
                {selected ? (
                  <span>
                    Selected:{' '}
                    <strong>
                      {formatSlot(
                        slots.find((s) => s.slot_id === selected)?.date,
                        slots.find((s) => s.slot_id === selected)?.start_time,
                        slots.find((s) => s.slot_id === selected)?.end_time,
                      )}
                    </strong>
                  </span>
                ) : (
                  <span className="muted">Select a time slot to continue.</span>
                )}
              </div>
              <button
                className="btn btn--primary"
                onClick={confirmBooking}
                disabled={!selected || booking}
              >
                {booking ? (
                  <span className="spinner" aria-hidden />
                ) : (
                  <CheckCircle2 size={16} aria-hidden />
                )}
                {booking ? 'Booking…' : 'Confirm booking'}
              </button>
            </div>
          </div>
        </>
      )}
    </>
  )
}
