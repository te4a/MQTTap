const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export function getToken() {
  return localStorage.getItem('token')
}

export function setToken(token) {
  localStorage.setItem('token', token)
}

export function clearToken() {
  localStorage.removeItem('token')
}

async function request(path, options = {}) {
  const headers = options.headers || {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (!headers['Content-Type'] && options.body) headers['Content-Type'] = 'application/json'

  const resp = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers
  })
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(text || resp.statusText)
  }
  if (resp.status === 204) return null
  return resp.json()
}

function toQuery(params) {
  const query = new URLSearchParams()
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    query.set(key, value)
  })
  const qs = query.toString()
  return qs ? `?${qs}` : ''
}

export const api = {
  login: (email, password) => request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password })
  }),
  me: () => request('/auth/me'),
  getSettings: () => request('/settings'),
  updateSettings: (payload) => request('/settings', {
    method: 'PUT',
    body: JSON.stringify(payload)
  }),
  topics: () => request('/topics'),
  history: (params) => request(`/history${toQuery(params)}`)
}
