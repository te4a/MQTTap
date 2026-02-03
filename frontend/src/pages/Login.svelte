<script>
  import { api, setToken } from '../lib.js'

  let email = ''
  let password = ''
  let error = ''

  async function submit() {
    error = ''
    try {
      const token = await api.login(email, password)
      setToken(token.access_token)
      window.dispatchEvent(new Event('authChange'))
      window.location.hash = '#/'
    } catch (err) {
      error = err.message
    }
  }
</script>

<div class="card">
  <h2>Вход</h2>
  <label>Email</label>
  <input type="email" bind:value={email} placeholder="admin@example.com" />
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
    border: 1px solid #e5e7eb;
    border-radius: 8px;
  }

  button {
    margin-top: 8px;
    background: #111827;
    color: white;
    border: none;
    padding: 10px 12px;
    border-radius: 8px;
    cursor: pointer;
  }

  .error {
    color: #b91c1c;
    font-size: 13px;
  }
</style>
