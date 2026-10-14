import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Inbox, AlertCircle, CheckCircle2, XCircle } from 'lucide-react'
import client, { apiErrorMessage } from '../../api/client.js'
import StatusBadge from '../../components/StatusBadge.jsx'
import EmptyState from '../../components/EmptyState.jsx'
import Spinner from '../../components/Spinner.jsx'
import ConfirmModal from '../../components/ConfirmModal.jsx'
import { useToast } from '../../context/ToastContext.jsx'
import { formatDateTime } from '../../utils/format.js'

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'pending', label: 'Pending' },
  { key: 'accepted', label: 'Accepted' },
  { key: 'declined', label: 'Declined' },
]

export default function Invitations() {
  const { addToast } = useToast()
  const [invitations, setInvitations] = useState([])
  const [counts, setCounts] = useState({})
  const [filter, setFilter] = useState('pending')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState(null)
  const [toDecline, setToDecline] = useState(null)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await client.get('/invitations')
      setInvitations(data.invitations || [])
      setCounts(data.counts || {})
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const filtered =
    filter === 'all' ? invitations : invitations.filter((i) => i.status === filter)

  const accept = async (invitationId) => {
    setBusyId(invitationId)
    setError('')
    try {
      await client.post(`/invitations/${invitationId}/accept`)
      addToast('Case accepted and added to your active cases.', 'success')
      load()
    } catch (err) {
      addToast(apiErrorMessage(err), 'error')
    } finally {
      setBusyId(null)
    }
  }

  const decline = async (invitationId) => {
    setBusyId(invitationId)
    setError('')
    try {
      const { data } = await client.post(`/invitations/${invitationId}/decline`, {})
      addToast(
        data.reassigned
          ? 'Case declined and re-offered to another lawyer.'
          : 'Case declined.',
        'success',
      )
      setToDecline(null)
      load()
    } catch (err) {
      addToast(apiErrorMessage(err), 'error')
    } finally {
      setBusyId(null)
    }
  }

  if (loading) return <Spinner label="Loading invitations…" />

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Case invitations</h1>
          <p className="page-head__sub">
            Review new cases matched to your specialization and accept or decline them.
          </p>
        </div>
      </div>

      {error && (
        <div className="alert alert--error mb-16" role="alert">
          <AlertCircle size={18} aria-hidden /> {error}
        </div>
      )}

      <div className="flex gap-8 mb-16">
        {FILTERS.map((f) => {
          const count = f.key === 'all' ? counts.total : counts[f.key]
          return (
            <button
              key={f.key}
              className={`btn btn--sm ${filter === f.key ? 'btn--navy' : 'btn--secondary'}`}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
              {count !== undefined && <span className="muted" style={{ marginLeft: 6 }}>{count}</span>}
            </button>
          )
        })}
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title="No invitations"
          description={
            filter === 'pending'
              ? 'No pending invitations right now.'
              : `No ${filter} invitations.`
          }
          icon={Inbox}
        />
      ) : (
        <div className="list">
          {filtered.map((i) => (
            <div key={i.invitation_id} className="list-item">
              <div className="list-item__main">
                <div className="list-item__title">{i.case_title}</div>
                <div className="list-item__meta">
                  <span>{i.case_id}</span>
                  <span>{i.predicted_category_name}</span>
                  <span>{formatDateTime(i.created_at)}</span>
                </div>
                {i.case_summary && <div className="muted small mt-16">{i.case_summary}</div>}
              </div>
              <StatusBadge status={i.status} />
              <div className="flex gap-8">
                <Link className="btn btn--secondary btn--sm" to={`/lawyer/invitations/${i.invitation_id}`}>
                  View details
                </Link>
                {i.status === 'pending' && (
                  <>
                    <button
                      className="btn btn--primary btn--sm"
                      onClick={() => accept(i.invitation_id)}
                      disabled={busyId === i.invitation_id}
                    >
                      {busyId === i.invitation_id ? (
                        <span className="spinner" aria-hidden />
                      ) : (
                        <CheckCircle2 size={15} aria-hidden />
                      )}
                      Accept
                    </button>
                    <button
                      className="btn btn--outline-danger btn--sm"
                      onClick={() => setToDecline(i)}
                      disabled={busyId === i.invitation_id}
                    >
                      <XCircle size={15} aria-hidden /> Decline
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <ConfirmModal
        open={!!toDecline}
        title="Decline this case?"
        message="The case will be re-offered to another eligible lawyer. You can also provide a reason on the details page."
        confirmLabel="Decline case"
        danger
        onConfirm={() => decline(toDecline.invitation_id)}
        onCancel={() => setToDecline(null)}
      />
    </>
  )
}
