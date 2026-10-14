import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import {
  FileText,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  XCircle,
  ArrowLeft,
  ShieldAlert,
  Clock,
} from 'lucide-react'
import client, { apiErrorMessage } from '../../api/client.js'
import StatusBadge from '../../components/StatusBadge.jsx'
import Spinner from '../../components/Spinner.jsx'
import { useToast } from '../../context/ToastContext.jsx'
import { formatDateTime, formatConfidence } from '../../utils/format.js'

export default function InvitationDetails() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { addToast } = useToast()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [declineOpen, setDeclineOpen] = useState(false)
  const [reason, setReason] = useState('')

  const load = () =>
    client
      .get(`/invitations/${id}`)
      .then((res) => setData(res.data))
      .catch((err) => setError(apiErrorMessage(err, 'Could not load this invitation.')))
      .finally(() => setLoading(false))

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  const accept = async () => {
    setBusy(true)
    try {
      await client.post(`/invitations/${id}/accept`)
      addToast('Case accepted.', 'success')
      load()
    } catch (err) {
      addToast(apiErrorMessage(err), 'error')
    } finally {
      setBusy(false)
    }
  }

  const decline = async () => {
    setBusy(true)
    try {
      const { data: result } = await client.post(`/invitations/${id}/decline`, {
        reason: reason.trim() || null,
      })
      addToast(
        result.reassigned ? 'Declined — case re-offered to another lawyer.' : 'Case declined.',
        'success',
      )
      setDeclineOpen(false)
      setReason('')
      load()
    } catch (err) {
      addToast(apiErrorMessage(err), 'error')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <Spinner label="Loading invitation…" />

  if (error) {
    return (
      <>
        <Link className="btn btn--ghost btn--sm mb-16" to="/lawyer/invitations">
          <ArrowLeft size={15} aria-hidden /> Back
        </Link>
        <div className="alert alert--error" role="alert">
          <AlertCircle size={18} aria-hidden /> {error}
        </div>
      </>
    )
  }

  const { invitation, case: c, lawyer } = data
  const isPending = invitation.status === 'pending'

  return (
    <>
      <div className="page-head">
        <div>
          <Link className="btn btn--ghost btn--sm" to="/lawyer/invitations" style={{ marginBottom: 8 }}>
            <ArrowLeft size={15} aria-hidden /> Back to invitations
          </Link>
          <h1>{c.title}</h1>
          <p className="page-head__sub">
            {c.case_id} · received {formatDateTime(invitation.created_at)}
          </p>
        </div>
        <StatusBadge status={invitation.status} />
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
                <strong>{c.predicted_category_name}</strong>{' '}
                <span className="muted">({c.predicted_category_id})</span>
              </span>
            </div>
            <div className="detail-row">
              <span className="detail-row__label">Confidence</span>
              <span className="detail-row__value">
                {formatConfidence(c.prediction_confidence)}
              </span>
            </div>
            <div className="alert alert--disclaimer mt-16">
              <ShieldAlert size={16} aria-hidden />
              <span>{c.prediction_explanation || 'Automated classification; not legal advice.'}</span>
            </div>
          </div>
        </div>

        <div>
          <div className="card">
            <div className="card__title">
              <Clock size={18} aria-hidden />
              <h3>Invitation</h3>
            </div>
            <div className="detail-row">
              <span className="detail-row__label">Lawyer</span>
              <span className="detail-row__value">
                <strong>{lawyer?.name}</strong>
              </span>
            </div>
            {lawyer?.specialization_names && (
              <div className="detail-row">
                <span className="detail-row__label">Specialization</span>
                <span className="detail-row__value">{lawyer.specialization_names.join(', ')}</span>
              </div>
            )}
            <div className="detail-row">
              <span className="detail-row__label">Status</span>
              <span className="detail-row__value">
                <StatusBadge status={invitation.status} />
              </span>
            </div>
            {invitation.responded_at && (
              <div className="detail-row">
                <span className="detail-row__label">Responded</span>
                <span className="detail-row__value">{formatDateTime(invitation.responded_at)}</span>
              </div>
            )}
            {invitation.decline_reason && (
              <div className="detail-row">
                <span className="detail-row__label">Decline reason</span>
                <span className="detail-row__value">{invitation.decline_reason}</span>
              </div>
            )}
          </div>

          {isPending ? (
            <div className="card">
              <div className="card__title">
                <CheckCircle2 size={18} aria-hidden />
                <h3>Respond to this invitation</h3>
              </div>
              <div className="flex gap-12">
                <button className="btn btn--primary" onClick={accept} disabled={busy}>
                  {busy ? <span className="spinner" aria-hidden /> : <CheckCircle2 size={16} aria-hidden />}
                  Accept case
                </button>
                <button className="btn btn--outline-danger" onClick={() => setDeclineOpen(true)} disabled={busy}>
                  <XCircle size={16} aria-hidden /> Decline case
                </button>
              </div>

              {declineOpen && (
                <div className="mt-16">
                  <label className="form-label" htmlFor="decline-reason">
                    Reason <span className="form-label__hint">(optional)</span>
                  </label>
                  <textarea
                    id="decline-reason"
                    className="textarea"
                    style={{ minHeight: 70 }}
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="e.g. Conflict of interest, outside my area of practice…"
                    maxLength={1000}
                  />
                  <div className="flex gap-8 mt-16">
                    <button className="btn btn--danger" onClick={decline} disabled={busy}>
                      Confirm decline
                    </button>
                    <button className="btn btn--secondary" onClick={() => setDeclineOpen(false)}>
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : invitation.status === 'accepted' ? (
            <div className="alert alert--success">
              <CheckCircle2 size={18} aria-hidden />
              <span>
                This case was accepted. View it under{' '}
                <Link to={`/lawyer/cases/${c.case_id}`}>active cases</Link>.
              </span>
            </div>
          ) : (
            <div className="alert alert--warning">
              <AlertCircle size={18} aria-hidden />
              <span>This invitation was {invitation.status}.</span>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
