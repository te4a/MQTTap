<script>
  import { api } from '../lib.js'
  import { lang, t } from '../i18n.js'

  let users = []
  let topics = []
  let topicRows = []
  let allTopics = []
  let fieldsByTopic = {}
  let meId = null
  let isAdmin = false
  let error = ''
  let message = ''
  let accessSearch = ''
  let form = {
    username: '',
    email: '',
    password: '',
    role: 'user',
    feature_access: { history: true, charts: true },
    allowed_topics: null,
    allowed_signals: null
  }

  async function load() {
    error = ''
    try {
      const me = await api.me()
      isAdmin = me.role === 'admin'
      meId = me.id
      if (!isAdmin) return
      const [usersData, topicsData] = await Promise.all([api.listUsers(), api.topics()])
      users = usersData || []
      topics = topicsData || []
      allTopics = topics.map(item => item.topic).sort()
      fieldsByTopic = Object.fromEntries(topics.map(item => [item.topic, item.fields || []]))
      topicRows = buildTopicRows(allTopics, fieldsByTopic)
      users = users.map(prepareUserState)
    } catch (err) {
      error = err.message
    }
  }

  function normalizeSignalMap(raw) {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {}
    const out = {}
    for (const [topic, fields] of Object.entries(raw)) {
      if (!Array.isArray(fields)) continue
      out[topic] = Array.from(new Set(fields.filter((f) => typeof f === 'string' && f.trim()))).sort()
    }
    return out
  }

  function buildFullSignalMap() {
    const out = {}
    for (const topic of allTopics) {
      out[topic] = (fieldsByTopic[topic] || []).slice().sort()
    }
    return out
  }

  function prepareUserState(user) {
    const allowedTopics = Array.isArray(user.allowed_topics) ? user.allowed_topics.slice().sort() : null
    const allowedSignals = normalizeSignalMap(user.allowed_signals)
    let draftSignals = {}
    if (allowedTopics === null) {
      draftSignals = buildFullSignalMap()
    } else {
      for (const topic of allowedTopics) {
        const knownFields = (fieldsByTopic[topic] || []).slice().sort()
        const restricted = allowedSignals[topic]
        draftSignals[topic] = (restricted && restricted.length ? restricted : knownFields)
      }
    }
    const featureAccess = user.feature_access && typeof user.feature_access === 'object'
      ? user.feature_access
      : { history: true, charts: true }
    return {
      ...user,
      feature_access: {
        history: featureAccess.history !== false,
        charts: featureAccess.charts !== false
      },
      topics_open: false,
      all_topics: allowedTopics === null,
      allowed_topics_draft: (allowedTopics === null ? allTopics.slice() : allowedTopics),
      allowed_signals_draft: draftSignals
    }
  }

  function buildTopicRows(topicList, topicFields) {
    const sortedTopics = [...topicList].sort()
    const prefixTopics = new Map()
    for (const topic of sortedTopics) {
      const parts = topic.split('/').filter(Boolean)
      let prefix = ''
      for (const part of parts) {
        prefix = prefix ? `${prefix}/${part}` : part
        if (!prefixTopics.has(prefix)) {
          prefixTopics.set(prefix, new Set())
        }
        prefixTopics.get(prefix).add(topic)
      }
    }
    const seenGroups = new Set()
    const out = []
    for (const topic of sortedTopics) {
      const parts = topic.split('/').filter(Boolean)
      let prefix = ''
      for (let depth = 0; depth < parts.length; depth += 1) {
        const part = parts[depth]
        prefix = prefix ? `${prefix}/${part}` : part
        if (!seenGroups.has(prefix)) {
          out.push({
            type: 'group',
            id: prefix,
            label: part,
            depth,
            leafTopics: Array.from(prefixTopics.get(prefix) || []).sort()
          })
          seenGroups.add(prefix)
        }
      }
      out.push({
        type: 'topic',
        id: `topic::${topic}`,
        label: parts[parts.length - 1] || topic,
        topic,
        depth: parts.length,
        leafTopics: [topic]
      })
      for (const field of [...(topicFields[topic] || [])].sort()) {
        out.push({
          type: 'signal',
          id: `signal::${topic}::${field}`,
          label: field,
          topic,
          signal: field,
          depth: parts.length + 1,
          leafTopics: [topic]
        })
      }
    }
    return out
  }

  function rowVisible(row) {
    const q = accessSearch.trim().toLowerCase()
    if (!q) return true
    if (row.type === 'signal') return `${row.topic}/${row.signal}`.toLowerCase().includes(q)
    if (row.topic) return row.topic.toLowerCase().includes(q)
    return row.id.toLowerCase().includes(q)
  }

  async function createUser() {
    error = ''
    message = ''
    try {
      await api.createUser(form)
      form = { username: '', email: '', password: '', role: 'user', feature_access: { history: true, charts: true }, allowed_topics: null, allowed_signals: null }
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

  async function saveFeatureAccess(user) {
    error = ''
    try {
      await api.updateUser(user.id, {
        feature_access: {
          history: user.feature_access?.history !== false,
          charts: user.feature_access?.charts !== false
        }
      })
      message = t('messages.saved', $lang)
      await load()
    } catch (err) {
      error = err.message
    }
  }

  function toggleTopicsEditor(user) {
    user.topics_open = !user.topics_open
    users = [...users]
  }

  function setAllTopics(user, checked) {
    user.all_topics = checked
    if (checked) {
      user.allowed_topics_draft = allTopics.slice()
      user.allowed_signals_draft = buildFullSignalMap()
    } else if (!Array.isArray(user.allowed_topics_draft)) {
      user.allowed_topics_draft = []
      user.allowed_signals_draft = {}
    }
    users = [...users]
  }

  function isTopicSelected(user, topic) {
    if (user.all_topics) return true
    return (user.allowed_topics_draft || []).includes(topic)
  }

  function setTopicSelected(user, topic, checked) {
    const selected = new Set(user.all_topics ? allTopics : (user.allowed_topics_draft || []))
    const signals = { ...(user.allowed_signals_draft || {}) }
    if (checked) {
      selected.add(topic)
      signals[topic] = (fieldsByTopic[topic] || []).slice()
    } else {
      selected.delete(topic)
      delete signals[topic]
      user.all_topics = false
    }
    user.allowed_topics_draft = Array.from(selected).sort()
    user.allowed_signals_draft = signals
    users = [...users]
  }

  function isSignalSelected(user, topic, signal) {
    if (user.all_topics) return true
    const list = user.allowed_signals_draft?.[topic] || []
    return list.includes(signal)
  }

  function setSignalSelected(user, topic, signal, checked) {
    const signals = { ...(user.allowed_signals_draft || {}) }
    const selectedTopics = new Set(user.all_topics ? allTopics : (user.allowed_topics_draft || []))
    const list = new Set(signals[topic] || [])
    if (checked) {
      list.add(signal)
      selectedTopics.add(topic)
    } else {
      list.delete(signal)
      user.all_topics = false
    }
    if (list.size === 0) {
      delete signals[topic]
      selectedTopics.delete(topic)
    } else {
      signals[topic] = Array.from(list).sort()
    }
    user.allowed_signals_draft = signals
    user.allowed_topics_draft = Array.from(selectedTopics).sort()
    users = [...users]
  }

  function isNodeChecked(user, row) {
    if (user.all_topics) return true
    const selected = new Set(user.allowed_topics_draft || [])
    return row.leafTopics.every(topic => selected.has(topic))
  }

  function toggleNode(user, row, checked) {
    const selected = new Set(user.all_topics ? allTopics : (user.allowed_topics_draft || []))
    const signals = { ...(user.allowed_signals_draft || {}) }
    if (checked) {
      row.leafTopics.forEach((topic) => {
        selected.add(topic)
        signals[topic] = (fieldsByTopic[topic] || []).slice()
      })
    } else {
      row.leafTopics.forEach((topic) => {
        selected.delete(topic)
        delete signals[topic]
      })
      user.all_topics = false
    }
    user.allowed_topics_draft = Array.from(selected).sort()
    user.allowed_signals_draft = signals
    users = [...users]
  }

  async function saveTopics(user) {
    error = ''
    message = ''
    try {
      await api.updateUser(user.id, {
        allowed_topics: user.all_topics ? null : (user.allowed_topics_draft || []),
        allowed_signals: user.all_topics ? null : (user.allowed_signals_draft || {})
      })
      message = t('messages.saved', $lang)
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

      <label>{t('users.featureAccess', $lang)}</label>
      <div class="feature-access">
        <label class="toggle">
          <span>{t('nav.history', $lang)}</span>
          <input type="checkbox" bind:checked={form.feature_access.history} />
        </label>
        <label class="toggle">
          <span>{t('nav.charts', $lang)}</span>
          <input type="checkbox" bind:checked={form.feature_access.charts} />
        </label>
      </div>
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
            <th>{t('common.id', $lang)}</th>
            <th>{t('common.username', $lang)}</th>
            <th>{t('common.email', $lang)}</th>
            <th>{t('common.role', $lang)}</th>
            <th>{t('users.featureAccess', $lang)}</th>
            <th>{t('users.topicAccess', $lang)}</th>
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
              <td>
                <div class="feature-access compact">
                  <label class="toggle">
                    <span>{t('nav.history', $lang)}</span>
                    <input type="checkbox" bind:checked={u.feature_access.history} on:change={() => saveFeatureAccess(u)} />
                  </label>
                  <label class="toggle">
                    <span>{t('nav.charts', $lang)}</span>
                    <input type="checkbox" bind:checked={u.feature_access.charts} on:change={() => saveFeatureAccess(u)} />
                  </label>
                </div>
              </td>
              <td>
                <button class="ghost" on:click={() => toggleTopicsEditor(u)}>
                  {u.topics_open ? t('common.hide', $lang) : t('common.edit', $lang)}
                </button>
              </td>
              <td class="actions">
                <button class="ghost" on:click={() => resetPassword(u)}>{t('users.resetPassword', $lang)}</button>
                <button class="ghost" disabled={u.id === meId} on:click={() => removeUser(u)}>{t('common.delete', $lang)}</button>
              </td>
            </tr>
            {#if u.topics_open}
              <tr>
                <td colspan="7">
                  <div class="topics-editor">
                    <div class="topics-toolbar">
                      <label class="all-topics">
                        <input type="checkbox" checked={u.all_topics} on:change={(e) => setAllTopics(u, e.target.checked)} />
                        <span>{t('users.allTopics', $lang)}</span>
                      </label>
                      <input class="search" bind:value={accessSearch} placeholder={t('users.searchTopicSignal', $lang)} />
                    </div>
                    <div class="topics-tree">
                      {#each topicRows as row}
                        {#if rowVisible(row)}
                          {#if row.type === 'signal'}
                            <label class="topic-node signal" style={`padding-left: ${8 + row.depth * 16}px`}>
                              <input
                                type="checkbox"
                                disabled={u.all_topics}
                                checked={isSignalSelected(u, row.topic, row.signal)}
                                on:change={(e) => setSignalSelected(u, row.topic, row.signal, e.target.checked)}
                              />
                              <span>{row.signal}</span>
                            </label>
                          {:else if row.type === 'topic'}
                            <label class="topic-node topic" style={`padding-left: ${8 + row.depth * 16}px`}>
                              <input
                                type="checkbox"
                                disabled={u.all_topics}
                                checked={isTopicSelected(u, row.topic)}
                                on:change={(e) => setTopicSelected(u, row.topic, e.target.checked)}
                              />
                              <span class="topic-path">{row.topic}</span>
                              <span class="topic-count">{(fieldsByTopic[row.topic] || []).length}</span>
                            </label>
                          {:else}
                            <label class="topic-node group" style={`padding-left: ${8 + row.depth * 16}px`}>
                              <input
                                type="checkbox"
                                disabled={u.all_topics}
                                checked={isNodeChecked(u, row)}
                                on:change={(e) => toggleNode(u, row, e.target.checked)}
                              />
                              <span>{row.label}</span>
                            </label>
                          {/if}
                        {/if}
                      {/each}
                    </div>
                    <div class="topics-actions">
                      <button class="ghost" on:click={() => saveTopics(u)}>{t('common.save', $lang)}</button>
                    </div>
                  </div>
                </td>
              </tr>
            {/if}
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

  .topics-editor {
    border: 1px solid #d8dee6;
    border-radius: 12px;
    padding: 12px;
    background: linear-gradient(180deg, #f9fbff, #f6f8fc);
    display: grid;
    gap: 10px;
  }

  .topics-toolbar {
    display: flex;
    gap: 12px;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
  }

  .all-topics {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
  }

  .all-topics input[type="checkbox"] {
    width: 16px;
    height: 16px;
    flex: 0 0 auto;
    margin: 0;
    padding: 0;
  }

  .search {
    max-width: 280px;
    width: 100%;
  }

  .topics-tree {
    border: 1px solid #dfe5ee;
    border-radius: 10px;
    max-height: 260px;
    overflow: auto;
    background: #ffffff;
    padding: 8px 0;
  }

  .topic-node {
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 28px;
    font-size: 13px;
    border-radius: 8px;
    margin: 2px 6px;
    padding-right: 8px;
  }

  .topic-node:hover {
    background: #f4f7ff;
  }

  .topic-node input[type="checkbox"] {
    width: 16px;
    height: 16px;
    flex: 0 0 auto;
    margin: 0;
    padding: 0;
  }

  .topic-node.group {
    font-weight: 600;
    color: #374151;
  }

  .topic-node.topic {
    color: #0f172a;
  }

  .topic-node.signal {
    color: #475569;
  }

  .topic-path {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .topic-count {
    font-size: 11px;
    color: #64748b;
    border: 1px solid #dbe3ee;
    border-radius: 999px;
    padding: 1px 6px;
    background: #fff;
  }

  .topics-actions {
    display: flex;
    justify-content: flex-end;
  }

  .feature-access {
    display: flex;
    align-items: center;
    gap: 14px;
    flex-wrap: wrap;
  }

  .feature-access.compact {
    gap: 10px;
  }

  .toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: #334155;
  }

  .toggle input[type="checkbox"] {
    width: 16px;
    height: 16px;
    margin: 0;
    padding: 0;
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
