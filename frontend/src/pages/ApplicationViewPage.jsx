// Task 1 Updated/frontend/src/pages/ApplicationViewPage.jsx
import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Navbar from '../components/Navbar.jsx'
import ConfirmDialog from '../components/ConfirmDialog.jsx'
import RemarksBlock from '../components/RemarksBlock.jsx'
import { getApplication, deleteApplication } from '../api/applications.js'
import { formatDate, formatDateTime, RISK_LABELS, RISK_BADGE_CLASS } from '../utils/helpers.js'

export default function ApplicationViewPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [app, setApp] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [showDelete, setShowDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const pollRef = useRef(null)

  const load = useCallback((silent = false) => {
    if (!silent) setLoading(true)
    getApplication(id)
      .then(setApp)
      .catch(err => setError(err.message || 'Failed to load application.'))
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => { load() }, [load])

  // Poll for the AI result while it's still processing, so the remarks
  // populate automatically without the user needing to refresh.
  useEffect(() => {
    if (!app || app.ai_status !== 'processing') {
      if (pollRef.current) clearInterval(pollRef.current)
      return
    }
    pollRef.current = setInterval(() => load(true), 3000)
    return () => clearInterval(pollRef.current)
  }, [app, load])

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await deleteApplication(id)
      navigate('/')
    } catch (err) {
      setError(err.message || 'Failed to delete application.')
      setDeleting(false)
    }
  }

  if (loading) {
    return (
      <>
        <Navbar />
        <div style={{ textAlign: 'center', padding: '4rem' }}><div className="spinner spinner-lg" /></div>
      </>
    )
  }

  if (error && !app) {
    return (
      <>
        <Navbar />
        <div className="page-wrapper container">
          <div className="alert alert-error">{error}</div>
        </div>
      </>
    )
  }

  return (
    <>
      <Navbar />
      {showDelete && (
        <ConfirmDialog
          title="Delete this application?"
          message={`This will permanently remove application ${app.app_ref} for ${app.full_name}. This cannot be undone.`}
          confirmLabel="Delete"
          danger
          loading={deleting}
          onConfirm={handleDelete}
          onClose={() => setShowDelete(false)}
        />
      )}

      <div className="page-wrapper container" style={{ maxWidth: 760 }}>
        <button className="btn btn-ghost btn-sm" style={{ marginBottom: '1rem' }} onClick={() => navigate('/')}>← Back to applications</button>

        <div className="section-header">
          <div>
            <h2 className="section-title" style={{ fontFamily: 'monospace' }}>{app.app_ref}</h2>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Submitted {formatDateTime(app.created_at)}</p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className="btn btn-secondary" onClick={() => navigate(`/edit/${app.id}`)}>Edit</button>
            <button className="btn btn-danger" onClick={() => setShowDelete(true)}>Delete</button>
          </div>
        </div>

        {error && <div className="alert alert-error mb-2">{error}</div>}

        <div className="card mb-2">
          <h4 className="card-subtitle">Patient Details</h4>
          <div className="detail-grid">
            <div><span className="detail-label">Full Name</span><span>{app.full_name}</span></div>
            <div><span className="detail-label">Date of Birth</span><span>{formatDate(app.date_of_birth)}</span></div>
            <div><span className="detail-label">Email</span><span>{app.email}</span></div>
            <div><span className="detail-label">Age at Submission</span><span>{app.age_at_submission} years</span></div>
          </div>
        </div>

        <div className="card mb-2">
          <h4 className="card-subtitle">Blood Test Values</h4>
          <div className="detail-grid">
            <div><span className="detail-label">Glucose</span><span>{app.glucose} mg/dL</span></div>
            <div><span className="detail-label">Haemoglobin</span><span>{app.haemoglobin} g/dL</span></div>
            <div><span className="detail-label">Cholesterol</span><span>{app.cholesterol} mg/dL</span></div>
            <div>
              <span className="detail-label">Risk Tag</span>
              {app.risk_tag
                ? <span className={`badge ${RISK_BADGE_CLASS[app.risk_tag]}`}>{RISK_LABELS[app.risk_tag]}</span>
                : <span style={{ color: 'var(--text-muted)' }}>Pending</span>}
            </div>
          </div>
        </div>

        <div className="card">
          <h4 className="card-subtitle">AI Remarks</h4>
          <div className="alert alert-warning mb-2" style={{ fontSize: '0.8rem' }}>
            ⚠ AI-generated — not a substitute for professional medical advice.
          </div>
          <RemarksBlock patientName={app.full_name} aiStatus={app.ai_status} remarks={app.remarks} isFallback={app.remarks_is_fallback} />
        </div>
      </div>
    </>
  )
}
