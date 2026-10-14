import {
  CheckCircle2,
  Clock,
  AlertCircle,
  Sparkles,
  User,
  Calendar,
  FileText,
  CheckCircle,
} from 'lucide-react'
import { formatDateTime, formatSlot } from '../utils/format.js'
import '../styles/case-timeline.css'

/**
 * CaseTimeline component displays a chronological timeline of case events.
 * 
 * Props:
 *   - caseData: { case, prediction, lawyer, invitation, appointments, progressNotes }
 *   - isLawyerView: boolean - if true, show lawyer-specific actions
 */
export default function CaseTimeline({ caseData, isLawyerView = false }) {
  if (!caseData) return null

  const { case: c, prediction, lawyer, invitation, appointments, progressNotes } = caseData

  // Build timeline events from case data
  const events = []

  // 1. Case Submitted
  if (c.created_at) {
    events.push({
      id: 'submitted',
      stage: 'Case Submitted',
      icon: FileText,
      completed: true,
      timestamp: c.created_at,
      details: c.title,
    })
  }

  // 2. AI Classification Completed
  if (prediction || c.predicted_category_id) {
    events.push({
      id: 'classified',
      stage: 'AI Classification Completed',
      icon: Sparkles,
      completed: true,
      timestamp: c.created_at, // same as submission
      details: `${prediction?.category_name || c.predicted_category_name} (${(prediction?.confidence ?? c.prediction_confidence * 100).toFixed(0)}% confidence)`,
    })
  }

  // 3. Lawyer Matched
  if (lawyer || invitation) {
    events.push({
      id: 'matched',
      stage: 'Lawyer Matched',
      icon: User,
      completed: !!lawyer || invitation?.status !== 'pending',
      timestamp: invitation?.created_at || c.created_at,
      details: lawyer?.name || invitation?.lawyer_name || 'Pending',
    })
  }

  // 4. Invitation Sent
  if (invitation) {
    events.push({
      id: 'invitation_sent',
      stage: 'Invitation Sent',
      icon: AlertCircle,
      completed: true,
      timestamp: invitation.created_at,
      details: `Status: ${invitation.status}`,
    })
  }

  // 5. Lawyer Accepted
  if (lawyer && c.assigned_lawyer_id) {
    events.push({
      id: 'accepted',
      stage: 'Lawyer Accepted',
      icon: CheckCircle2,
      completed: true,
      timestamp: c.accepted_at || c.updated_at,
      details: `${lawyer.name} accepted on ${formatDateTime(c.accepted_at || c.updated_at)}`,
    })
  } else if (invitation?.status === 'declined') {
    events.push({
      id: 'declined',
      stage: 'Invitation Declined',
      icon: AlertCircle,
      completed: true,
      timestamp: invitation.responded_at || invitation.created_at,
      details: invitation.decline_reason || 'Case declined, reassigning...',
    })
  } else if (invitation?.status === 'pending') {
    events.push({
      id: 'pending_response',
      stage: 'Awaiting Lawyer Response',
      icon: Clock,
      completed: false,
      timestamp: invitation.created_at,
      details: `Invitation pending since ${formatDateTime(invitation.created_at)}`,
    })
  }

  // 6. Appointment Booked
  const bookedAppointment = appointments?.find(
    (a) => a.status === 'booked' || a.status === 'requested',
  )
  if (bookedAppointment) {
    events.push({
      id: 'appointment_booked',
      stage: 'Appointment Booked',
      icon: Calendar,
      completed: true,
      timestamp: bookedAppointment.created_at,
      details: formatSlot(
        bookedAppointment.date,
        bookedAppointment.start_time,
        bookedAppointment.end_time,
      ),
    })
  } else if (lawyer && c.assigned_lawyer_id) {
    events.push({
      id: 'appointment_pending',
      stage: 'Appointment Booking',
      icon: Calendar,
      completed: false,
      timestamp: c.accepted_at || c.updated_at,
      details: 'Awaiting appointment booking',
    })
  }

  // 7. Consultation Completed
  const completedAppointment = appointments?.find((a) => a.status === 'completed')
  if (completedAppointment) {
    events.push({
      id: 'consultation_completed',
      stage: 'Consultation Completed',
      icon: CheckCircle,
      completed: true,
      timestamp: completedAppointment.updated_at,
      details: `Held on ${formatSlot(completedAppointment.date, completedAppointment.start_time, completedAppointment.end_time)}`,
    })
  }

  // 8. Progress Notes
  if (progressNotes && progressNotes.length > 0) {
    progressNotes.forEach((note, idx) => {
      events.push({
        id: `progress_${idx}`,
        stage: 'Progress Update',
        icon: FileText,
        completed: true,
        timestamp: note.created_at,
        details: note.content,
        isNote: true,
      })
    })
  } else if (lawyer && c.assigned_lawyer_id) {
    events.push({
      id: 'case_progress',
      stage: 'Case Progress',
      icon: FileText,
      completed: false,
      timestamp: c.updated_at,
      details: 'Awaiting progress updates from lawyer',
    })
  }

  // 9. Case Closed
  if (c.status === 'closed' || c.status === 'resolved') {
    events.push({
      id: 'case_closed',
      stage: 'Case Closed',
      icon: CheckCircle2,
      completed: true,
      timestamp: c.updated_at,
      details: `Status: ${c.status}`,
    })
  }

  return (
    <div className="case-timeline">
      <div className="timeline-container">
        {events.map((event, idx) => {
          const Icon = event.icon
          const isLast = idx === events.length - 1

          return (
            <div
              key={event.id}
              className={`timeline-item ${event.completed ? 'timeline-item--completed' : 'timeline-item--pending'} ${event.isNote ? 'timeline-item--note' : ''}`}
            >
              <div className="timeline-item__marker">
                <Icon size={18} aria-hidden />
              </div>

              <div className="timeline-item__content">
                <div className="timeline-item__stage">{event.stage}</div>
                {event.details && (
                  <div className="timeline-item__details">{event.details}</div>
                )}
                {event.timestamp && (
                  <div className="timeline-item__timestamp">
                    {formatDateTime(event.timestamp)}
                  </div>
                )}
              </div>

              {!isLast && <div className="timeline-item__line" />}
            </div>
          )
        })}
      </div>
    </div>
  )
}
