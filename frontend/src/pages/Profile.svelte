<script>
  import { api } from '../lib.js'
  import { lang, t } from '../i18n.js'

  let email = ''
  let currentPassword = ''
  let newPassword = ''
  let confirmPassword = ''
  let maxPoints = 5000
  let message = ''
  let error = ''
  let emailMessage = ''
  let emailError = ''
  let passwordMessage = ''
  let passwordError = ''
  let chartMessage = ''
  let chartError = ''

  async function load() {
    try {
      const me = await api.me()
      email = me.email || ''
      maxPoints = Number(me.max_points ?? 5000)
    } catch (err) {
      error = err.message
    }
  }

  async function saveEmail() {
    emailError = ''
    emailMessage = ''
    try {
      await api.updateProfile({ email: email || null })
      emailMessage = t('messages.emailUpdated', $lang)
    } catch (err) {
      emailError = err.message
    }
  }

  async function submit() {
    passwordError = ''
    passwordMessage = ''
    if (!currentPassword || !newPassword) {
      passwordError = t('errors.required', $lang)
      return
    }
    if (newPassword !== confirmPassword) {
      passwordError = t('errors.passwordsMismatch', $lang)
      return
    }
    try {
      await api.changePassword(currentPassword, newPassword)
      passwordMessage = t('messages.passwordUpdated', $lang)
      currentPassword = ''
      newPassword = ''
      confirmPassword = ''
    } catch (err) {
      passwordError = err.message
    }
  }

  async function saveMaxPoints() {
    chartError = ''
    chartMessage = ''
    const value = Number(maxPoints)
    if (!Number.isFinite(value) || value < 1 || value > 5000) {
      chartError = t('errors.invalidMaxPoints', $lang)
      return
    }
    try {
      await api.updateProfile({ max_points: value })
      chartMessage = t('messages.saved', $lang)
    } catch (err) {
      chartError = err.message
    }
  }

  load()
</script>

<section class="card">
  <div class="header">
    <div>
      <h2>{t('profile.title', $lang)}</h2>
      <p class="subtitle">{t('profile.subtitle', $lang)}</p>
    </div>
  </div>

  <div class="section">
    <div class="section-title">{t('profile.emailSection', $lang)}</div>
    <div class="section-body">
      <label>{t('common.email', $lang)}</label>
      <input type="email" bind:value={email} placeholder={t('placeholders.email', $lang)} />
      <div class="section-actions">
        <button class="ghost" on:click={saveEmail}>{t('profile.updateEmail', $lang)}</button>
      </div>
      {#if emailMessage}
        <div class="ok">{emailMessage}</div>
      {/if}
      {#if emailError}
        <div class="error">{emailError}</div>
      {/if}
    </div>
  </div>

  <div class="section">
    <div class="section-title">{t('profile.passwordSection', $lang)}</div>
    <div class="section-body">
      <label>{t('profile.currentPassword', $lang)}</label>
      <input type="password" bind:value={currentPassword} />

      <label>{t('profile.newPassword', $lang)}</label>
      <input type="password" bind:value={newPassword} />

      <label>{t('profile.confirmPassword', $lang)}</label>
      <input type="password" bind:value={confirmPassword} />

      <div class="section-actions">
        <button on:click={submit}>{t('profile.updatePassword', $lang)}</button>
      </div>
      {#if passwordMessage}
        <div class="ok">{passwordMessage}</div>
      {/if}
      {#if passwordError}
        <div class="error">{passwordError}</div>
      {/if}
    </div>
  </div>

  <div class="section">
    <div class="section-title">{t('profile.chartsSection', $lang)}</div>
    <div class="section-body">
      <label>{t('profile.maxPoints', $lang)}</label>
      <input type="number" min="1" max="5000" step="1" bind:value={maxPoints} />
      <div class="section-actions">
        <button class="ghost" on:click={saveMaxPoints}>{t('profile.updateMaxPoints', $lang)}</button>
      </div>
      {#if chartMessage}
        <div class="ok">{chartMessage}</div>
      {/if}
      {#if chartError}
        <div class="error">{chartError}</div>
      {/if}
    </div>
  </div>

  {#if error}
    <div class="error">{error}</div>
  {/if}
</section>

<style>
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }

  .subtitle {
    margin: 4px 0 0;
    color: #6b7280;
    font-size: 13px;
  }

  .section {
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 16px;
    display: grid;
    gap: 12px;
    margin-bottom: 16px;
    background: #f9fafb;
  }

  .section-title {
    font-weight: 600;
  }

  .section-body {
    display: grid;
    gap: 10px;
  }

  .section-actions {
    display: flex;
    justify-content: flex-end;
  }

  .ok,
  .error {
    margin-top: 10px;
  }
</style>
