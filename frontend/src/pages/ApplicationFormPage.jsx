// HealthChecker/frontend/src/pages/ApplicationFormPage.jsx
import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Navbar from '../components/Navbar.jsx'
import { validateForm } from '../utils/validation.js'
import { calcAge } from '../utils/helpers.js'
import { getApplication, createApplication, updateApplication } from '../api/applications.js'

const EMPTY = { full_name: '', date_of_birth: '', email: '', glucose: '', haemoglobin: '', cholesterol: '' }
const today = new Date().toISOString().split('T')[0]

export default function ApplicationFormPage({ mode }) {
  const navigate = useNavigate()
  const { id } = useParams()
  const isEdit = mode === 'edit'

  const [form, setForm] = useState(EMPTY)
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(isEdit)
  const [submitting, setSubmitting] = useState(false)
  const [apiError, setApiError] = useState('')

  useEffect(() => {
    if (!isEdit) return
    getApplication(id)
      .then(app => {
        setForm({
          full_name: app.full_name,
          date_of_birth: app.date_of_birth,
          email: app.email,
          glucose: app.glucose,
          haemoglobin: app.haemoglobin,
          cholesterol: app.cholesterol,
        })
      })
      .catch(err => setApiError(err.message || 'Failed to load application.'))
      .finally(() => setLoading(false))
  }, [id, isEdit])

  const change = e => {
    const { name, value } = e.target
    setForm(f => ({ ...f, [name]: value }))
    setErrors(p => ({ ...p, [name]: null }))
  }

  const age = calcAge(form.date_of_birth)

  const handleSubmit = async e => {
    e.preventDefault()
    const errs = validateForm(form)
    setErrors(errs)
    if (Object.keys(errs).length) return

    const payload = {
      full_name: form.full_name.trim(),
      date_of_birth: form.date_of_birth,
      email: form.email.trim(),
      glucose: Number(form.glucose),
      haemoglobin: Number(form.haemoglobin),
      cholesterol: Number(form.cholesterol),
    }

    setSubmitting(true)
    setApiError('')
    try {
      const result = isEdit ? await updateApplication(id, payload) : await createApplication(payload)
      navigate(`/view/${result.id}`)
    } catch (err) {
      setApiError(err.message || 'Failed to save application.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <Navbar />
      <div className="page-wrapper container" style={{ maxWidth: 640 }}>
        <div className="section-header">
          <div>
            <h2 className="section-title">{isEdit ? 'Edit Application' : 'New Application'}</h2>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              {isEdit
                ? 'Updating these values will re-run the AI assessment and recalculate the risk tag.'
                : 'Enter patient details and blood test values to run an AI health assessment.'}
            </p>
          </div>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem' }}><div className="spinner spinner-lg" /></div>
        ) : (
          <div className="card">
            {apiError && <div className="alert alert-error mb-2">{apiError}</div>}
            <form onSubmit={handleSubmit} noValidate style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="form-group">
                <label htmlFor="full_name">Full Name <span style={{ color: 'var(--error)' }}>*</span></label>
                <input id="full_name" name="full_name" value={form.full_name} onChange={change}
                  placeholder="e.g. Jane Doe" className={errors.full_name ? 'error' : ''} />
                {errors.full_name && <span className="error-msg">⚠ {errors.full_name}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="date_of_birth">Date of Birth <span style={{ color: 'var(--error)' }}>*</span></label>
                <input id="date_of_birth" type="date" name="date_of_birth" max={today}
                  value={form.date_of_birth} onChange={change}
                  className={errors.date_of_birth ? 'error' : ''} />
                {errors.date_of_birth && <span className="error-msg">⚠ {errors.date_of_birth}</span>}
                {age !== null && !errors.date_of_birth && <span className="hint-msg">Age: {age} years</span>}
              </div>

              <div className="form-group">
                <label htmlFor="email">Email Address <span style={{ color: 'var(--error)' }}>*</span></label>
                <input id="email" type="email" name="email" value={form.email} onChange={change}
                  placeholder="name@example.com" className={errors.email ? 'error' : ''} />
                {errors.email && <span className="error-msg">⚠ {errors.email}</span>}
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="glucose">Glucose (mg/dL) <span style={{ color: 'var(--error)' }}>*</span></label>
                  <input id="glucose" type="number" step="0.01" name="glucose" value={form.glucose} onChange={change}
                    placeholder="e.g. 95" className={errors.glucose ? 'error' : ''} />
                  {errors.glucose && <span className="error-msg">⚠ {errors.glucose}</span>}
                </div>
                <div className="form-group">
                  <label htmlFor="haemoglobin">Haemoglobin (g/dL) <span style={{ color: 'var(--error)' }}>*</span></label>
                  <input id="haemoglobin" type="number" step="0.01" name="haemoglobin" value={form.haemoglobin} onChange={change}
                    placeholder="e.g. 14.2" className={errors.haemoglobin ? 'error' : ''} />
                  {errors.haemoglobin && <span className="error-msg">⚠ {errors.haemoglobin}</span>}
                </div>
                <div className="form-group">
                  <label htmlFor="cholesterol">Cholesterol (mg/dL) <span style={{ color: 'var(--error)' }}>*</span></label>
                  <input id="cholesterol" type="number" step="0.01" name="cholesterol" value={form.cholesterol} onChange={change}
                    placeholder="e.g. 180" className={errors.cholesterol ? 'error' : ''} />
                  {errors.cholesterol && <span className="error-msg">⚠ {errors.cholesterol}</span>}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => navigate(-1)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? <><span className="spinner" /> Checking…</> : (isEdit ? 'Save Changes' : 'Check')}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </>
  )
}
