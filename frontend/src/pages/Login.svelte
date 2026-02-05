<script>
  import { createEventDispatcher } from 'svelte'
  import { api, setToken } from '../lib.js'

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
</script>

<div class="card">
  <h2>Вход</h2>
  <label>Username</label>
  <input type="text" bind:value={username} placeholder="admin" />
  <label>Пароль</label>
  <input type="password" bind:value={password} />
  <button on:click={submit}>Войти</button>
  {#if error}
    <div class="error">{error}</div>
  {/if}
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
</style>
