<script>
  import { onMount } from 'svelte'
  import Router from 'svelte-spa-router'
  import Sidebar from './components/Sidebar.svelte'
  import Topbar from './components/Topbar.svelte'
  import Login from './pages/Login.svelte'
  import History from './pages/History.svelte'
  import Chart from './pages/Chart.svelte'
  import Settings from './pages/Settings.svelte'
  import Users from './pages/Users.svelte'
  import { api, getToken, clearToken } from './lib.js'

  const routes = {
    '/': History,
    '/chart': Chart,
    '/settings': Settings,
    '/users': Users,
    '/login': Login
  }

  let loggedIn = false
  let user = null

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
    window.addEventListener('authChange', handler)
    return () => window.removeEventListener('authChange', handler)
  })
</script>

{#if !loggedIn}
  <div class="login-only">
    <Login />
  </div>
{:else}
  <div class="app">
    <Sidebar {loggedIn} isAdmin={user?.role === 'admin'} />
    <div class="main">
      <Topbar {user} on:authChange={refreshAuth} />
      <div class="content">
        <Router {routes} />
      </div>
    </div>
  </div>
{/if}

<style>
  :global(body) {
    margin: 0;
    font-family: system-ui, sans-serif;
    background: #f4f2ee;
    color: #1f2328;
  }

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