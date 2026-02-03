<script>
  import { onMount } from 'svelte'
  import { api } from '../lib.js'

  let topics = []
  let selectedTopic = ''
  let fields = []
  let selectedFields = new Set()
  let rows = []
  let error = ''
  let loading = false

  let fromTs = ''
  let toTs = ''
  let order = 'desc'

  onMount(loadTopics)

  async function loadTopics() {
    error = ''
    try {
      topics = await api.topics()
      if (topics.length) {
        selectedTopic = topics[0].topic
        updateFields()
      }
    } catch (err) {
      error = err.message
    }
  }

  function updateFields() {
    const topic = topics.find(t => t.topic === selectedTopic)
    fields = topic ? topic.fields : []
    selectedFields = new Set(fields)
  }

  function toggleField(field) {
    const next = new Set(selectedFields)
    if (next.has(field)) next.delete(field)
    else next.add(field)
    selectedFields = next
  }

  async function loadHistory() {
    if (!selectedTopic) return
    loading = true
    error = ''
    try {
      const payload = {
        topic: selectedTopic,
        fields: Array.from(selectedFields).join(','),
        from_ts: fromTs || undefined,
        to_ts: toTs || undefined,
        order
      }
      const data = await api.history(payload)
      rows = data.rows || []
    } catch (err) {
      error = err.message
    } finally {
      loading = false
    }
  }
</script>

<section class="card">
  <h2>История значений</h2>

  <div class="filters">
    <div>
      <label>Топик</label>
      <select bind:value={selectedTopic} on:change={updateFields}>
        {#each topics as t}
          <option value={t.topic}>{t.topic}</option>
        {/each}
      </select>
    </div>

    <div class="fields">
      <label>Поля</label>
      <div class="field-list">
        {#each fields as field}
          <label class="chip">
            <input type="checkbox" checked={selectedFields.has(field)} on:change={() => toggleField(field)} />
            {field}
          </label>
        {/each}
      </div>
    </div>

    <div>
      <label>С</label>
      <input type="datetime-local" bind:value={fromTs} />
    </div>
    <div>
      <label>По</label>
      <input type="datetime-local" bind:value={toTs} />
    </div>
    <div>
      <label>Порядок</label>
      <select bind:value={order}>
        <option value="desc">Новые сверху</option>
        <option value="asc">Старые сверху</option>
      </select>
    </div>

    <button on:click={loadHistory} disabled={loading}>Загрузить</button>
  </div>

  {#if error}
    <div class="error">{error}</div>
  {/if}

  {#if rows.length === 0}
    <div class="empty">Нет данных</div>
  {:else}
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            {#each Object.keys(rows[0]) as col}
              <th>{col}</th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each rows as row}
            <tr>
              {#each Object.keys(row) as col}
                <td>{row[col]}</td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</section>

<style>
  .card {
    background: #ffffff;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 6px 16px rgba(0,0,0,0.06);
  }

  .filters {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
    margin-bottom: 16px;
  }

  label {
    font-size: 13px;
    color: #4b5563;
  }

  select, input {
    width: 100%;
    padding: 8px 10px;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
  }

  button {
    align-self: end;
    background: #111827;
    color: white;
    border: none;
    padding: 10px 12px;
    border-radius: 8px;
    cursor: pointer;
  }

  .fields {
    grid-column: 1 / -1;
  }

  .field-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 6px;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    border-radius: 999px;
    background: #f3f4f6;
    font-size: 12px;
  }

  .error {
    color: #b91c1c;
    margin-bottom: 8px;
  }

  .empty {
    color: #9ca3af;
  }

  .table-wrap {
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th, td {
    padding: 8px 10px;
    border-bottom: 1px solid #e5e7eb;
    font-size: 13px;
  }

  th {
    text-align: left;
    background: #f9fafb;
  }
</style>