// Task 1 Updated/frontend/src/pages/HomePage.jsx
import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar.jsx'
import ConfirmDialog from '../components/ConfirmDialog.jsx'
import { listApplications, deleteApplication } from '../api/applications.js'
import { formatDateTime, RISK_LABELS, RISK_BADGE_CLASS, fuzzyMatch, highlightRanges } from '../utils/helpers.js'

const PAGE_SIZE = 10
const CANDIDATE_LIMIT = 500 // broad fetch so live search isn't limited by pagination

const DATE_PRESETS = [
  { label: 'Any time', value: '' },
  { label: 'Today', value: 'today' },
  { label: 'Last 7 days', value: 'week' },
  { label: 'Last 30 days', value: 'month' },
  { label: 'Last 12 months', value: 'year' },
]

function presetToRange(preset) {
  if (!preset) return { date_from: '', date_to: '' }
  const today = new Date()
  const to = today.toISOString().split('T')[0]
  let from = new Date(today)
  if (preset === 'today') from = today
  if (preset === 'week') from.setDate(from.getDate() - 7)
  if (preset === 'month') from.setDate(from.getDate() - 30)
  if (preset === 'year') from.setFullYear(from.getFullYear() - 1)
  return { date_from: from.toISOString().split('T')[0], date_to: to }
}

function Highlighted({ text, ranges }) {
  if (!ranges || ranges.length === 0) return <>{text}</>
  return (
    <>
      {highlightRanges(text, ranges).map((p, i) =>
        p.match ? <mark key={i} className="search-hl">{p.text}</mark> : <span key={i}>{p.text}</span>
      )}
    </>
  )
}

