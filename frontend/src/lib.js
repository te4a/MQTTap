import { get } from 'svelte/store'
import { lang, t } from './i18n.js'

const API_BASE = import.meta.env.VITE_API_BASE || `${window.location.origin}/api`

export function getToken() {
  return localStorage.getItem('token')
}

export function setToken(token) {
  localStorage.setItem('token', token)
}

export function clearToken() {
  localStorage.removeItem('token')
}

function handleUnauthorized() {
  clearToken()
  window.dispatchEvent(new Event('authChange'))
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
  if (resp.status === 401) {
    handleUnauthorized()
  }
  if (!resp.ok) {
    const rawText = await resp.text()
    let detail = rawText
    try {
      const data = JSON.parse(rawText)
      detail = data?.detail ? String(data.detail) : rawText
    } catch {
      detail = rawText
    }
    const message = translateError(detail || resp.statusText)
    throw new Error(message || resp.statusText)
  }
  if (resp.status === 204) return null
  return resp.json()
}

const ERROR_MAP = {
  'Username already exists': 'errors.usernameExists',
  'Email already exists': 'errors.emailExists',
  'Invalid invite': 'errors.invalidInvite',
  'Invalid invite role': 'errors.invalidInvite',
  'Invite code already exists': 'errors.inviteCodeExists',
  'Invalid credentials': 'errors.invalidCredentials',
  'Account pending approval': 'errors.accountPending',
  'Invalid token': 'errors.invalidToken',
  'Admin only': 'errors.adminOnly',
  'invalid role': 'errors.invalidRole',
  'User not found': 'errors.userNotFound',
  'Invalid current password': 'errors.invalidCurrentPassword',
  'Chart not found': 'errors.chartNotFound'
}

function translateError(detail) {
  if (!detail) return ''
  const key = ERROR_MAP[detail]
  if (!key) return detail
  return t(key, get(lang))
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
  login: (username, password) => request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password })
  }),
  register: (payload) => request('/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  me: () => request('/auth/me'),
  updateProfile: (payload) => request('/auth/profile', {
    method: 'PUT',
    body: JSON.stringify(payload)
  }),
  changePassword: (oldPassword, newPassword) => request('/auth/password', {
    method: 'POST',
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
  }),
  getSettings: () => request('/settings'),
  getPublicSettings: () => request('/settings/public'),
  updateSettings: (payload) => request('/settings', {
    method: 'PUT',
    body: JSON.stringify(payload)
  }),
  topics: () => request('/topics'),
  history: (params) => request(`/history${toQuery(params)}`),
  listCharts: () => request('/charts'),
  createChart: (payload) => request('/charts', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  updateChart: (id, payload) => request(`/charts/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  }),
  deleteChart: (id) => request(`/charts/${id}`, { method: 'DELETE' }),
  listUsers: () => request('/users'),
  createUser: (payload) => request('/users', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  updateUser: (id, payload) => request(`/users/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  }),
  deleteUser: (id) => request(`/users/${id}`, { method: 'DELETE' }),
  listInvites: () => request('/invites'),
  createInvite: (payload) => request('/invites', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  updateInvite: (id, payload) => request(`/invites/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  }),
  deleteInvite: (id) => request(`/invites/${id}`, { method: 'DELETE' })
}
