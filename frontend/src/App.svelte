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
    '/': History,
    '/chart': Chart,
    '/profile': Profile,
    '/invites': Invites,
    '/settings': Settings,
    '/users': Users,
    '/login': Login,
    '/register': Register
  }

  let loggedIn = false
  let user = null
  let currentPath = window.location.pathname || '/'

  function navigate(path) {
    if (path === currentPath) return
    window.history.pushState({}, '', path)
    currentPath = path
  }

  function resolveRoute(path) {
    return routes[path] || History
  }

  function resolveTitle(path) {
    const map = {
      '/': 'nav.history',
      '/chart': 'nav.charts',
      '/profile': 'nav.profile',
      '/settings': 'nav.settings',
      '/users': 'nav.users',
      '/invites': 'nav.invites',
      '/login': 'nav.login',
      '/register': 'nav.register'
    }
    const key = map[path] || 'nav.history'
    return t(key, $lang)
  }

  async function refreshAuth() {
    loggedIn = !!getToken()
    if (!loggedIn) {
      user = null
      return
    }
    try {
      user = await api.me()
    } catch {
      clearToken()
      loggedIn = false
      user = null
      window.dispatchEvent(new Event('authChange'))
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
{:else}
  <div class="app">
    <Sidebar {loggedIn} isAdmin={user?.role === 'admin'} {navigate} />
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
