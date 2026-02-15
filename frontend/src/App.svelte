<script>
  import { onMount } from 'svelte'
  import Sidebar from './components/Sidebar.svelte'
  import Topbar from './components/Topbar.svelte'
  import Login from './pages/Login.svelte'
  import Register from './pages/Register.svelte'
  import History from './pages/History.svelte'
  import Chart from './pages/Chart.svelte'
  import Settings from './pages/Settings.svelte'
  import Users from './pages/Users.svelte'
  import Profile from './pages/Profile.svelte'
  import Invites from './pages/Invites.svelte'
  import { lang, t } from './i18n.js'
  import { api, getToken, clearToken } from './lib.js'

  const routes = {
    '/history': History,
    '/chart': Chart,
    '/profile': Profile,
    '/invites': Invites,
    '/settings': Settings,
    '/users': Users,
    '/login': Login,
    '/register': Register
  }

  let loggedIn = false
  let authResolved = false
  let user = null
  let userRole = ''
  let featureAccess = { history: true, charts: true }
  let currentPath = window.location.pathname || '/'

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

  function hasFeatureAccess(feature) {
    const access = featureAccess
    if (feature === 'history') return access.history
    if (feature === 'charts') return access.charts
    return true
  }

  function normalizeFeatureAccess(source) {
    const raw = source?.feature_access
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
          toBool(source?.can_access_history, true)
        ),
        charts: toBool(
          normalized.charts ?? normalized.can_access_charts ?? normalized.charts_enabled,
          toBool(source?.can_access_charts, true)
        )
      }
    }
    return {
      history: toBool(source?.can_access_history, true),
      charts: toBool(source?.can_access_charts, true)
    }
  }

  function navigate(path) {
    if (loggedIn && !isRouteAllowed(path)) {
      path = resolveFallbackPath()
    }
    if (path === currentPath) return
    window.history.pushState({}, '', path)
    currentPath = path
  }

  function resolveRoute(path) {
    if (path === '/') return Profile
    const resolved = routes[path] || Profile
    if (loggedIn && !isRouteAllowed(path)) return Profile
    return resolved
  }

  function resolveTitle(path) {
    const map = {
      '/': 'nav.profile',
      '/history': 'nav.history',
      '/chart': 'nav.charts',
      '/profile': 'nav.profile',
      '/settings': 'nav.settings',
      '/users': 'nav.users',
      '/invites': 'nav.invites',
      '/login': 'nav.login',
      '/register': 'nav.register'
    }
    const key = map[path] || 'nav.history'
    if (loggedIn && !isRouteAllowed(path)) return t('nav.profile', $lang)
    return t(key, $lang)
  }

  function isRouteAllowed(path) {
    if (!loggedIn) return path === '/login' || path === '/register'
    if (!user) return true
    if (path === '/settings' || path === '/users' || path === '/invites') {
      return user.role === 'admin'
    }
    if (path === '/history') return hasFeatureAccess('history')
    if (path === '/chart') return hasFeatureAccess('charts')
    if (path === '/') return true
    return true
  }

  function resolveFallbackPath() {
    if (hasFeatureAccess('history')) return '/history'
    if (hasFeatureAccess('charts')) return '/chart'
    return '/profile'
  }

  async function refreshAuth() {
    loggedIn = !!getToken()
    authResolved = false
    if (!loggedIn) {
      user = null
      userRole = ''
      featureAccess = { history: true, charts: true }
      authResolved = true
      return
    }
    featureAccess = { history: true, charts: true }
    try {
      user = await api.me()
      user = { ...user, feature_access: normalizeFeatureAccess(user) }
      userRole = user.role || ''
      featureAccess = normalizeFeatureAccess(user)
      if (currentPath === '/') {
        navigate(resolveFallbackPath())
        return
      }
      if (!isRouteAllowed(currentPath)) {
        navigate(resolveFallbackPath())
      }
    } catch {
      clearToken()
      loggedIn = false
      user = null
      userRole = ''
      featureAccess = { history: true, charts: true }
      window.dispatchEvent(new Event('authChange'))
    } finally {
      authResolved = true
    }
  }

  onMount(() => {
    refreshAuth()
    const handler = () => refreshAuth()
    const popHandler = () => {
      currentPath = window.location.pathname || '/'
    }
    window.addEventListener('authChange', handler)
    window.addEventListener('popstate', popHandler)
    return () => {
      window.removeEventListener('authChange', handler)
      window.removeEventListener('popstate', popHandler)
    }
  })
</script>

{#if !loggedIn}
  <div class="login-only">
    {#if currentPath === '/register'}
      <Register on:navigate={(e) => navigate(e.detail)} />
    {:else}
      <Login on:navigate={(e) => navigate(e.detail)} />
    {/if}
  </div>
{:else if !authResolved}
  <div class="booting">{t('common.loading', $lang)}</div>
{:else}
  <div class="app">
    <Sidebar
      {loggedIn}
      role={userRole}
      featureAccess={featureAccess}
      isAdmin={userRole === 'admin'}
      {navigate}
    />
    <div class="main">
      <Topbar {user} title={resolveTitle(currentPath)} on:authChange={refreshAuth} />
      <div class="content">
        <svelte:component this={resolveRoute(currentPath)} />
      </div>
    </div>
  </div>
{/if}

<style>
  .login-only {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }

  .app {
    display: grid;
    grid-template-columns: 240px 1fr;
    min-height: 100vh;
  }

  .booting {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #6b7280;
    font-size: 14px;
  }

  .main {
    display: flex;
    flex-direction: column;
  }

  .content {
    padding: 24px;
  }

  @media (max-width: 900px) {
    .app {
      grid-template-columns: 1fr;
    }
  }
</style>
