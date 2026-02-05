<script>
  import { onMount } from 'svelte'
  import { api } from '../lib.js'

  let users = []
  let error = ''
  let message = ''
  let isAdmin = false
  let meId = null

  let form = {
    username: '',
    email: '',
    password: '',
    role: 'user'
  }

  async function load() {
    error = ''
    try {
      const me = await api.me()
      isAdmin = me.role === 'admin'
      meId = me.id
      if (!isAdmin) return
      users = await api.listUsers()
    } catch (err) {
      error = err.message
    }
  }

  async function createUser() {
    error = ''
    message = ''
    try {
      await api.createUser(form)
      form = { username: '', email: '', password: '', role: 'user' }
      message = 'Пользователь создан'
      await load()
    } catch (err) {
      error = err.message
    }
  }

  async function updateRole(user, role) {
    error = ''
    try {
      await api.updateUser(user.id, { role })
      await load()
    } catch (err) {
      error = err.message
    }
  }

  async function saveEmail(user) {
    error = ''
    try {
      await api.updateUser(user.id, { email: user.email || null })
      message = 'Email обновлён'
    } catch (err) {
      error = err.message
    }
  }

  async function resetPassword(user) {
    const newPass = prompt('Новый пароль')
    if (!newPass) return
    error = ''
    try {
      await api.updateUser(user.id, { password: newPass })
      message = 'Пароль обновлён'
    } catch (err) {
      error = err.message
    }
  }

  async function removeUser(user) {
    if (user.id === meId) return
    if (!confirm(`Удалить пользователя ${user.username}?`)) return
    error = ''
    try {
      await api.deleteUser(user.id)
      await load()
    } catch (err) {
      error = err.message
    }
  }

  onMount(load)
</script>

<section class="card">
  <h2>Пользователи (admin)</h2>

  {#if !isAdmin}
    <div class="error">Доступ только для администратора</div>
  {:else}
    <div class="grid">
      <label>Username</label>
      <input bind:value={form.username} />

      <label>Email (optional)</label>
      <input bind:value={form.email} />

      <label>Пароль</label>
      <input type="password" bind:value={form.password} />

      <label>Роль</label>
      <select bind:value={form.role}>
        <option value="user">user</option>
        <option value="admin">admin</option>
      </select>
    </div>

    <button on:click={createUser}>Создать</button>

    {#if message}
      <div class="ok">{message}</div>
    {/if}
    {#if error}
      <div class="error">{error}</div>
    {/if}
  {/if}
</section>

{#if isAdmin}
  <section class="card">
    <h3>Список пользователей</h3>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Username</th>
            <th>Email</th>
            <th>Роль</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          {#each users as u}
            <tr>
              <td>{u.id}</td>
              <td>{u.username}</td>
              <td class="email-cell">
                <input class="email-input" bind:value={u.email} placeholder="-" />
                <button class="ghost" on:click={() => saveEmail(u)}>Сохранить</button>
              </td>
              <td>
                <select value={u.role} on:change={(e) => updateRole(u, e.target.value)}>
                  <option value="user">user</option>
                  <option value="admin">admin</option>
                </select>
              </td>
              <td class="actions">
                <button class="ghost" on:click={() => resetPassword(u)}>Сменить пароль</button>
                <button class="ghost" disabled={u.id === meId} on:click={() => removeUser(u)}>Удалить</button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>
{/if}

<style>
  .card {
    margin-bottom: 16px;
  }

  .grid {
    display: grid;
    grid-template-columns: 140px 1fr;
    gap: 12px;
    margin-bottom: 12px;
  }

  .ghost {
    background: transparent;
    color: #111827;
    border: 1px solid #e5e7eb;
    padding: 6px 10px;
  }

  .actions {
    display: flex;
    gap: 8px;
  }

  .email-cell {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .email-input {
    min-width: 180px;
  }

  .ok {
    margin-top: 10px;
  }

  .error {
    margin-top: 10px;
  }

  tbody tr:last-child td {
    border-bottom: none;
  }

  @media (max-width: 700px) {
    .grid {
      grid-template-columns: 1fr;
    }
    .actions {
      flex-direction: column;
    }
    .email-cell {
      flex-direction: column;
      align-items: stretch;
    }
  }
</style>
