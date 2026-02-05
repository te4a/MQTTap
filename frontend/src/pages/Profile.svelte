<script>
  import { api } from '../lib.js'

  let email = ''
  let currentPassword = ''
  let newPassword = ''
  let confirmPassword = ''
  let message = ''
  let error = ''

  async function load() {
    try {
      const me = await api.me()
      email = me.email || ''
    } catch (err) {
      error = err.message
    }
  }

  async function saveEmail() {
    error = ''
    message = ''
    try {
      await api.updateProfile({ email: email || null })
      message = 'Email updated'
    } catch (err) {
      error = err.message
    }
  }

  async function submit() {
    error = ''
    message = ''
    if (!currentPassword || !newPassword) {
      error = 'Current and new password required'
      return
    }
    if (newPassword !== confirmPassword) {
      error = 'Passwords do not match'
      return
    }
    try {
      await api.changePassword(currentPassword, newPassword)
      message = 'Password updated'
      currentPassword = ''
      newPassword = ''
      confirmPassword = ''
    } catch (err) {
      error = err.message
    }
  }

  load()
</script>

<section class="card">
  <div class="header">
    <div>
      <h2>Profile</h2>
      <p class="subtitle">Manage your account email and password.</p>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Email</div>
    <div class="section-body">
      <label>Email</label>
      <input type="email" bind:value={email} placeholder="name@example.com" />
      <div class="section-actions">
        <button class="ghost" on:click={saveEmail}>Update email</button>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Password</div>
    <div class="section-body">
      <label>Current password</label>
      <input type="password" bind:value={currentPassword} />

      <label>New password</label>
      <input type="password" bind:value={newPassword} />

      <label>Confirm password</label>
      <input type="password" bind:value={confirmPassword} />

      <div class="section-actions">
        <button on:click={submit}>Update password</button>
      </div>
    </div>
  </div>

  {#if message}
    <div class="ok">{message}</div>
  {/if}
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