export default function HomePage() {
  const navigate = useNavigate()
  const [candidates, setCandidates] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [searchQuery, setSearchQuery] = useState('')
  const [datePreset, setDatePreset] = useState('')
  const [remarksType, setRemarksType] = useState('')
  const [riskTag, setRiskTag] = useState('')
  const [sort, setSort] = useState('newest')
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  // Fetches a broad candidate set (respecting the dropdown filters + sort)
  // from the backend. Free-text search is then matched/ranked entirely on
  // the client below, so it isn't constrained to a single page and can
  // surface close-but-not-exact matches.
  const loadCandidates = useCallback(() => {
    setLoading(true)
    const { date_from, date_to } = presetToRange(datePreset)
    listApplications({
      page: 1, page_size: CANDIDATE_LIMIT, date_from, date_to,
      remarks_type: remarksType || undefined,
      risk_tag: riskTag || undefined,
      sort,
    })
      .then(res => { setCandidates(res.items); setError('') })
      .catch(err => setError(err.message || 'Failed to load applications.'))
      .finally(() => setLoading(false))
  }, [datePreset, remarksType, riskTag, sort])

  useEffect(() => { loadCandidates() }, [loadCandidates])
  useEffect(() => { setPage(1) }, [searchQuery, datePreset, remarksType, riskTag, sort])

  // Poll while any loaded item is still processing, so statuses update without a manual refresh.
  useEffect(() => {
    const anyProcessing = candidates.some(a => a.ai_status === 'processing')
    if (!anyProcessing) return
    const t = setInterval(loadCandidates, 4000)
    return () => clearInterval(t)
  }, [candidates, loadCandidates])

  // Live, typo-tolerant ranking: recomputed on every keystroke from the
  // already-fetched candidate set — no extra network round trip per
  // character, so it feels instant. Empty query = no filtering/highlighting,
  // original (server-chosen) order is kept.
  const ranked = useMemo(() => {
    if (!searchQuery.trim()) {
      return candidates.map(a => ({ app: a, nameRanges: [], emailRanges: [] }))
    }
    const scored = candidates.map(a => {
      const nameMatch = fuzzyMatch(searchQuery, a.full_name)
      const emailMatch = fuzzyMatch(searchQuery, a.email)
      const score = Math.max(nameMatch.score, emailMatch.score)
      return { app: a, score, nameRanges: nameMatch.ranges, emailRanges: emailMatch.ranges }
    })
    return scored
      .filter(r => r.score > 0)
      .sort((a, b) => b.score - a.score)
  }, [candidates, searchQuery])

  const total = ranked.length
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const pageItems = ranked.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await deleteApplication(deleteTarget.id)
      setDeleteTarget(null)
      loadCandidates()
    } catch (err) {
      setError(err.message || 'Failed to delete application.')
      setDeleting(false)
    }
  }

  return (
    <>
      <Navbar />
      {deleteTarget && (
        <ConfirmDialog
          title="Delete this application?"
          message={`This will permanently remove application ${deleteTarget.app_ref} for ${deleteTarget.full_name}. This cannot be undone.`}
          confirmLabel="Delete"
          danger
          loading={deleting}
          onConfirm={handleDelete}
          onClose={() => setDeleteTarget(null)}
        />
      )}

      <div className="page-wrapper container">
        <div className="alert alert-warning mb-2">
          ⚠ Remarks shown on each application are <strong>AI-generated</strong> and are provided for
          informational purposes only. They are <strong>not a substitute for professional medical advice,
          diagnosis, or treatment</strong>. Always consult a qualified physician about your blood test results.
        </div>

        <div className="section-header">
          <div>
            <h2 className="section-title">Applications</h2>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>{total} matching application{total === 1 ? '' : 's'}</p>
          </div>
          <button className="btn btn-primary" onClick={() => navigate('/new')}>+ New Application</button>
        </div>

        <div className="filters-bar">
          <div className="search-form">
            <input
              type="text"
              placeholder="Search by name or email — results filter as you type…"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setSearchQuery('')}>Clear</button>
            )}
          </div>

          <div className="filter-group">
            <label>Date</label>
            <select value={datePreset} onChange={e => setDatePreset(e.target.value)}>
              {DATE_PRESETS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </div>

          <div className="filter-group">
            <label>Remarks</label>
            <select value={remarksType} onChange={e => setRemarksType(e.target.value)}>
              <option value="">All</option>
              <option value="ai">AI-generated</option>
              <option value="manual">Auto / non-AI fallback</option>
            </select>
          </div>

          <div className="filter-group">
            <label>Risk Tag</label>
            <select value={riskTag} onChange={e => setRiskTag(e.target.value)}>
              <option value="">All</option>
              <option value="normal">Normal</option>
              <option value="slightly_abnormal">Slightly Abnormal</option>
              <option value="high">High Risk</option>
            </select>
          </div>

          <div className="filter-group">
            <label>Sort</label>
            <select value={sort} onChange={e => setSort(e.target.value)}>
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
              <option value="name">Name (A–Z)</option>
            </select>
          </div>
        </div>

        {error && <div className="alert alert-error mb-2">{error}</div>}

        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem' }}><div className="spinner spinner-lg" /></div>
        ) : pageItems.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🩺</div>
            <h3>No applications found</h3>
            <p>Try adjusting your search or filters, or create a new application.</p>
          </div>
        ) : (
          <>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>App Ref</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Age</th>
                    <th>Submitted</th>
                    <th>Status</th>
                    <th>Risk</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map(({ app: a, nameRanges, emailRanges }) => (
                    <tr key={a.id}>
                      <td style={{ fontFamily: 'monospace', fontWeight: 600, color: 'var(--green-700)' }}>{a.app_ref}</td>
                      <td><Highlighted text={a.full_name} ranges={nameRanges} /></td>
                      <td><Highlighted text={a.email} ranges={emailRanges} /></td>
                      <td>{a.age_at_submission}</td>
                      <td>{formatDateTime(a.created_at)}</td>
                      <td>
                        {a.ai_status === 'processing'
                          ? <span className="badge badge-processing">⏳ Processing</span>
                          : <span className="badge badge-done">✓ Done</span>}
                      </td>
                      <td>
                        {a.risk_tag
                          ? <span className={`badge ${RISK_BADGE_CLASS[a.risk_tag]}`}>{RISK_LABELS[a.risk_tag]}</span>
                          : <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>—</span>}
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem', whiteSpace: 'nowrap' }}>
                          <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/view/${a.id}`)}>View</button>
                          <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/edit/${a.id}`)}>Edit</button>
                          <button className="btn btn-danger btn-sm" onClick={() => setDeleteTarget(a)}>Delete</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="pagination">
              <button className="btn btn-secondary btn-sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
              <span>Page {page} of {totalPages}</span>
              <button className="btn btn-secondary btn-sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next →</button>
            </div>
          </>
        )}
      </div>
    </>
  )
}