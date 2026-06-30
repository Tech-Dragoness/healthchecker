// HealthChecker/frontend/src/components/ConfirmDialog.jsx
export default function ConfirmDialog({ title, message, confirmLabel = 'Confirm', danger = false, loading = false, onConfirm, onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" style={{ maxWidth: 420 }} onClick={e => e.stopPropagation()}>
        <h3 className="modal-title">{title}</h3>
        <p style={{ marginBottom: '1.5rem', color: 'var(--text-secondary)' }}>{message}</p>
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
          <button className="btn btn-secondary" onClick={onClose} disabled={loading}>Cancel</button>
          <button className={`btn ${danger ? 'btn-danger' : 'btn-primary'}`} onClick={onConfirm} disabled={loading}>
            {loading ? <><span className="spinner" /> Please wait…</> : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
