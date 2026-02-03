<script>
  import { createEventDispatcher, onMount } from 'svelte'
  import { api, clearToken, getToken } from '../lib.js'

  const dispatch = createEventDispatcher()
  let user = null
  let error = ''

  async function loadMe() {
    if (!getToken()) {
      user = null
      return
    }
    try {
      user = await api.me()
    } catch (err) {
      error = err.message
      clearToken()
      user = null
    }
  }

  function logout() {
    clearToken()
    user = null
    dispatch('authChange')
  }

  onMount(() => {
    loadMe()
    const handler = () => loadMe()
    window.addEventListener('authChange', handler)
    window.addEventListener('hashchange', handler)
    return () => {
      window.removeEventListener('authChange', handler)
      window.removeEventListener('hashchange', handler)
    }
  })
</script>

<header class="topbar">
  <div class="title">MQTT consumer</div>
  <div class="spacer"></div>
  {#if user}
    <div class="user">{user.email} · {user.role}</div>
    <button on:click={logout}>Выйти</button>
  {:else}
    <a href="#/login">Войти</a>
  {/if}
</header>

{#if error}
  <div class="error">{error}</div>
{/if}

<style>
  .topbar {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 16px 24px;
    background: #ffffff;
    border-bottom: 1px solid #e5e7eb;
  }

  .title {
    font-weight: 600;
  }

  .spacer {
    flex: 1;
  }

  .user {
    font-size: 14px;
    color: #374151;
  }

  button {
    border: none;
    background: #111827;
    color: white;
    padding: 8px 12px;
    border-radius: 8px;
    cursor: pointer;
  }

  a {
    color: #111827;
    text-decoration: none;
    font-weight: 600;
  }

  .error {
    margin: 12px 24px 0;
    color: #b91c1c;
    font-size: 13px;
  }
</style>
