<script>
  import { onMount, onDestroy, tick } from 'svelte'
  import Chart from 'chart.js/auto'
  import { api } from '../lib.js'

  let topics = []
  let selectedTopic = ''
  let fields = []
  let selectedField = ''
  let agg = 'avg'
  let interval = 'minute'
  let fromTs = ''
  let toTs = ''
  let showPoints = true
  let error = ''

  let charts = []
  let nextId = 1
  let refreshTimer = null
  const refreshMs = 5000

  onMount(async () => {
    try {
      topics = await api.topics()
      await loadSavedCharts()
      if (topics.length && !selectedTopic) {
        selectedTopic = topics[0].topic
        updateFields()
      }
    } catch (err) {
      error = err.message
    }
    refreshTimer = setInterval(refreshLiveCharts, refreshMs)
  })

  onDestroy(() => {
    if (refreshTimer) clearInterval(refreshTimer)
  })

  function isAggEnabled(value) {
    return value && value !== 'none'
  }

  async function refreshLiveCharts() {
    for (const item of charts) {
      if (!item.toTs) {
        await buildChart(item)
      }
    }
  }

  async function loadSavedCharts() {
    const saved = await api.listCharts()
    charts = []
    for (const item of saved) {
      const cfg = typeof item.config === 'string' ? JSON.parse(item.config) : (item.config || {})
      const topic = topics.find(t => t.topic === cfg.topic)
      const chart = {
        id: item.id,
        topic: cfg.topic,
        field: cfg.field,
        isJson: topic ? topic.is_json : true,
        agg: cfg.agg || 'avg',
        interval: cfg.interval || 'minute',
        fromTs: cfg.fromTs || '',
        toTs: cfg.toTs || '',
        showPoints: cfg.showPoints !== false,
        label: cfg.label || (isAggEnabled(cfg.agg) ? `${cfg.field} (${cfg.agg})` : `${cfg.field} (raw)`),
        canvas: null,
        chart: null,
        menuOpen: false,
        updating: false
      }
      charts = [...charts, chart]
      await tick()
      await buildChart(chart)
    }
  }

  function updateFields() {
    const topic = topics.find(t => t.topic === selectedTopic)
    fields = topic ? topic.fields : []
    selectedField = fields[0] || ''
  }

  function valueFromRow(row, field, isJson) {
    if (isJson) return row[field]
    return row.value_float ?? row.value_int ?? row.value_bool ?? row.value_text ?? row.value_json
  }

  async function buildChart(item) {
    if (item.updating) return
    item.updating = true
    error = ''
    try {
      const params = {
        topic: item.topic,
        fields: item.field,
        from_ts: item.fromTs || undefined,
        to_ts: item.toTs || undefined
      }
      if (isAggEnabled(item.agg)) {
        params.agg = item.agg
        params.interval = item.interval
      } else {
        params.order = 'desc'
        params.limit = 5000
      }

      const data = await api.history(params)
      const rows = data.rows || []

      const labels = isAggEnabled(item.agg)
        ? rows.map(r => r.bucket)
        : rows.map(r => r.ts).reverse()

      const values = isAggEnabled(item.agg)
        ? rows.map(r => (item.isJson ? r[item.field] : r.value))
        : rows.map(r => valueFromRow(r, item.field, item.isJson)).reverse()

      await tick()
      if (item.chart) {
        item.chart.data.labels = labels
        item.chart.data.datasets[0].data = values
        item.chart.data.datasets[0].pointRadius = item.showPoints ? 3 : 0
        item.chart.data.datasets[0].pointHoverRadius = item.showPoints ? 4 : 0
        item.chart.update('none')
      } else {
        item.chart = new Chart(item.canvas, {
          type: 'line',
          data: {
            labels,
            datasets: [
              {
                label: item.label,
                data: values,
                borderColor: '#111827',
                backgroundColor: 'rgba(17,24,39,0.1)',
                tension: 0.2,
                pointRadius: item.showPoints ? 3 : 0,
                pointHoverRadius: item.showPoints ? 4 : 0
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false
          }
        })
      }
    } catch (err) {
      error = err.message
    } finally {
      item.updating = false
    }
  }

  async function addChart() {
    if (!selectedTopic || !selectedField) return
    const topic = topics.find(t => t.topic === selectedTopic)
    const config = {
      topic: selectedTopic,
      field: selectedField,
      agg,
      interval,
      fromTs,
      toTs,
      showPoints,
      label: isAggEnabled(agg) ? `${selectedField} (${agg})` : `${selectedField} (raw)`
    }
    const saved = await api.createChart({ name: config.label, config })
    const item = {
      id: saved.id,
      topic: config.topic,
      field: config.field,
      isJson: topic ? topic.is_json : true,
      agg: config.agg,
      interval: config.interval,
      fromTs: config.fromTs,
      toTs: config.toTs,
      showPoints: config.showPoints,
      label: config.label,
      canvas: null,
      chart: null,
      menuOpen: false,
      updating: false
    }
    charts = [...charts, item]
    await tick()
    await buildChart(item)
  }

  async function removeChart(id) {
    const item = charts.find(c => c.id === id)
    if (item?.chart) item.chart.destroy()
    charts = charts.filter(c => c.id !== id)
    await api.deleteChart(id)
  }

  async function clearCharts() {
    for (const item of charts) {
      if (item.chart) item.chart.destroy()
      await api.deleteChart(item.id)
    }
    charts = []
  }

  async function togglePoints(item) {
    item.showPoints = !item.showPoints
    item.menuOpen = false
    const config = {
      topic: item.topic,
      field: item.field,
      agg: item.agg,
      interval: item.interval,
      fromTs: item.fromTs,
      toTs: item.toTs,
      showPoints: item.showPoints,
      label: item.label
    }
    await api.updateChart(item.id, { name: item.label, config })
    charts = [...charts]
    await buildChart(item)
  }

  function toggleMenu(item) {
    item.menuOpen = !item.menuOpen
    charts = [...charts]
  }
</script>

<section class="card">
  <h2>Графики</h2>
  <div class="filters">
    <div>
      <label>Топик</label>
      <select bind:value={selectedTopic} on:change={updateFields}>
        {#each topics as t}
          <option value={t.topic}>{t.topic}</option>
        {/each}
      </select>
    </div>
    <div>
      <label>Поле</label>
      <select bind:value={selectedField}>
        {#each fields as field}
          <option value={field}>{field}</option>
        {/each}
      </select>
    </div>
    <div>
      <label>Агрегация</label>
      <select bind:value={agg}>
        <option value="none">Выключена</option>
        <option value="avg">avg</option>
        <option value="min">min</option>
        <option value="max">max</option>
      </select>
    </div>
    {#if isAggEnabled(agg)}
      <div>
        <label>Интервал</label>
        <select bind:value={interval}>
          <option value="minute">minute</option>
          <option value="hour">hour</option>
          <option value="day">day</option>
        </select>
      </div>
    {/if}
    <div>
      <label>С</label>
      <input type="datetime-local" bind:value={fromTs} />
    </div>
    <div>
      <label>По</label>
      <input type="datetime-local" bind:value={toTs} />
    </div>
    <div class="actions">
      <button on:click={addChart}>Добавить график</button>
      <button class="ghost" on:click={clearCharts}>Очистить</button>
    </div>
  </div>

  {#if error}
    <div class="error">{error}</div>
  {/if}
</section>

<div class="grid">
  {#each charts as item}
    <section class="chart-card">
      <div class="chart-head">
        <div>
          <div class="title">{item.topic}</div>
          <div class="subtitle">{item.label}</div>
        </div>
        <div class="actions-right">
          <div class="menu">
            <button class="ghost" on:click={() => toggleMenu(item)}>...</button>
            {#if item.menuOpen}
              <div class="menu-panel">
                <label>
                  <input type="checkbox" checked={item.showPoints} on:change={() => togglePoints(item)} />
                  Показывать точки
                </label>
              </div>
            {/if}
          </div>
          <button class="ghost" on:click={() => removeChart(item.id)}>Удалить</button>
        </div>
      </div>
      <div class="chart-area">
        <canvas bind:this={item.canvas}></canvas>
      </div>
    </section>
  {/each}
</div>

<style>
  .card {
    background: #ffffff;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 6px 16px rgba(0,0,0,0.06);
  }

  .filters {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    margin-bottom: 16px;
    align-items: end;
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
    background: #111827;
    color: white;
    border: none;
    padding: 10px 12px;
    border-radius: 8px;
    cursor: pointer;
  }

  .ghost {
    background: transparent;
    color: #111827;
    border: 1px solid #e5e7eb;
  }

  .actions {
    display: flex;
    gap: 8px;
  }

  .error {
    color: #b91c1c;
    margin-bottom: 8px;
  }

  .grid {
    margin-top: 16px;
    display: grid;
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .chart-card {
    background: #ffffff;
    padding: 16px;
    border-radius: 12px;
    box-shadow: 0 6px 16px rgba(0,0,0,0.06);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .chart-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
  }

  .actions-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .title {
    font-weight: 600;
  }

  .subtitle {
    font-size: 12px;
    color: #6b7280;
  }

  .chart-area {
    height: 240px;
  }

  .menu {
    position: relative;
  }

  .menu-panel {
    position: absolute;
    right: 0;
    top: 36px;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 10px 12px;
    box-shadow: 0 8px 20px rgba(0,0,0,0.08);
    min-width: 160px;
    z-index: 5;
  }
</style>