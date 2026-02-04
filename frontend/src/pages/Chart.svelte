<script>
    import {onMount, onDestroy, tick} from 'svelte'
    import Chart from 'chart.js/auto'
    import {api} from '../lib.js'

    let topics = []
    let selectedTopic = ''
    let fields = []
    let selectedField = ''
    let agg = 'avg'
    let interval = 'minute'
    let fromTs = ''
    let toTs = ''
    let showPoints = true
    let floatPrecision = 5
    let error = ''

    let charts = []
    let nextId = 1
    let refreshTimer = null
    const refreshMs = 5000
    let dragId = null
    let resizeState = null

    onMount(async () => {
        try {
            topics = await api.topics()
            const settings = await api.getPublicSettings()
            if (settings && settings.float_precision !== undefined) {
                floatPrecision = Number(settings.float_precision)
            }
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
        return value && value !== 'off'
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
        const loaded = []
        let index = 0
        for (const item of saved) {
            const cfg = typeof item.config === 'string' ? JSON.parse(item.config) : (item.config || {})
            const topic = topics.find(t => t.topic === cfg.topic)
            const normalizedAgg = cfg.agg === 'none' ? 'off' : (cfg.agg || 'avg')
            const order = Number.isFinite(cfg.order) ? cfg.order : index
            const chart = {
                id: item.id,
                topic: cfg.topic,
                field: cfg.field,
                isJson: topic ? topic.is_json : true,
                agg: normalizedAgg,
                interval: cfg.interval || 'minute',
                fromTs: cfg.fromTs || '',
                toTs: cfg.toTs || '',
                showPoints: cfg.showPoints !== false,
                label: cfg.label || (isAggEnabled(normalizedAgg) ? `${cfg.field} (${normalizedAgg})` : `${cfg.field} (raw)`),
                order,
                height: Number.isFinite(cfg.height) ? cfg.height : 240,
                canvas: null,
                chart: null,
                menuOpen: false,
                updating: false,
                fromInitialized: !!cfg.fromTs
            }
            loaded.push(chart)
            index += 1
        }
        charts = loaded.sort((a, b) => a.order - b.order)
        await tick()
        for (const chart of charts) {
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

    function makeLabelFormatter(labels) {
        const parsed = labels.map((value) => {
            const d = new Date(value)
            if (Number.isNaN(d.getTime())) return null
            return d
        })

        const first = parsed.find(d => d)
        const allSameYear = first ? parsed.every(d => d && d.getFullYear() === first.getFullYear()) : false
        const allSameMonth = first ? parsed.every(d => d && d.getMonth() === first.getMonth()) : false
        const allSameDate = first ? parsed.every(d => d && d.getDate() === first.getDate()) : false
        const allSameHour = first ? parsed.every(d => d && d.getHours() === first.getHours()) : false
        const allSameMinute = first ? parsed.every(d => d && d.getMinutes() === first.getMinutes()) : false
        const allSameSecond = first ? parsed.every(d => d && d.getSeconds() === first.getSeconds()) : false
        const allSameMillisecond = first ? parsed.every(d => d && d.getMilliseconds() === first.getMilliseconds()) : false

        function formatLabel(d) {
            if (!d) return ''
            const parts = [
                {same: allSameYear, value: d.getFullYear().toString(), sep: ''},
                {same: allSameMonth, value: (d.getMonth() + 1).toString().padStart(2, '0'), sep: '-'},
                {same: allSameDate, value: d.getDate().toString().padStart(2, '0'), sep: '-'},

                {same: allSameHour, value: d.getHours().toString().padStart(2, '0'), sep: ' '},
                {same: allSameMinute, value: d.getMinutes().toString().padStart(2, '0'), sep: ':'},
                {same: allSameSecond, value: d.getSeconds().toString().padStart(2, '0'), sep: ':'},
                {
                    same: allSameMillisecond,
                    value: Math.floor(d.getMilliseconds() / 10).toString().padStart(2, '0'),
                    sep: '.'
                },
            ]

            return parts
                .filter(p => !p.same)
                .map((p, i) => (i === 0 ? p.value : p.sep + p.value))
                .join('')
        }

        return {
            byIndex: (index) => {
                const d = parsed[index]
                return formatLabel(d) || String(labels[index])
            },
            byValue: (value) => {
                const d = new Date(value)
                if (Number.isNaN(d.getTime())) return String(value)
                return formatLabel(d)
            }
        }
    }

    function formatNumber(value) {
        if (value === null || value === undefined) return ''
        if (typeof value === 'number' && Number.isFinite(value)) {
            const digits = Number.isFinite(floatPrecision) ? Math.max(0, floatPrecision) : 5
            const factor = Math.pow(10, digits)
            const rounded = Math.round(value * factor) / factor
            return String(rounded)
        }
        return String(value)
    }

    function toLocalInput(value) {
        const d = new Date(value)
        if (Number.isNaN(d.getTime())) return ''
        const yyyy = d.getFullYear().toString().padStart(4, '0')
        const mm = (d.getMonth() + 1).toString().padStart(2, '0')
        const dd = d.getDate().toString().padStart(2, '0')
        const hh = d.getHours().toString().padStart(2, '0')
        const mi = d.getMinutes().toString().padStart(2, '0')
        return `${yyyy}-${mm}-${dd}T${hh}:${mi}`
    }

    function buildConfig(item) {
        return {
            topic: item.topic,
            field: item.field,
            agg: item.agg,
            interval: item.interval,
            fromTs: item.fromTs,
            toTs: item.toTs,
            showPoints: item.showPoints,
            label: item.label,
            order: item.order,
            height: item.height
        }
    }

    async function persistChart(item) {
        const config = buildConfig(item)
        await api.updateChart(item.id, {name: item.label, config})
    }

    async function updateChartConfig(item) {
        await persistChart(item)
        await buildChart(item)
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

            if (!item.fromTs && labels.length) {
                const earliest = labels[0]
                const localValue = toLocalInput(earliest)
                if (localValue) {
                    item.fromTs = localValue
                    if (!item.fromInitialized) {
                        item.fromInitialized = true
                        await persistChart(item)
                    }
                }
            }

            const labelFormatter = makeLabelFormatter(labels)
            const tickCallback = (value, index) => {
                const label = labelFormatter.byIndex(index)
                if (index === 0) return label
                const prevLabel = labelFormatter.byIndex(index - 1)
                return label === prevLabel ? '' : label
            }

            await tick()
            if (item.chart) {
                item.chart.data.labels = labels
                item.chart.data.datasets[0].data = values
                item.chart.data.datasets[0].pointRadius = item.showPoints ? 3 : 0
                item.chart.data.datasets[0].pointHoverRadius = item.showPoints ? 4 : 4
                item.chart.data.datasets[0].pointHitRadius = item.showPoints ? 3 : 10
                item.chart.options.scales = {
                    x: {
                        ticks: {
                            callback: tickCallback
                        }
                    },
                    y: {
                        ticks: {
                            callback: formatNumber
                        }
                    }
                }
                item.chart.options.interaction = {
                    mode: 'nearest',
                    intersect: false
                }
                item.chart.options.plugins = {
                    tooltip: {
                        callbacks: {
                            title: (items) => items.length ? labelFormatter.byValue(items[0].label) : '',
                            label: (ctx) => formatNumber(ctx.parsed.y)
                        }
                    }
                }
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
                                pointHoverRadius: item.showPoints ? 4 : 4,
                                pointHitRadius: item.showPoints ? 3 : 10
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: {
                            mode: 'nearest',
                            intersect: false
                        },
                        scales: {
                            x: {
                                ticks: {
                                    callback: tickCallback
                                }
                            },
                            y: {
                                ticks: {
                                    callback: formatNumber
                                }
                            }
                        },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    title: (items) => items.length ? labelFormatter.byValue(items[0].label) : '',
                                    label: (ctx) => formatNumber(ctx.parsed.y)
                                }
                            }
                        }
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
            label: isAggEnabled(agg) ? `${selectedField} (${agg})` : `${selectedField} (raw)`,
            order: charts.length,
            height: 240
        }
        const saved = await api.createChart({name: config.label, config})
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
            order: config.order,
            height: config.height,
            canvas: null,
            chart: null,
            menuOpen: false,
            updating: false,
            fromInitialized: !!config.fromTs
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

    async function togglePoints(item, event) {
        item.showPoints = event.target.checked
        item.menuOpen = false
        charts = [...charts]
        if (item.chart) {
            item.chart.destroy()
            item.chart = null
        }
        await updateChartConfig(item)
    }

    function toggleMenu(item) {
        item.menuOpen = !item.menuOpen
        charts = [...charts]
    }

    function onDragStart(item, event) {
        dragId = item.id
        if (event?.dataTransfer) {
            event.dataTransfer.effectAllowed = 'move'
            event.dataTransfer.setData('text/plain', String(item.id))
        }
    }

    function onDragOver(event) {
        event.preventDefault()
        if (event?.dataTransfer) {
            event.dataTransfer.dropEffect = 'move'
        }
    }

    async function onDrop(target, event) {
        event.preventDefault()
        const raw = event?.dataTransfer?.getData('text/plain')
        const droppedId = Number(raw || dragId)
        if (!droppedId || droppedId === target.id) return
        const fromIndex = charts.findIndex(c => c.id === droppedId)
        const toIndex = charts.findIndex(c => c.id === target.id)
        if (fromIndex < 0 || toIndex < 0) return
        const next = [...charts]
        const [moved] = next.splice(fromIndex, 1)
        next.splice(toIndex, 0, moved)
        let changed = false
        next.forEach((item, index) => {
            if (item.order !== index) {
                item.order = index
                changed = true
            }
        })
        charts = next
        if (changed) {
            for (const item of next) {
                await persistChart(item)
            }
        }
        dragId = null
    }

    function onDragEnd() {
        dragId = null
    }

    function clampHeight(value) {
        const maxHeight = typeof window !== 'undefined' ? window.innerHeight : 600
        return Math.max(200, Math.min(value, maxHeight))
    }

    function startResize(item, event) {
        event.preventDefault()
        resizeState = {
            id: item.id,
            startY: event.clientY,
            startHeight: item.height
        }
        window.addEventListener('mousemove', onResizeMove)
        window.addEventListener('mouseup', onResizeEnd)
    }

    function onResizeMove(event) {
        if (!resizeState) return
        const item = charts.find(c => c.id === resizeState.id)
        if (!item) return
        const nextHeight = clampHeight(resizeState.startHeight + (event.clientY - resizeState.startY))
        item.height = nextHeight
        charts = [...charts]
        if (item.chart) item.chart.resize()
    }

    async function onResizeEnd() {
        if (!resizeState) return
        const item = charts.find(c => c.id === resizeState.id)
        resizeState = null
        window.removeEventListener('mousemove', onResizeMove)
        window.removeEventListener('mouseup', onResizeEnd)
        if (item) {
            await persistChart(item)
        }
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
                <option value="off">off</option>
                <option value="avg">avg</option>
                <option value="min">min</option>
                <option value="max">max</option>
            </select>
        </div>
        {#if isAggEnabled(agg)}
            <div>
                <label>Интервал</label>
                <select bind:value={interval}>
                    <option value="second">second</option>
                    <option value="minute">minute</option>
                    <option value="hour">hour</option>
                    <option value="day">day</option>
                </select>
            </div>
        {/if}
        <div>
            <label>С</label>
            <input type="datetime-local" bind:value={fromTs}/>
        </div>
        <div>
            <label>По</label>
            <input type="datetime-local" bind:value={toTs}/>
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
    {#each charts as item (item.id)}
        <section
            class="chart-card"
            class:dragging={dragId === item.id}
            draggable="true"
            on:dragstart={(e) => onDragStart(item, e)}
            on:dragover={onDragOver}
            on:drop={(e) => onDrop(item, e)}
            on:dragend={onDragEnd}
        >
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
                                    <input type="checkbox" checked={item.showPoints}
                                           on:change={(e) => togglePoints(item, e)}/>
                                    Показывать точки
                                </label>
                                <div class="menu-section">
                                    <label>Агрегация</label>
                                    <select bind:value={item.agg} on:change={() => updateChartConfig(item)}>
                                        <option value="off">off</option>
                                        <option value="avg">avg</option>
                                        <option value="min">min</option>
                                        <option value="max">max</option>
                                    </select>
                                </div>
                                {#if isAggEnabled(item.agg)}
                                    <div class="menu-section">
                                        <label>Интервал</label>
                                        <select bind:value={item.interval} on:change={() => updateChartConfig(item)}>
                                            <option value="second">second</option>
                                            <option value="minute">minute</option>
                                            <option value="hour">hour</option>
                                            <option value="day">day</option>
                                        </select>
                                    </div>
                                {/if}
                                <div class="menu-section">
                                    <label>С</label>
                                    <input type="datetime-local" bind:value={item.fromTs} on:change={() => updateChartConfig(item)} />
                                </div>
                                <div class="menu-section">
                                    <label>По</label>
                                    <input type="datetime-local" bind:value={item.toTs} on:change={() => updateChartConfig(item)} />
                                </div>
                            </div>
                        {/if}
                    </div>
                    <button class="ghost" on:click={() => removeChart(item.id)}>Удалить</button>
                </div>
            </div>
            <div class="chart-area" style={`height: ${item.height}px`}>
                <canvas bind:this={item.canvas}></canvas>
            </div>
            <div class="resize-grip" on:mousedown={(e) => startResize(item, e)}></div>
        </section>
    {/each}
</div>

<style>
    .card {
        background: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.06);
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
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.06);
        display: flex;
        flex-direction: column;
        gap: 12px;
        position: relative;
    }

    .chart-card.dragging {
        opacity: 0.7;
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
        min-height: 200px;
    }

    .resize-grip {
        position: absolute;
        left: 0;
        right: 0;
        bottom: 0;
        height: 12px;
        cursor: ns-resize;
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
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
        min-width: 200px;
        z-index: 5;
        display: grid;
        gap: 8px;
    }

    .menu-section {
        display: grid;
        gap: 6px;
    }
</style>
