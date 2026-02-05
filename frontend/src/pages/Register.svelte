<script>
  import { createEventDispatcher } from 'svelte'
  import { api } from '../lib.js'

  const dispatch = createEventDispatcher()
  let username = ''
  let password = ''
  let confirmPassword = ''
  let email = ''
  let invite = ''
  let error = ''
  let message = ''

  async function submit() {
    error = ''
    message = ''
    if (!username || !password) {
      error = 'Username and password required'
      return
    }
    if (password !== confirmPassword) {
      error = 'Passwords do not match'
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
      message = 'Registration submitted'
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
  <h2>Registration</h2>
  <label>Username</label>
  <input type="text" bind:value={username} placeholder="username" />

  <label>Email (optional)</label>
  <input type="email" bind:value={email} placeholder="name@example.com" />

  <label>Invite code (optional)</label>
  <input type="text" bind:value={invite} />

  <label>Password</label>
  <input type="password" bind:value={password} />

  <label>Confirm password</label>
  <input type="password" bind:value={confirmPassword} />

  <button on:click={submit}>Register</button>

  {#if message}
    <div class="ok">{message}</div>
  {/if}
  {#if error}
    <div class="error">{error}</div>
  {/if}

  <div class="hint">
    Already have an account? <a href="/login" on:click={goLogin}>Sign in</a>
  </div>
</div>

<style>
  .register-card {
    max-width: 420px;
    margin: 40px auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .hint {
    margin-top: 8px;
    font-size: 13px;
    color: #6b7280;
  }

  .hint a {
    color: #111827;
  }
</style>
