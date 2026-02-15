<script>
  import { lang, t } from '../i18n.js'
  import { getToken } from '../lib.js'

  export let loggedIn = false
  export let isAdmin = false
  export let role = ''
  export let featureAccess = { history: true, charts: true }
  export let navigate

  const links = [
    { href: '/history', key: 'nav.history', feature: 'history' },
    { href: '/chart', key: 'nav.charts', feature: 'charts' },
    { href: '/profile', key: 'nav.profile' },
    { href: '/invites', key: 'nav.invites', adminOnly: true },
    { href: '/settings', key: 'nav.settings', adminOnly: true },
    { href: '/users', key: 'nav.users', adminOnly: true }
  ]

  function go(path, event) {
    event.preventDefault()
    if (navigate) navigate(path)
  }

  function canView(link) {
    const admin = isAdmin || role === 'admin' || tokenRole() === 'admin'
    let allowed = true
    if (link.adminOnly && !admin) allowed = false
    else if (link.feature === 'history') allowed = isFeatureEnabled('history')
    else if (link.feature === 'charts') allowed = isFeatureEnabled('charts')
    return allowed
  }

  function toBool(value, fallback = true) {
    if (value === undefined || value === null) return fallback
    if (typeof value === 'boolean') return value
    if (typeof value === 'number') return value !== 0
    if (typeof value === 'string') {
      const normalized = value.trim().toLowerCase()
      if (['false', '0', 'no', 'off'].includes(normalized)) return false
      if (['true', '1', 'yes', 'on'].includes(normalized)) return true
    }
    return fallback
  }

  function isFeatureEnabled(feature) {
    const access = normalizeFeatureAccess(featureAccess)
    if (feature === 'history') return access.history
    if (feature === 'charts') return access.charts
    return true
  }

  function normalizeFeatureAccess(source) {
    const raw = source
    let parsed = raw
    if (typeof raw === 'string') {
      try {
        parsed = JSON.parse(raw)
      } catch {
        parsed = null
      }
    }
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      const normalized = Object.fromEntries(
        Object.entries(parsed).map(([k, v]) => [String(k).trim().toLowerCase(), v])
      )
      return {
        history: toBool(
          normalized.history ?? normalized.can_access_history ?? normalized.history_enabled,
          true
        ),
        charts: toBool(
          normalized.charts ?? normalized.can_access_charts ?? normalized.charts_enabled,
          true
        )
      }
    }
    return { history: true, charts: true }
  }

  function tokenRole() {
    try {
      const token = getToken()
      if (!token) return ''
      const payload = token.split('.')[1]
      if (!payload) return ''
      const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
      const json = JSON.parse(atob(normalized))
      return typeof json?.role === 'string' ? json.role : ''
    } catch {
      return ''
    }
  }
</script>

<aside class="sidebar">
  <div class="brand">
    <img class="brand-icon" src="/app-icon.png" alt="MQTTap" />
    MQTTap
  </div>
  <nav>
    {#each links as link}
      {#if canView(link)}
        <a class:disabled={!loggedIn} href={link.href} on:click={(e) => go(link.href, e)}>{t(link.key, $lang)}</a>
      {/if}
    {/each}
  </nav>
</aside>

<style>
  .sidebar {
    background: #111827;
    color: #f9fafb;
    padding: 24px;
  }

  .brand {
    font-weight: 700;
    font-size: 20px;
    margin-bottom: 32px;
    letter-spacing: 0.5px;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .brand-icon {
    width: 44px;
    height: 44px;
    object-fit: contain;
  }

  nav {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  a {
    color: #f9fafb;
    text-decoration: none;
    padding: 10px 12px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.05);
  }

  a:hover {
    background: rgba(255, 255, 255, 0.15);
  }

  a.disabled {
    opacity: 0.5;
    pointer-events: none;
  }

</style>
