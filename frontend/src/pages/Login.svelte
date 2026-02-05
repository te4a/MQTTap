<script>
  import { createEventDispatcher } from 'svelte'
  import { api, setToken } from '../lib.js'
  import { availableLangs, lang, setLang, t } from '../i18n.js'

  const dispatch = createEventDispatcher()
  let username = ''
  let password = ''
  let error = ''

  async function submit() {
    error = ''
    try {
      const token = await api.login(username, password)
      setToken(token.access_token)
      dispatch('navigate', '/')
      window.dispatchEvent(new Event('authChange'))
    } catch (err) {
      error = err.message
    }
  }

  function goRegister(event) {
    event.preventDefault()
    dispatch('navigate', '/register')
  }
</script>

<div class="card">
  <div class="lang-row">
    <select class="lang-select" bind:value={$lang} on:change={(e) => setLang(e.target.value)}>
      {#each availableLangs as item}
        <option value={item.value}>{item.label}</option>
      {/each}
    </select>
  </div>
  <h2>{t('login.title', $lang)}</h2>
  <label>{t('common.username', $lang)}</label>
  <input type="text" bind:value={username} placeholder={t('placeholders.username', $lang)} />
  <label>{t('common.password', $lang)}</label>
  <input type="password" bind:value={password} />
  <button on:click={submit}>{t('login.submit', $lang)}</button>
  {#if error}
    <div class="error">{error}</div>
  {/if}
  <div class="hint">
    {t('login.noAccount', $lang)} <a href="/register" on:click={goRegister}>{t('login.register', $lang)}</a>
  </div>
</div>

<style>
  .card {
    max-width: 360px;
    margin: 40px auto;
    background: #ffffff;
    padding: 24px;
    border-radius: 12px;
    box-shadow: 0 10px 20px rgba(0,0,0,0.08);
    display: flex;
    flex-direction: column;
    gap: 10px;
    position: relative;
  }

  input {
    padding: 10px 12px;
  }

  button {
    margin-top: 8px;
  }

  .error {
    font-size: 13px;
  }

  .hint {
    margin-top: 8px;
    font-size: 13px;
    color: #6b7280;
  }

  .hint a {
    color: #111827;
  }

  .lang-row {
    position: absolute;
    top: 12px;
    right: 12px;
  }

  .lang-select {
    padding: 4px 8px;
    border-radius: 999px;
    border: 1px solid #e5e7eb;
    background: #ffffff;
    font-size: 12px;
  }
</style>
