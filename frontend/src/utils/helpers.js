// Task 1 Updated/frontend/src/utils/helpers.js
export function formatDate(d) {
  if (!d) return '—'
  const date = new Date(d)
  if (isNaN(date)) return '—'
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

export function formatDateTime(d) {
  if (!d) return '—'
  const date = new Date(d)
  if (isNaN(date)) return '—'
  return date.toLocaleString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export function calcAge(dobString) {
  if (!dobString) return null
  const dob = new Date(dobString)
  if (isNaN(dob)) return null
  const today = new Date()
  let age = today.getFullYear() - dob.getFullYear()
  const m = today.getMonth() - dob.getMonth()
  if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) age--
  return age
}

export const RISK_LABELS = {
  normal: 'Normal',
  slightly_abnormal: 'Slightly Abnormal',
  high: 'High Risk',
}

export const RISK_BADGE_CLASS = {
  normal: 'badge-normal',
  slightly_abnormal: 'badge-slight',
  high: 'badge-high',
}

// Parses the AI's five-section plain-text report into a structured object
// for nicer rendering. Falls back to raw text if sections aren't found.
export function parseRemarks(raw) {
  if (!raw) return null
  const headers = ['FINDINGS', 'RISK ASSESSMENT', 'IMMEDIATE ACTIONS', 'LIFESTYLE MODIFICATIONS', 'RECOMMENDATION']
  const sections = {}
  let remaining = raw
  for (let i = 0; i < headers.length; i++) {
    const h = headers[i]
    const idx = remaining.indexOf(`${h}:`)
    if (idx === -1) continue
    const start = idx + h.length + 1
    let end = remaining.length
    for (let j = i + 1; j < headers.length; j++) {
      const nextIdx = remaining.indexOf(`${headers[j]}:`, start)
      if (nextIdx !== -1) { end = nextIdx; break }
    }
    sections[h] = remaining.slice(start, end).trim()
  }
  if (Object.keys(sections).length === 0) return null
  return sections
}

// ── Fuzzy search (typo-tolerant, ranked, with highlight spans) ─────────────
//
// Used for the "as you type" search bar. Matching is NOT limited to exact
// substrings — a candidate string scores > 0 as long as every character of
// the query appears in it IN ORDER (a "subsequence" match, the same idea
// fuzzy finders like Sublime/VS Code's Quick Open use), with bonus weight
// for longer contiguous runs and for matches near the start of the string.
// Results are then sorted so the closest / most-similar matches float to
// the top, even when they aren't a 100% exact match.

function _normalize(s) {
  return (s || '').toLowerCase()
}

// Returns { score, ranges } where score is 0 (no match) to ~1+ (closer to
// an exact/contiguous match), and ranges is the list of [start, end)
// character spans in `text` that matched the query, for highlighting.
export function fuzzyMatch(query, text) {
  const q = _normalize(query)
  const t = _normalize(text)
  if (!q) return { score: 0, ranges: [] }
  if (!t) return { score: 0, ranges: [] }

  // Fast path: exact substring match scores highest, weighted by how early
  // it appears and what fraction of the string it covers.
  const exactIdx = t.indexOf(q)
  if (exactIdx !== -1) {
    const coverage = q.length / t.length
    const positionBonus = 1 - exactIdx / (t.length + 1)
    const score = 1 + coverage + positionBonus * 0.5
    return { score, ranges: [[exactIdx, exactIdx + q.length]] }
  }

  // Fuzzy subsequence match: walk both strings, greedily matching query
  // characters in order, rewarding contiguous runs.
  let qi = 0
  let ranges = []
  let runStart = -1
  let runLen = 0
  let matchedChars = 0
  let contiguityBonus = 0

  for (let ti = 0; ti < t.length && qi < q.length; ti++) {
    if (t[ti] === q[qi]) {
      if (runStart === -1) runStart = ti
      runLen++
      matchedChars++
      qi++
    } else if (runStart !== -1) {
      ranges.push([runStart, runStart + runLen])
      contiguityBonus += runLen > 1 ? runLen - 1 : 0
      runStart = -1
      runLen = 0
    }
  }
  if (runStart !== -1) {
    ranges.push([runStart, runStart + runLen])
    contiguityBonus += runLen > 1 ? runLen - 1 : 0
  }

  if (matchedChars < q.length) return { score: 0, ranges: [] } // not all query chars found in order

  const completeness = matchedChars / q.length
  const density = matchedChars / t.length
  const score = completeness * 0.6 + density * 0.2 + contiguityBonus * 0.05

  return { score, ranges }
}

// Highlights the matched ranges from fuzzyMatch() inside `text`, returning
// an array of React-renderable pieces ({ text, match }). The caller decides
// how to render `match: true` pieces (e.g. wrap in <mark>).
export function highlightRanges(text, ranges) {
  if (!ranges || ranges.length === 0) return [{ text, match: false }]
  const pieces = []
  let cursor = 0
  for (const [start, end] of ranges) {
    if (start > cursor) pieces.push({ text: text.slice(cursor, start), match: false })
    pieces.push({ text: text.slice(start, end), match: true })
    cursor = end
  }
  if (cursor < text.length) pieces.push({ text: text.slice(cursor), match: false })
  return pieces
}
