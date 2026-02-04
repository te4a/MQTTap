<script>
  import { createEventDispatcher } from 'svelte'
  import { clearToken } from '../lib.js'

  export let user = null
  const dispatch = createEventDispatcher()

  function logout() {
    clearToken()
    dispatch('authChange')
  }
</script>

<header class="topbar">
  <div class="title">MQTT consumer</div>
  <div class="spacer"></div>
  {#if user}
    <div class="user">{user.username} · {user.role}</div>
    <button on:click={logout}>Выйти</button>
  {/if}
</header>

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
</style>