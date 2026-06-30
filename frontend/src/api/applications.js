// Task 1 Updated/frontend/src/api/applications.js
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

async function handle(res) {
  if (!res.ok) {
    let detail = 'Something went wrong. Please try again.'
    try {
      const body = await res.json()
      if (body.detail) {
        detail = Array.isArray(body.detail)
          ? body.detail.map(d => d.msg).join(' ')
          : body.detail
      }
    } catch (_) {}
    throw new Error(detail)
  }
  if (res.status === 204) return null
  return res.json()
}

export async function listApplications(params = {}) {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') qs.set(k, v)
  })
  const res = await fetch(`${API_URL}/applications/?${qs.toString()}`)
  return handle(res)
}

export async function getApplication(id) {
  const res = await fetch(`${API_URL}/applications/${id}`)
  return handle(res)
}

export async function createApplication(payload) {
  const res = await fetch(`${API_URL}/applications/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return handle(res)
}

export async function updateApplication(id, payload) {
  const res = await fetch(`${API_URL}/applications/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return handle(res)
}

export async function deleteApplication(id) {
  const res = await fetch(`${API_URL}/applications/${id}`, { method: 'DELETE' })
  return handle(res)
}
