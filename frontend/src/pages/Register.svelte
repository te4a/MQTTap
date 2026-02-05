<script>
  import { createEventDispatcher } from 'svelte'
  import { api } from '../lib.js'
  import { get } from 'svelte/store'
  import { availableLangs, lang, setLang, t } from '../i18n.js'

  const dispatch = createEventDispatcher()
  let username = ''
  let password = ''
  let confirmPassword = ''
  let email = ''
  let invite = ''
  let error = ''
  let message = ''

  function tr(key) {
    return t(key, get(lang))
  }

  async function submit() {
    error = ''
    message = ''
    if (!username || !password) {
      error = tr('errors.required')
      return
    }
    if (password !== confirmPassword) {
      error = tr('errors.passwordsMismatch')
      return
    }
    const payload = {
      username,
      password
    }
    if (email.trim()) payload.email = email.trim()
    if (invite.trim()) payload.invite = invite.trim()
    try {
      await api.register(payload)
      message = tr('messages.registrationSubmitted')
      password = ''
      confirmPassword = ''
    } catch (err) {
      error = err.message
    }
  }

  function goLogin(event) {
    event.preventDefault()
    dispatch('navigate', '/login')
  }
</script>

<div class="card register-card">
  <div class="lang-row">
    <select class="lang-select" bind:value={$lang} on:change={(e) => setLang(e.target.value)}>
      {#each availableLangs as item}
        <option value={item.value}>{item.label}</option>
      {/each}
    </select>
  </div>
  <h2>{t('register.title', $lang)}</h2>
  <label>{t('common.username', $lang)}</label>
  <input type="text" bind:value={username} placeholder={t('placeholders.username', $lang)} />

  <label>{t('common.email', $lang)} ({t('common.optional', $lang)})</label>
  <input type="email" bind:value={email} placeholder={t('placeholders.email', $lang)} />

  <label>{t('register.invite', $lang)} ({t('common.optional', $lang)})</label>
  <input type="text" bind:value={invite} />

  <label>{t('common.password', $lang)}</label>
  <input type="password" bind:value={password} />

  <label>{t('profile.confirmPassword', $lang)}</label>
  <input type="password" bind:value={confirmPassword} />

  <button on:click={submit}>{t('register.submit', $lang)}</button>

  {#if message}
    <div class="ok">{message}</div>
  {/if}
  {#if error}
    <div class="error">{error}</div>
  {/if}

  <div class="hint">
    {t('register.haveAccount', $lang)} <a href="/login" on:click={goLogin}>{t('login.title', $lang)}</a>
  </div>
</div>

<style>
  .register-card {
    max-width: 420px;
    margin: 40px auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
    position: relative;
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
