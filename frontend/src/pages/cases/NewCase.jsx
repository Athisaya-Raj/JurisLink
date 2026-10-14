import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  FileText,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  ArrowLeft,
  ShieldAlert,
} from 'lucide-react'
import client, { apiErrorMessage } from '../../api/client.js'
import StatusBadge from '../../components/StatusBadge.jsx'
import { formatConfidence } from '../../utils/format.js'

function generateId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID()
  return `client-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export default function NewCase() {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [supportingInfo, setSupportingInfo] = useState('')
  const [preferredDate, setPreferredDate] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [submitError, setSubmitError] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const requestIdRef = useRef(generateId())

  const validate = () => {
    const errors = {}
    if (!title.trim()) errors.title = 'Please provide a case title.'
    if (!description.trim()) errors.description = 'Please describe your legal issue.'
    else if (description.trim().length < 10)
      errors.description = 'Please provide a longer description (at least 10 characters).'
    return errors
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitError('')
    const errors = validate()
    setFieldErrors(errors)
    if (Object.keys(errors).length) return

    setLoading(true)
    try {
      const payload = {
        title: title.trim(),
        description: description.trim(),
        client_request_id: requestIdRef.current,
      }
      if (supportingInfo.trim()) payload.supporting_info = supportingInfo.trim()
      if (preferredDate) payload.preferred_date = preferredDate

      const { data } = await client.post('/cases/demo/submit-and-classify', payload)
      setResult(data)
      // Reset the idempotency key for the next distinct case.
      requestIdRef.current = generateId()
    } catch (err) {
      setSubmitError(apiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const reset = () => {
    setResult(null)
    setTitle('')
    setDescription('')
    setSupportingInfo('')
    setPreferredDate('')
  }

  if (result) {
    const { case: c, prediction, lawyer, message, disposition } = result
    return (
      <>
        <div className="page-head">
          <div>
            <h1>Case submitted</h1>
            <p className="page-head__sub">
              {disposition === 'duplicate' ? 'A case for this request already exists.' : 'Your case was received and processed.'}
            </p>
          </div>
        </div>

        <div className="alert alert--success mb-16" role="status">
          <CheckCircle2 size={18} aria-hidden />
          <span>{message}</span>
        </div>

        <div className="card mb-16">
          <div className="card__title">
            <FileText size={18} aria-hidden />
            <h3>{c.title}</h3>
          </div>
          <div className="detail-row">
            <span className="detail-row__label">Case reference</span>
            <span className="detail-row__value">{c.case_id}</span>
          </div>
          <div className="detail-row">
            <span className="detail-row__label">Status</span>
            <span className="detail-row__value">
              <StatusBadge status={c.status} />
            </span>
          </div>
        </div>

        <div className="card mb-16">
          <div className="card__title">
            <Sparkles size={18} aria-hidden />
            <h3>Predicted category</h3>
          </div>
          <div className="detail-row">
            <span className="detail-row__label">Category</span>
            <span className="detail-row__value">
              <strong>{prediction.category_name}</strong> ({prediction.category_id})
            </span>
          </div>
          <div className="detail-row">
            <span className="detail-row__label">Model confidence</span>
            <span className="detail-row__value">{formatConfidence(prediction.confidence)}</span>
          </div>
          {prediction.review_recommended && (
            <div className="alert alert--warning mt-16">
              <ShieldAlert size={16} aria-hidden />
              <span>This classification is uncertain and may benefit from manual review.</span>
            </div>
          )}
          <div className="alert alert--disclaimer mt-16">
            <ShieldAlert size={16} aria-hidden />
            <span>{prediction.explanation}</span>
          </div>
        </div>

        {lawyer ? (
          <div className="card mb-16">
            <div className="card__title">
              <CheckCircle2 size={18} aria-hidden />
              <h3>Invitation sent</h3>
            </div>
            <div className="detail-row">
              <span className="detail-row__label">Lawyer</span>
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
            <div className="alert alert--info mt-16">
              <AlertCircle size={16} aria-hidden />
              <span>
                An invitation has been sent to {lawyer.name}. You'll be able to book an
                appointment once they accept the case.
              </span>
            </div>
            <div className="mt-16">
              <Link className="btn btn--secondary" to={`/cases/${c.case_id}`}>
                View case details
              </Link>
            </div>
          </div>
        ) : (
          <div className="alert alert--warning mb-16">
            <AlertCircle size={18} aria-hidden />
            <span>
              No eligible lawyer is currently available for this category. Your case is pending
              assignment and will be reviewed.
            </span>
          </div>
        )}

        <button className="btn btn--secondary" onClick={reset}>
          <ArrowLeft size={16} aria-hidden /> Submit another case
        </button>
      </>
    )
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Submit a new case</h1>
          <p className="page-head__sub">
            Describe your legal issue in your own words. We will classify it and match you with a
            lawyer.
          </p>
        </div>
      </div>

      {submitError && (
        <div className="alert alert--error mb-16" role="alert">
          <AlertCircle size={18} aria-hidden /> {submitError}
        </div>
      )}

      <form className="card" onSubmit={handleSubmit} noValidate>
        <div className="form-field">
          <label className="form-label" htmlFor="title">
            Case title
          </label>
          <input
            id="title"
            className="input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Rental deposit dispute"
            maxLength={300}
          />
          {fieldErrors.title && <div className="field-error">{fieldErrors.title}</div>}
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="description">
            Describe your legal issue
          </label>
          <textarea
            id="description"
            className="textarea"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g. My landlord refuses to return my rental deposit even though I vacated the apartment and completed the agreement."
            maxLength={10000}
          />
          {fieldErrors.description && (
            <div className="field-error">{fieldErrors.description}</div>
          )}
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="supporting">
            Supporting information <span className="form-label__hint">(optional)</span>
          </label>
          <textarea
            id="supporting"
            className="textarea"
            style={{ minHeight: 80 }}
            value={supportingInfo}
            onChange={(e) => setSupportingInfo(e.target.value)}
            placeholder="Any relevant context, dates, or documents you can describe."
            maxLength={5000}
          />
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="preferred">
            Preferred appointment date <span className="form-label__hint">(optional)</span>
          </label>
          <input
            id="preferred"
            type="date"
            className="input"
            value={preferredDate}
            onChange={(e) => setPreferredDate(e.target.value)}
          />
        </div>

        <button className="btn btn--primary" type="submit" disabled={loading}>
          {loading ? (
            <span className="spinner" aria-hidden />
          ) : (
            <Sparkles size={16} aria-hidden />
          )}
          {loading ? 'Classifying…' : 'Submit case'}
        </button>
      </form>
    </>
  )
}
