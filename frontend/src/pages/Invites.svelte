<script>
  import { api } from '../lib.js'

  let invites = []
  let role = 'user'
  let code = ''
  let isActive = true
  let error = ''
  let message = ''
  let isAdmin = false

  async function load() {
    error = ''
    try {
      const me = await api.me()
      isAdmin = me.role === 'admin'
      if (!isAdmin) {
        error = 'Admin only'
        return
      }
      invites = await api.listInvites()
    } catch (err) {
      error = err.message
    }
  }

  async function createInvite() {
    error = ''
    message = ''
    try {
      const payload = { role_name: role, is_active: isActive }
      if (code.trim()) payload.code = code.trim()
      const created = await api.createInvite(payload)
      invites = [...invites, created]
      code = ''
      message = 'Invite created'
    } catch (err) {
      error = err.message
    }
  }

  async function saveInvite(item) {
    error = ''
    message = ''
    try {
      const payload = {
        code: item.code,
        role_name: item.role_name,
        is_active: item.is_active
      }
      const updated = await api.updateInvite(item.id, payload)
      invites = invites.map(inv => (inv.id === updated.id ? updated : inv))
      message = 'Invite updated'
    } catch (err) {
      error = err.message
    }
  }

  async function removeInvite(item) {
    error = ''
    message = ''
    try {
      await api.deleteInvite(item.id)
      invites = invites.filter(inv => inv.id !== item.id)
      message = 'Invite deleted'
    } catch (err) {
      error = err.message
    }
  }

  load()
</script>

<section class="card">
  <h2>Invites</h2>

  {#if !isAdmin}
    <div class="error">{error || 'Admin only'}</div>
  {:else}
    <div class="create">
      <label>Role</label>
      <select bind:value={role}>
        <option value="user">user</option>
        <option value="admin">admin</option>
      </select>

      <label>Code (optional)</label>
      <input bind:value={code} placeholder="auto-generated if empty" />

      <label>Active</label>
      <select bind:value={isActive}>
        <option value={true}>true</option>
        <option value={false}>false</option>
      </select>

      <button on:click={createInvite}>Create invite</button>
    </div>

    {#if message}
      <div class="ok">{message}</div>
    {/if}
    {#if error}
      <div class="error">{error}</div>
    {/if}

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Code</th>
            <th>Role</th>
            <th>Active</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each invites as inv}
            <tr>
              <td>{inv.id}</td>
              <td><input class="code-input" bind:value={inv.code} /></td>
              <td>
                <select bind:value={inv.role_name}>
                  <option value="user">user</option>
                  <option value="admin">admin</option>
                </select>
              </td>
              <td>
                <select bind:value={inv.is_active}>
                  <option value={true}>true</option>
                  <option value={false}>false</option>
                </select>
              </td>
              <td class="actions">
                <button class="ghost" on:click={() => saveInvite(inv)}>Save</button>
                <button class="ghost" on:click={() => removeInvite(inv)}>Delete</button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</section>

<style>
  .create {
    display: grid;
    grid-template-columns: 140px 1fr;
    gap: 12px;
    margin-bottom: 16px;
    align-items: center;
  }

  .create button {
    grid-column: 2;
    justify-self: start;
  }

  .actions {
    display: flex;
    gap: 8px;
  }

  .code-input {
    min-width: 180px;
  }

  @media (max-width: 700px) {
    .create {
      grid-template-columns: 1fr;
    }
    .create button {
      grid-column: auto;
    }
  }
</style>
