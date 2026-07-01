// HealthChecker/frontend/src/components/RemarksBlock.jsx
import { parseRemarks } from '../utils/helpers'

const SECTION_ORDER = ['FINDINGS', 'RISK ASSESSMENT', 'IMMEDIATE ACTIONS', 'LIFESTYLE MODIFICATIONS', 'RECOMMENDATION']

export default function RemarksBlock({ aiStatus, remarks }) {

  if (aiStatus === 'processing') {
    return (
      <div className="ai-loading">
        <div className="ai-loading-pulse">
          <span /><span /><span />
        </div>
        <p className="ai-loading-text">Analysing blood test results…</p>
        <p className="ai-loading-sub">This usually takes a few seconds.</p>
      </div>
    )
  }

  if (!remarks) {
    return <p style={{ color: 'var(--text-muted)' }}>No remarks available.</p>
  }

  const sections = parseRemarks(remarks)

  return (
    <div>
      {sections ? (
        <div className="remarks-sections">
          {SECTION_ORDER.filter(h => sections[h]).map(h => (
            <div className="remarks-section" key={h}>
              <h4>{h}</h4>
              <p>{sections[h]}</p>
            </div>
          ))}
        </div>
      ) : (
        <p style={{ whiteSpace: 'pre-wrap' }}>{remarks}</p>
      )}
    </div>
  )
}
