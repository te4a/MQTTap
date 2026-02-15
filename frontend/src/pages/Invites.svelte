<script>
  import { api } from '../lib.js'
  import { lang, t } from '../i18n.js'

  let invites = []
  let role = 'user'
  let code = ''
  let isActive = true
  let isSingleUse = false
  let error = ''
  let message = ''
  let isAdmin = false

  async function load() {
    error = ''
    try {
      const me = await api.me()
      isAdmin = me.role === 'admin'
      if (!isAdmin) {
        error = t('invites.adminOnly', $lang)
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
      const payload = { role_name: role, is_active: isActive, is_single_use: isSingleUse }
      if (code.trim()) payload.code = code.trim()
      const created = await api.createInvite(payload)
      invites = [...invites, created]
      code = ''
      message = t('messages.created', $lang)
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
        is_active: item.is_active,
        is_single_use: item.is_single_use
      }
      const updated = await api.updateInvite(item.id, payload)
      invites = invites.map(inv => (inv.id === updated.id ? updated : inv))
      message = t('messages.saved', $lang)
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
      message = t('messages.deleted', $lang)
    } catch (err) {
      error = err.message
    }
  }

  load()
</script>

<section class="card">
  <h2>{t('invites.title', $lang)}</h2>

  {#if !isAdmin}
    <div class="error">{error || t('invites.adminOnly', $lang)}</div>
  {:else}
    <div class="create">
      <label>{t('common.role', $lang)}</label>
      <select bind:value={role}>
        <option value="user">{t('role.user', $lang)}</option>
        <option value="admin">{t('role.admin', $lang)}</option>
      </select>

      <label>{t('common.code', $lang)} ({t('common.optional', $lang)})</label>
      <input bind:value={code} placeholder={t('placeholders.inviteAuto', $lang)} />

      <label>{t('common.active', $lang)}</label>
      <select bind:value={isActive}>
        <option value={true}>{t('common.true', $lang)}</option>
        <option value={false}>{t('common.false', $lang)}</option>
      </select>

      <label>{t('common.singleUse', $lang)}</label>
      <select bind:value={isSingleUse}>
        <option value={true}>{t('common.true', $lang)}</option>
        <option value={false}>{t('common.false', $lang)}</option>
      </select>

      <button on:click={createInvite}>{t('invites.create', $lang)}</button>
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
            <th>{t('common.id', $lang)}</th>
            <th>{t('common.code', $lang)}</th>
            <th>{t('common.role', $lang)}</th>
            <th>{t('common.active', $lang)}</th>
            <th>{t('common.singleUse', $lang)}</th>
            <th>{t('common.actions', $lang)}</th>
          </tr>
        </thead>
        <tbody>
          {#each invites as inv}
            <tr>
              <td>{inv.id}</td>
              <td><input class="code-input" bind:value={inv.code} /></td>
              <td>
                <select bind:value={inv.role_name}>
                  <option value="user">{t('role.user', $lang)}</option>
                  <option value="admin">{t('role.admin', $lang)}</option>
                </select>
              </td>
              <td>
                <select bind:value={inv.is_active}>
                  <option value={true}>{t('common.true', $lang)}</option>
                  <option value={false}>{t('common.false', $lang)}</option>
                </select>
              </td>
              <td>
                <select bind:value={inv.is_single_use}>
                  <option value={true}>{t('common.true', $lang)}</option>
                  <option value={false}>{t('common.false', $lang)}</option>
                </select>
              </td>
              <td class="actions">
                <button class="ghost" on:click={() => saveInvite(inv)}>{t('common.save', $lang)}</button>
                <button class="ghost" on:click={() => removeInvite(inv)}>{t('common.delete', $lang)}</button>
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
