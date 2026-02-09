<script>
  import { createEventDispatcher } from 'svelte'
  import { clearToken } from '../lib.js'
  import { availableLangs, lang, setLang, t } from '../i18n.js'

  export let user = null
  export let title = ''
  const dispatch = createEventDispatcher()

  function logout() {
    clearToken()
    dispatch('authChange')
  }

</script>

<header class="topbar">
  <div class="title">{title}</div>
  <div class="spacer"></div>
  <select class="lang" bind:value={$lang} on:change={(e) => setLang(e.target.value)}>
    {#each availableLangs as item}
      <option value={item.value}>{item.label}</option>
    {/each}
  </select>
  {#if user}
    <div class="user">{user.username}</div>
    <button on:click={logout}>{t('topbar.logout', $lang)}</button>
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

  .lang {
    padding: 4px 8px;
    border-radius: 999px;
    border: 1px solid #e5e7eb;
    background: #ffffff;
    font-size: 12px;
    width: auto;
    min-width: 56px;
    display: inline-block;
  }
</style>
