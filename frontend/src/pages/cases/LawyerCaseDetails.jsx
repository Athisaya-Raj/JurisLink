import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { FileText, Sparkles, AlertCircle, Calendar, ShieldAlert, ArrowLeft, Plus } from 'lucide-react'
import client, { apiErrorMessage } from '../../api/client.js'
import { addProgressNote, getProgressNotes } from '../../api/progressService.js'
import StatusBadge from '../../components/StatusBadge.jsx'
import CaseTimeline from '../../components/CaseTimeline.jsx'
import Spinner from '../../components/Spinner.jsx'
import { useToast } from '../../context/ToastContext.jsx'
import { formatDateTime, formatConfidence, formatSlot } from '../../utils/format.js'

const STATUS_OPTIONS = [
  { value: 'assigned', label: 'Assigned' },
  { value: 'in_review', label: 'In review' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'closed', label: 'Closed' },
]

export default function LawyerCaseDetails() {
  const { id } = useParams()
  const { addToast } = useToast()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const [saving, setSaving] = useState(false)
  const [progressNotes, setProgressNotes] = useState([])
  const [notesLoading, setNotesLoading] = useState(false)
  const [showNoteForm, setShowNoteForm] = useState(false)
  const [noteContent, setNoteContent] = useState('')
  const [savingNote, setSavingNote] = useState(false)

  const load = async () => {
    try {
      const res = await client.get(`/cases/${id}`)
      setData(res.data)
      setStatus(res.data.case.status)
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not load this case.'))
    } finally {
      setLoading(false)
    }
  }

  const loadProgressNotes = async () => {
    setNotesLoading(true)
    try {
      const notes = await getProgressNotes(id)
      setProgressNotes(notes)
    } catch (err) {
      // Notes may not exist yet
      console.error('Could not load progress notes:', err)
    } finally {
      setNotesLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  useEffect(() => {
    if (data) {
      loadProgressNotes()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.case?.case_id])

  const updateStatus = async () => {
    setSaving(true)
    try {
      const { data: updated } = await client.patch(`/cases/${id}/status`, { status })
      setData((prev) => ({ ...prev, case: updated.case }))
      addToast('Case status updated.', 'success')
    } catch (err) {
      addToast(apiErrorMessage(err), 'error')
    } finally {
      setSaving(false)
    }
  }

  const saveProgressNote = async () => {
    if (!noteContent.trim()) {
      addToast('Please enter a progress note.', 'error')
      return
    }

    setSavingNote(true)
    try {
      const newNote = await addProgressNote(id, noteContent.trim(), 'progress')
      setProgressNotes([newNote, ...progressNotes])
      setNoteContent('')
      setShowNoteForm(false)
      addToast('Progress note added.', 'success')
      
      // Reload case data to update timeline
      await load()
    } catch (err) {
      addToast(apiErrorMessage(err), 'error')
    } finally {
      setSavingNote(false)
    }
  }

  if (loading) return <Spinner label="Loading case…" />

  if (error) {
    return (
      <>
        <Link className="btn btn--ghost btn--sm mb-16" to="/lawyer">
          <ArrowLeft size={15} aria-hidden /> Back
        </Link>
        <div className="alert alert--error" role="alert">
          <AlertCircle size={18} aria-hidden /> {error}
        </div>
      </>
    )
  }

  const { case: c, prediction, appointments } = data

  return (
    <>
      <div className="page-head">
        <div>
          <Link className="btn btn--ghost btn--sm" to="/lawyer" style={{ marginBottom: 8 }}>
            <ArrowLeft size={15} aria-hidden /> Back to dashboard
          </Link>
          <h1>{c.title}</h1>
          <p className="page-head__sub">
            {c.case_id} · submitted {formatDateTime(c.created_at)}
            {c.accepted_at ? ` · accepted ${formatDateTime(c.accepted_at)}` : ''}
          </p>
        </div>
        <StatusBadge status={c.status} />
      </div>

      <div className="grid grid--2">
        <div>
          <div className="card">
            <div className="card__title">
              <FileText size={18} aria-hidden />
              <h3>Client's issue</h3>
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
          </div>

          <div className="card">
            <div className="card__title">
              <Sparkles size={18} aria-hidden />
              <h3>Classification</h3>
            </div>
            <div className="detail-row">
              <span className="detail-row__label">Predicted category</span>
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
              <FileText size={18} aria-hidden />
              <h3>Case status</h3>
            </div>
            {c.accepted_at && (
              <div className="detail-row">
                <span className="detail-row__label">Accepted</span>
                <span className="detail-row__value">{formatDateTime(c.accepted_at)}</span>
              </div>
            )}
            <div className="form-field">
              <label className="form-label" htmlFor="case-status">
                Update status
              </label>
              <div className="flex gap-8">
                <select
                  id="case-status"
                  className="select"
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                >
                  {STATUS_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
                <button
                  className="btn btn--primary"
                  onClick={updateStatus}
                  disabled={saving || status === c.status}
                >
                  {saving ? 'Saving…' : 'Update'}
                </button>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card__title">
              <Calendar size={18} aria-hidden />
              <h3>Appointments</h3>
            </div>
            {appointments.length === 0 ? (
              <p className="muted">No appointments booked for this case yet.</p>
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
          <CaseTimeline caseData={{ ...data, progressNotes }} isLawyerView={true} />
        </div>
      </section>

      <section className="mt-16">
        <div className="card">
          <div className="card__title">
            <FileText size={18} aria-hidden />
            <h3>Progress Notes</h3>
          </div>

          {!showNoteForm ? (
            <button
              className="btn btn--primary mb-16"
              onClick={() => setShowNoteForm(true)}
            >
              <Plus size={16} aria-hidden /> Add progress note
            </button>
          ) : (
            <div className="form-field mb-16">
              <label className="form-label" htmlFor="progress-note">
                Progress note
              </label>
              <textarea
                id="progress-note"
                className="textarea"
                style={{ minHeight: 100 }}
                value={noteContent}
                onChange={(e) => setNoteContent(e.target.value)}
                placeholder="e.g. Initial consultation completed. Client confirmed details of dispute. Will prepare legal analysis for next meeting."
                maxLength={2000}
              />
              <div className="flex gap-8 mt-16">
                <button
                  className="btn btn--primary"
                  onClick={saveProgressNote}
                  disabled={savingNote || !noteContent.trim()}
                >
                  {savingNote ? 'Saving…' : 'Save note'}
                </button>
                <button
                  className="btn btn--secondary"
                  onClick={() => {
                    setShowNoteForm(false)
                    setNoteContent('')
                  }}
                  disabled={savingNote}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {notesLoading ? (
            <p className="muted">Loading progress notes…</p>
          ) : progressNotes.length === 0 ? (
            <p className="muted">No progress notes yet. Add one to track case progress.</p>
          ) : (
            <div className="progress-notes-list">
              {progressNotes.map((note) => (
                <div key={note.progress_note_id} className="progress-note-item">
                  <div className="progress-note-item__header">
                    <div className="progress-note-item__time">{formatDateTime(note.created_at)}</div>
                    <div className="progress-note-item__type">{note.note_type}</div>
                  </div>
                  <div className="progress-note-item__content">{note.content}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </>
  )
}
