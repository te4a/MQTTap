<script>
  import { api } from '../lib.js'
  import { lang, t } from '../i18n.js'

  let users = []
  let meId = null
  let isAdmin = false
  let error = ''
  let message = ''
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
      message = t('messages.created', $lang)
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
      await load()
    } catch (err) {
      error = err.message
    }
  }

  async function resetPassword(user) {
    const pwd = prompt(t('common.password', $lang))
    if (!pwd) return
    error = ''
    try {
      await api.updateUser(user.id, { password: pwd })
      await load()
    } catch (err) {
      error = err.message
    }
  }

  async function removeUser(user) {
    error = ''
    try {
      await api.deleteUser(user.id)
      await load()
    } catch (err) {
      error = err.message
    }
  }

  load()
</script>

<section class="card">
  <h2>{t('users.title', $lang)}</h2>
  {#if isAdmin}
    <h3>{t('users.create', $lang)}</h3>
    <div class="grid">
      <label>{t('common.username', $lang)}</label>
      <input bind:value={form.username} />

      <label>{t('common.email', $lang)}</label>
      <input bind:value={form.email} />

      <label>{t('common.password', $lang)}</label>
      <input type="password" bind:value={form.password} />

      <label>{t('common.role', $lang)}</label>
      <select bind:value={form.role}>
        <option value="user">{t('role.user', $lang)}</option>
        <option value="admin">{t('role.admin', $lang)}</option>
        <option value="pending">{t('role.pending', $lang)}</option>
      </select>
    </div>

    <button on:click={createUser}>{t('common.create', $lang)}</button>

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
    <h3>{t('users.list', $lang)}</h3>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>{t('common.username', $lang)}</th>
            <th>{t('common.email', $lang)}</th>
            <th>{t('common.role', $lang)}</th>
            <th>{t('common.actions', $lang)}</th>
          </tr>
        </thead>
        <tbody>
          {#each users as u}
            <tr>
              <td>{u.id}</td>
              <td>{u.username}</td>
              <td class="email-cell">
                <input class="email-input" bind:value={u.email} placeholder={t('users.emailPlaceholder', $lang)} />
                <button class="ghost" on:click={() => saveEmail(u)}>{t('common.save', $lang)}</button>
              </td>
              <td>
                <select value={u.role} on:change={(e) => updateRole(u, e.target.value)}>
                  <option value="user">{t('role.user', $lang)}</option>
                  <option value="admin">{t('role.admin', $lang)}</option>
                  <option value="pending">{t('role.pending', $lang)}</option>
                </select>
              </td>
              <td class="actions">
                <button class="ghost" on:click={() => resetPassword(u)}>{t('users.resetPassword', $lang)}</button>
                <button class="ghost" disabled={u.id === meId} on:click={() => removeUser(u)}>{t('common.delete', $lang)}</button>
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

  .ok,
  .error {
    margin-top: 10px;
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
