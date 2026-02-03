<script>
  import { onMount, tick } from 'svelte'
  import Chart from 'chart.js/auto'
  import { api } from '../lib.js'

  let topics = []
  let selectedTopic = ''
  let fields = []
  let selectedField = ''
  let aggEnabled = true
  let agg = 'avg'
  let interval = 'minute'
  let fromTs = ''
  let toTs = ''
  let error = ''

  let charts = []
  let nextId = 1

  onMount(async () => {
    try {
      topics = await api.topics()
      if (topics.length) {
        selectedTopic = topics[0].topic
        updateFields()
      }
    } catch (err) {
      error = err.message
    }
  })

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
    error = ''
    try {
      const params = {
        topic: item.topic,
        fields: item.field,
        from_ts: item.fromTs || undefined,
        to_ts: item.toTs || undefined
      }
      if (item.aggEnabled) {
        params.agg = item.agg
        params.interval = item.interval
      } else {
        params.order = 'desc'
        params.limit = 5000
      }

      const data = await api.history(params)
      const rows = data.rows || []

      const labels = item.aggEnabled
        ? rows.map(r => r.bucket)
        : rows.map(r => r.ts).reverse()

      const values = item.aggEnabled
        ? rows.map(r => (item.isJson ? r[item.field] : r.value))
        : rows.map(r => valueFromRow(r, item.field, item.isJson)).reverse()

      await tick()
      if (item.chart) item.chart.destroy()
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
              tension: 0.2
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false
        }
      })
    } catch (err) {
      error = err.message
    }
  }

  async function addChart() {
    if (!selectedTopic || !selectedField) return
    const topic = topics.find(t => t.topic === selectedTopic)
    const item = {
      id: nextId++,
      topic: selectedTopic,
      field: selectedField,
      isJson: topic ? topic.is_json : true,
      aggEnabled,
      agg,
      interval,
      fromTs,
      toTs,
      label: aggEnabled ? `${selectedField} (${agg})` : `${selectedField} (raw)`,
      canvas: null,
      chart: null
    }
    charts = [...charts, item]
    await tick()
    await buildChart(item)
  }

  function removeChart(id) {
    const item = charts.find(c => c.id === id)
    if (item?.chart) item.chart.destroy()
    charts = charts.filter(c => c.id !== id)
  }

  function clearCharts() {
    charts.forEach(c => c.chart && c.chart.destroy())
    charts = []
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
    <div class="inline">
      <label>
        <input type="checkbox" bind:checked={aggEnabled} />
        Агрегация
      </label>
    </div>
    {#if aggEnabled}
      <div>
        <label>Агрегация</label>
        <select bind:value={agg}>
          <option value="avg">avg</option>
          <option value="min">min</option>
          <option value="max">max</option>
          <option value="sum">sum</option>
          <option value="count">count</option>
        </select>
      </div>
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
        <button class="ghost" on:click={() => removeChart(item.id)}>Удалить</button>
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

  .inline {
    display: flex;
    align-items: center;
    gap: 8px;
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
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
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
</style>