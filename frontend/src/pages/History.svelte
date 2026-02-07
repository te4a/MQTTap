<script>
  import { api } from '../lib.js'
  import { lang, t } from '../i18n.js'

  let topics = []
  let selectedTopic = ''
  let fields = []
  let selectedFields = []
  let fromTs = ''
  let toTs = ''
  let agg = 'off'
  let interval = 'minute'
  let intervalCount = 1
  let rows = []
  let error = ''
  let loading = false

  function shortInterval(value, langCode) {
    const map = {
      second: { en: 's', ru: 'с' },
      minute: { en: 'm', ru: 'м' },
      hour: { en: 'h', ru: 'ч' },
      day: { en: 'd', ru: 'д' }
    }
    const entry = map[value] || { en: value?.[0] || '', ru: value?.[0] || '' }
    return (langCode || 'en') === 'ru' ? entry.ru : entry.en
  }

  async function loadTopics() {
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
    selectedFields = fields.slice(0, 3)
  }

  function toggleField(field) {
    if (selectedFields.includes(field)) {
      selectedFields = selectedFields.filter(value => value !== field)
    } else {
      selectedFields = [...selectedFields, field]
    }
  }

  async function loadHistory() {
    error = ''
    loading = true
    try {
      const intervalValue = agg !== 'off'
        ? `${Math.max(1, Number(intervalCount) || 1)} ${interval}`
        : undefined
      const params = {
        topic: selectedTopic,
        fields: selectedFields.join(','),
        from_ts: fromTs || undefined,
        to_ts: toTs || undefined,
        agg: agg !== 'off' ? agg : undefined,
        interval: intervalValue
      }
      const data = await api.history(params)
      rows = data.rows || []
    } catch (err) {
      error = err.message
    } finally {
      loading = false
    }
  }

  loadTopics()
</script>

<section class="card">
  <h2>{t('history.title', $lang)}</h2>
  <div class="filters">
    <div>
      <label>{t('charts.topic', $lang)}</label>
      <select bind:value={selectedTopic} on:change={updateFields}>
        {#each topics as t}
          <option value={t.topic}>{t.topic}</option>
        {/each}
      </select>
    </div>
    <div class="fields">
      <label>{t('charts.fields', $lang)}</label>
      <div class="field-list">
        {#each fields as field}
          <label class="chip">
            <input type="checkbox" checked={selectedFields.includes(field)} on:change={() => toggleField(field)} />
            {field}
          </label>
        {/each}
      </div>
    </div>
    <div>
      <label>{t('common.aggregation', $lang)}</label>
      <select bind:value={agg}>
        <option value="off">{t('agg.off', $lang)}</option>
        <option value="avg">{t('agg.avg', $lang)}</option>
        <option value="min">{t('agg.min', $lang)}</option>
        <option value="max">{t('agg.max', $lang)}</option>
      </select>
    </div>
    {#if agg !== 'off'}
      <div>
        <label>{t('common.interval', $lang)}</label>
        <div class="interval-row">
          <span class="interval-label">{t('common.intervalEvery', $lang)}</span>
          <input type="number" min="1" step="1" bind:value={intervalCount} />
          <div class="select-short">
            <span class="select-short-label">{shortInterval(interval, $lang)}</span>
            <select bind:value={interval}>
              <option value="second">{t('interval.second', $lang)}</option>
              <option value="minute">{t('interval.minute', $lang)}</option>
              <option value="hour">{t('interval.hour', $lang)}</option>
              <option value="day">{t('interval.day', $lang)}</option>
            </select>
          </div>
        </div>
      </div>
    {/if}
    <div>
      <label>{t('common.from', $lang)}</label>
      <input type="datetime-local" bind:value={fromTs} />
    </div>
    <div>
      <label>{t('common.to', $lang)}</label>
      <input type="datetime-local" bind:value={toTs} />
    </div>
    <button on:click={loadHistory} disabled={loading}>{t('history.load', $lang)}</button>
  </div>

  {#if error}
    <div class="error">{error}</div>
  {/if}

  {#if rows.length === 0}
    <div class="empty">{t('history.noData', $lang)}</div>
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
  .filters {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
    margin-bottom: 16px;
  }

  button {
    align-self: end;
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

  .interval-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .interval-row input {
    width: 80px;
  }

  .interval-label {
    font-size: 12px;
    color: #6b7280;
  }

  .select-short {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 48px;
    padding: 8px 24px 8px 10px;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #ffffff;
  }

  .select-short select {
    position: absolute;
    inset: 0;
    opacity: 0;
    cursor: pointer;
  }

  .select-short-label {
    font-size: 12px;
    min-width: 32px;
    text-align: center;
  }

  .select-short::after {
    content: '';
    position: absolute;
    right: 8px;
    top: 50%;
    width: 6px;
    height: 6px;
    border-right: 2px solid #6b7280;
    border-bottom: 2px solid #6b7280;
    transform: translateY(-50%) rotate(45deg);
    pointer-events: none;
  }

  .error {
    margin-bottom: 8px;
  }

  .empty {
    color: #9ca3af;
  }
</style>
