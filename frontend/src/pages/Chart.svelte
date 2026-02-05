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
    let addMenuOpen = false
    let modalOpen = false
    let modalType = 'single'
    let modalTopic = ''
    let modalField = ''
    let modalFields = []
    let modalSelectedFields = []
    let modalFormula = ''
    let modalFormulaFields = ''
    let modalAgg = 'avg'
    let modalInterval = 'minute'
    let modalFromTs = ''
    let modalToTs = ''
    let modalShowPoints = true
    let modalError = ''
    let modalFormulaError = ''
    let modalEditingId = null

    let charts = []
    let nextId = 1
    let refreshTimer = null
    const refreshMs = 5000
    let dragId = null
    let resizeState = null
    const palette = ['#111827', '#2563eb', '#16a34a', '#f97316', '#dc2626']

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

    function normalizeChannels(channels) {
        const normalized = []
        if (!Array.isArray(channels)) return normalized
        channels.forEach((channel, index) => {
            const field = typeof channel === 'string' ? channel : channel.field
            if (!field) return
            const axis = channel.axis || (index === 0 ? 'y' : `y${index}`)
            const label = channel.label || field
            normalized.push({field, axis, label})
        })
        return normalized
    }

    function getTopicByName(name) {
        return topics.find(t => t.topic === name)
    }

    function getFieldsForTopic(name) {
        const topic = getTopicByName(name)
        return topic ? topic.fields : []
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
            const topic = getTopicByName(cfg.topic)
            const normalizedAgg = cfg.agg === 'none' ? 'off' : (cfg.agg || 'avg')
            const type = cfg.type || 'single'
            const channels = normalizeChannels(cfg.channels || [])
            const formula = cfg.formula || ''
            const formulaFields = Array.isArray(cfg.fields) ? cfg.fields : []
            const order = Number.isFinite(cfg.order) ? cfg.order : index
            const chart = {
                id: item.id,
                type,
                topic: cfg.topic,
                field: cfg.field,
                channels,
                formula,
                fields: formulaFields,
                isJson: topic ? topic.is_json : true,
                agg: normalizedAgg,
                interval: cfg.interval || 'minute',
                fromTs: cfg.fromTs || '',
                toTs: cfg.toTs || '',
                showPoints: cfg.showPoints !== false,
                label: cfg.label || (
                    type === 'multi'
                        ? `${cfg.topic} (multi)`
                        : type === 'formula'
                            ? (cfg.formula || 'formula')
                            : (isAggEnabled(normalizedAgg) ? `${cfg.field} (${normalizedAgg})` : `${cfg.field} (raw)`)
                ),
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
        fields = getFieldsForTopic(selectedTopic)
        selectedField = fields[0] || ''
    }

    function toggleAddMenu() {
        addMenuOpen = !addMenuOpen
    }

    function openAddModal(type) {
        modalEditingId = null
        modalType = type
        modalOpen = true
        addMenuOpen = false
        modalError = ''
        modalFormulaError = ''
        modalTopic = selectedTopic || (topics[0]?.topic || '')
        modalFields = getFieldsForTopic(modalTopic)
        modalField = modalFields[0] || ''
        modalSelectedFields = modalFields.slice(0, 2)
        modalFormulaFields = modalSelectedFields.join(',')
        modalFormula = ''
        modalAgg = agg
        modalInterval = interval
        modalFromTs = fromTs
        modalToTs = toTs
        modalShowPoints = showPoints
        if (modalType === 'formula') {
            validateFormulaInput()
        }
    }

    function closeModal() {
        modalOpen = false
        modalError = ''
        modalFormulaError = ''
    }

    function openEditModal(item) {
        item.menuOpen = false
        modalEditingId = item.id
        modalType = item.type || 'single'
        modalOpen = true
        addMenuOpen = false
        modalError = ''
        modalFormulaError = ''
        modalTopic = item.topic
        modalFields = getFieldsForTopic(modalTopic)
        modalField = item.field || modalFields[0] || ''
        modalSelectedFields = (item.channels || []).map(channel => channel.field)
        modalFormulaFields = (item.fields || []).join(',')
        modalFormula = item.formula || ''
        modalAgg = item.agg
        modalInterval = item.interval
        modalFromTs = item.fromTs || ''
        modalToTs = item.toTs || ''
        modalShowPoints = item.showPoints !== false
        if (modalType === 'formula') {
            validateFormulaInput()
        }
    }

    function updateModalFields() {
        modalFields = getFieldsForTopic(modalTopic)
        if (!modalFields.includes(modalField)) {
            modalField = modalFields[0] || ''
        }
        modalSelectedFields = modalSelectedFields.filter(field => modalFields.includes(field))
        if (!modalSelectedFields.length && modalFields.length) {
            modalSelectedFields = modalFields.slice(0, 2)
        }
        if (modalType === 'formula' && !modalFormulaFields.trim()) {
            modalFormulaFields = modalSelectedFields.join(',')
        }
        if (modalType === 'formula') {
            validateFormulaInput()
        }
    }

    function toggleModalField(field) {
        if (modalSelectedFields.includes(field)) {
            modalSelectedFields = modalSelectedFields.filter(value => value !== field)
        } else if (modalSelectedFields.length < 5) {
            modalSelectedFields = [...modalSelectedFields, field]
        }
    }

    function parseFieldList(text) {
        return text
            .split(',')
            .map(item => item.trim())
            .filter(Boolean)
    }

    function validateFormulaInput() {
        modalFormulaError = ''
        const fieldsList = parseFieldList(modalFormulaFields)
        if (!fieldsList.length) {
            modalFormulaError = 'Fields required'
            return
        }
        const invalidFields = fieldsList.filter(field => !modalFields.includes(field))
        if (invalidFields.length) {
            modalFormulaError = `Unknown fields: ${invalidFields.join(', ')}`
            return
        }
        const formula = modalFormula.trim()
        if (!formula) {
            modalFormulaError = 'Formula required'
            return
        }
        if (!/^[0-9A-Za-z_+\-*/().\s]+$/.test(formula)) {
            modalFormulaError = 'Formula contains invalid characters'
            return
        }
        try {
            buildFormulaEvaluator(fieldsList, formula)
        } catch (err) {
            modalFormulaError = err.message || 'Invalid formula'
        }
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

    function buildScales(axisIds, tickCallback, axisColors = {}) {
        const scales = {
            x: {
                ticks: {
                    callback: tickCallback
                }
            }
        }
        const ids = axisIds.includes('y') ? ['y', ...axisIds.filter(id => id !== 'y')] : axisIds
        ids.forEach((id, index) => {
            scales[id] = {
                type: 'linear',
                position: 'left',
                offset: index > 0,
                ticks: {
                    callback: formatNumber,
                    color: axisColors[id] || '#111827'
                }
            }
        })
        return scales
    }

    function bucketDate(value, interval) {
        const d = new Date(value)
        if (Number.isNaN(d.getTime())) return null
        const result = new Date(d)
        if (interval === 'day') {
            result.setHours(0, 0, 0, 0)
        } else if (interval === 'hour') {
            result.setMinutes(0, 0, 0)
        } else if (interval === 'minute') {
            result.setSeconds(0, 0)
        } else if (interval === 'second') {
            result.setMilliseconds(0)
        }
        return result
    }

    function aggregateSeries(labels, values, interval, aggMode) {
        const buckets = new Map()
        labels.forEach((label, index) => {
            const value = values[index]
            if (value === null || value === undefined || !Number.isFinite(value)) return
            const bucket = bucketDate(label, interval)
            if (!bucket) return
            const key = bucket.toISOString()
            if (!buckets.has(key)) {
                buckets.set(key, {ts: bucket, values: []})
            }
            buckets.get(key).values.push(value)
        })
        const sorted = Array.from(buckets.values()).sort((a, b) => a.ts - b.ts)
        const outLabels = []
        const outValues = []
        sorted.forEach((entry) => {
            if (!entry.values.length) return
            let value = null
            if (aggMode === 'min') value = Math.min(...entry.values)
            if (aggMode === 'max') value = Math.max(...entry.values)
            if (aggMode === 'avg') value = entry.values.reduce((sum, v) => sum + v, 0) / entry.values.length
            if (value === null) return
            outLabels.push(entry.ts.toISOString())
            outValues.push(value)
        })
        return {labels: outLabels, values: outValues}
    }

    function buildFormulaEvaluator(fields, formula) {
        const tokens = formula.match(/[A-Za-z_][A-Za-z0-9_]*/g) || []
        for (const token of tokens) {
            if (!fields.includes(token)) {
                throw new Error(`Unknown field in formula: ${token}`)
            }
        }
        return new Function(...fields, `return ${formula}`)
    }

    function buildConfig(item) {
        const base = {
            type: item.type || 'single',
            topic: item.topic,
            agg: item.agg,
            interval: item.interval,
            fromTs: item.fromTs,
            toTs: item.toTs,
            showPoints: item.showPoints,
            label: item.label,
            order: item.order,
            height: item.height
        }
        if ((item.type || 'single') === 'multi') {
            base.channels = item.channels
        } else if ((item.type || 'single') === 'formula') {
            base.formula = item.formula
            base.fields = item.fields
        } else {
            base.field = item.field
        }
        return base
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
            const type = item.type || 'single'
            let labels = []
            let datasets = []

            if (type === 'single') {
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
                labels = isAggEnabled(item.agg)
                    ? rows.map(r => r.bucket)
                    : rows.map(r => r.ts).reverse()
                const values = isAggEnabled(item.agg)
                    ? rows.map(r => (item.isJson ? r[item.field] : r.value))
                    : rows.map(r => valueFromRow(r, item.field, item.isJson)).reverse()
                datasets = [
                    {
                        label: item.label,
                        data: values,
                        borderColor: palette[0],
                        backgroundColor: 'rgba(17,24,39,0.1)',
                        tension: 0.2,
                        pointRadius: item.showPoints ? 3 : 0,
                        pointHoverRadius: item.showPoints ? 4 : 4,
                        pointHitRadius: item.showPoints ? 3 : 10,
                        yAxisID: 'y'
                    }
                ]
            } else if (type === 'multi') {
                const fieldsList = item.channels.map(ch => ch.field)
                const params = {
                    topic: item.topic,
                    fields: fieldsList.join(','),
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
                labels = isAggEnabled(item.agg)
                    ? rows.map(r => r.bucket)
                    : rows.map(r => r.ts).reverse()
                datasets = item.channels.map((channel, index) => ({
                    label: channel.label || channel.field,
                    data: isAggEnabled(item.agg)
                        ? rows.map(r => r[channel.field])
                        : rows.map(r => valueFromRow(r, channel.field, true)).reverse(),
                    borderColor: palette[index % palette.length],
                    backgroundColor: 'rgba(17,24,39,0.1)',
                    tension: 0.2,
                    pointRadius: item.showPoints ? 3 : 0,
                    pointHoverRadius: item.showPoints ? 4 : 4,
                    pointHitRadius: item.showPoints ? 3 : 10,
                    yAxisID: channel.axis || (index === 0 ? 'y' : `y${index}`)
                }))
            } else if (type === 'formula') {
                if (!item.formula || !item.fields || !item.fields.length) {
                    throw new Error('Formula config is empty')
                }
                const params = {
                    topic: item.topic,
                    fields: item.fields.join(','),
                    from_ts: item.fromTs || undefined,
                    to_ts: item.toTs || undefined,
                    order: 'desc',
                    limit: 5000
                }
                const data = await api.history(params)
                const rows = data.rows || []
                const evaluator = buildFormulaEvaluator(item.fields, item.formula)
                const rawLabels = rows.map(r => r.ts).reverse()
                const rawValues = []
                const rawFilteredLabels = []
                let formulaError = ''
                rows.slice().reverse().forEach((row, index) => {
                    const values = item.fields.map(name => row[name])
                    if (values.some(value => value === null || value === undefined)) return
                    const numericValues = values.map(Number)
                    if (numericValues.some(value => !Number.isFinite(value))) return
                    let result
                    try {
                        result = evaluator(...numericValues)
                    } catch (err) {
                        formulaError = 'Formula evaluation error'
                        return
                    }
                    if (!Number.isFinite(result)) {
                        formulaError = 'Division by zero or invalid value'
                        return
                    }
                    rawValues.push(result)
                    rawFilteredLabels.push(rawLabels[index])
                })
                if (formulaError) {
                    error = formulaError
                }
                if (isAggEnabled(item.agg)) {
                    const aggregated = aggregateSeries(rawFilteredLabels, rawValues, item.interval, item.agg)
                    labels = aggregated.labels
                    datasets = [
                        {
                            label: item.label,
                            data: aggregated.values,
                            borderColor: palette[0],
                            backgroundColor: 'rgba(17,24,39,0.1)',
                            tension: 0.2,
                            pointRadius: item.showPoints ? 3 : 0,
                            pointHoverRadius: item.showPoints ? 4 : 4,
                            pointHitRadius: item.showPoints ? 3 : 10,
                            yAxisID: 'y'
                        }
                    ]
                } else {
                    labels = rawFilteredLabels
                    datasets = [
                        {
                            label: item.label,
                            data: rawValues,
                            borderColor: palette[0],
                            backgroundColor: 'rgba(17,24,39,0.1)',
                            tension: 0.2,
                            pointRadius: item.showPoints ? 3 : 0,
                            pointHoverRadius: item.showPoints ? 4 : 4,
                            pointHitRadius: item.showPoints ? 3 : 10,
                            yAxisID: 'y'
                        }
                    ]
                }
            }

            if (!datasets.length) {
                throw new Error('No data to display')
            }

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

            const axisIds = Array.from(new Set(datasets.map(dataset => dataset.yAxisID || 'y')))
            const axisColors = {}
            datasets.forEach((dataset) => {
                const axis = dataset.yAxisID || 'y'
                if (!axisColors[axis]) {
                    axisColors[axis] = dataset.borderColor || '#111827'
                }
            })
            const scales = buildScales(axisIds, tickCallback, axisColors)

            await tick()
            if (item.chart) {
                item.chart.data.labels = labels
                item.chart.data.datasets = datasets
                item.chart.options.scales = scales
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
                        datasets
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: {
                            mode: 'nearest',
                            intersect: false
                        },
                        scales,
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

    async function addChartFromModal() {
        modalError = ''
        if (modalType === 'formula') {
            validateFormulaInput()
            if (modalFormulaError) return
        }
        if (!modalTopic) {
            modalError = 'Topic required'
            return
        }
        const topic = getTopicByName(modalTopic)
        if ((modalType === 'multi' || modalType === 'formula') && (!topic || !topic.is_json)) {
            modalError = 'Only JSON topics supported'
            return
        }
        if (modalType === 'single') {
            if (!modalField) {
                modalError = 'Field required'
                return
            }
            const config = {
                type: 'single',
                topic: modalTopic,
                field: modalField,
                agg: modalAgg,
                interval: modalInterval,
                fromTs: modalFromTs,
                toTs: modalToTs,
                showPoints: modalShowPoints,
                label: isAggEnabled(modalAgg) ? `${modalField} (${modalAgg})` : `${modalField} (raw)`,
                order: charts.length,
                height: 240
            }
            if (modalEditingId) {
                await updateChartFromModal(config, topic)
            } else {
                await createChartItem(config, topic)
            }
        } else if (modalType === 'multi') {
            if (!modalSelectedFields.length) {
                modalError = 'Select up to 5 fields'
                return
            }
            const channels = modalSelectedFields.slice(0, 5).map((field, index) => ({
                field,
                axis: index === 0 ? 'y' : `y${index}`,
                label: field
            }))
            const config = {
                type: 'multi',
                topic: modalTopic,
                channels,
                agg: modalAgg,
                interval: modalInterval,
                fromTs: modalFromTs,
                toTs: modalToTs,
                showPoints: modalShowPoints,
                label: `${modalTopic} (multi)`,
                order: charts.length,
                height: 240
            }
            if (modalEditingId) {
                await updateChartFromModal(config, topic)
            } else {
                await createChartItem(config, topic)
            }
        } else if (modalType === 'formula') {
            const fieldsList = parseFieldList(modalFormulaFields)
            if (!fieldsList.length) {
                modalError = 'Fields required'
                return
            }
            const invalidFields = fieldsList.filter(field => !modalFields.includes(field))
            if (invalidFields.length) {
                modalError = `Unknown fields: ${invalidFields.join(', ')}`
                return
            }
            if (!modalFormula.trim()) {
                modalError = 'Formula required'
                return
            }
            const config = {
                type: 'formula',
                topic: modalTopic,
                fields: fieldsList,
                formula: modalFormula.trim(),
                agg: modalAgg,
                interval: modalInterval,
                fromTs: modalFromTs,
                toTs: modalToTs,
                showPoints: modalShowPoints,
                label: modalFormula.trim(),
                order: charts.length,
                height: 240
            }
            if (modalEditingId) {
                await updateChartFromModal(config, topic)
            } else {
                await createChartItem(config, topic)
            }
        }
    }

    async function updateChartFromModal(config, topic) {
        const item = charts.find(c => c.id === modalEditingId)
        if (!item) return
        item.type = config.type || 'single'
        item.topic = config.topic
        item.field = config.field
        item.channels = normalizeChannels(config.channels || [])
        item.fields = Array.isArray(config.fields) ? config.fields : []
        item.formula = config.formula || ''
        item.isJson = topic ? topic.is_json : true
        item.agg = config.agg
        item.interval = config.interval
        item.fromTs = config.fromTs
        item.toTs = config.toTs
        item.showPoints = config.showPoints
        item.label = config.label
        if (item.chart) {
            item.chart.destroy()
            item.chart = null
        }
        await updateChartConfig(item)
        closeModal()
    }

    async function createChartItem(config, topic) {
        const saved = await api.createChart({name: config.label, config})
        const item = {
            id: saved.id,
            type: config.type || 'single',
            topic: config.topic,
            field: config.field,
            channels: normalizeChannels(config.channels || []),
            formula: config.formula || '',
            fields: Array.isArray(config.fields) ? config.fields : [],
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
        closeModal()
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
        <div class="actions">
            <div class="add-menu">
                <button on:click={toggleAddMenu}>Добавить график</button>
                {#if addMenuOpen}
                    <div class="add-menu-panel">
                        <button class="ghost" on:click={() => openAddModal('single')}>Обычный график</button>
                        <button class="ghost" on:click={() => openAddModal('multi')}>Многоканальный график</button>
                        <button class="ghost" on:click={() => openAddModal('formula')}>График по формуле</button>
                    </div>
                {/if}
            </div>
            <button class="ghost" on:click={clearCharts}>Очистить</button>
        </div>
    </div>

    {#if error}
        <div class="error">{error}</div>
    {/if}

    {#if modalOpen}
        <div class="modal-backdrop" on:click={closeModal}>
            <div class="modal" on:click|stopPropagation>
                <div class="modal-header">
                    <h3>Добавить график</h3>
                    <button class="ghost" on:click={closeModal}>×</button>
                </div>
                <div class="modal-grid">
                    <div>
                        <label>Тип</label>
                        <div class="modal-type">{modalType}</div>
                    </div>
                    <div>
                        <label>Топик</label>
                        <select bind:value={modalTopic} on:change={updateModalFields}>
                            {#each topics as t}
                                <option value={t.topic}>{t.topic}</option>
                            {/each}
                        </select>
                    </div>
                    {#if modalType === 'single'}
                        <div>
                            <label>Поле</label>
                            <select bind:value={modalField}>
                                {#each modalFields as field}
                                    <option value={field}>{field}</option>
                                {/each}
                            </select>
                        </div>
                    {/if}
                    {#if modalType === 'multi'}
                        <div class="modal-span">
                            <label>Поля (до 5)</label>
                            <div class="field-grid">
                                {#each modalFields as field}
                                    <label class="field-option">
                                        <input
                                            type="checkbox"
                                            checked={modalSelectedFields.includes(field)}
                                            on:change={() => toggleModalField(field)}
                                        />
                                        {field}
                                    </label>
                                {/each}
                            </div>
                        </div>
                    {/if}
                    {#if modalType === 'formula'}
                        <div class="modal-span">
                            <label>Поля (через запятую)</label>
                            <input
                                type="text"
                                bind:value={modalFormulaFields}
                                class:input-error={!!modalFormulaError}
                                on:input={validateFormulaInput}
                            />
                        </div>
                        <div class="modal-span">
                            <label>Формула (+ - * /)</label>
                            <input
                                type="text"
                                bind:value={modalFormula}
                                class:input-error={!!modalFormulaError}
                                on:input={validateFormulaInput}
                            />
                        </div>
                        <div class="modal-span hint">
                            Доступные поля: {modalFields.join(', ')}
                        </div>
                        {#if modalFormulaError}
                            <div class="modal-span error-text">{modalFormulaError}</div>
                        {/if}
                    {/if}
                    <div>
                        <label>Агрегация</label>
                        <select bind:value={modalAgg}>
                            <option value="off">off</option>
                            <option value="avg">avg</option>
                            <option value="min">min</option>
                            <option value="max">max</option>
                        </select>
                    </div>
                    {#if isAggEnabled(modalAgg)}
                        <div>
                            <label>Интервал</label>
                            <select bind:value={modalInterval}>
                                <option value="second">second</option>
                                <option value="minute">minute</option>
                                <option value="hour">hour</option>
                                <option value="day">day</option>
                            </select>
                        </div>
                    {/if}
                    <div>
                        <label>С</label>
                        <input type="datetime-local" bind:value={modalFromTs}/>
                    </div>
                    <div>
                        <label>По</label>
                        <input type="datetime-local" bind:value={modalToTs}/>
                    </div>
                    <div class="modal-span">
                        <label class="checkbox">
                            <input type="checkbox" bind:checked={modalShowPoints} />
                            Показывать точки
                        </label>
                    </div>
                </div>
                {#if modalError}
                    <div class="error">{modalError}</div>
                {/if}
                <div class="modal-actions">
                    <button on:click={addChartFromModal}>Создать</button>
                    <button class="ghost" on:click={closeModal}>Отмена</button>
                </div>
            </div>
        </div>
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
                                <button class="ghost" on:click={() => openEditModal(item)}>Редактировать</button>
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

    .add-menu {
        position: relative;
    }

    .add-menu-panel {
        position: absolute;
        top: 44px;
        left: 0;
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 8px;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
        display: grid;
        gap: 6px;
        z-index: 6;
        min-width: 220px;
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

    .modal-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(15, 23, 42, 0.4);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 30;
        padding: 20px;
    }

    .modal {
        background: #ffffff;
        border-radius: 12px;
        padding: 16px 18px;
        width: min(720px, 100%);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
        display: grid;
        gap: 12px;
    }

    .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .modal-grid {
        display: grid;
        gap: 12px;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }

    .modal-span {
        grid-column: 1 / -1;
    }

    .modal-actions {
        display: flex;
        gap: 8px;
        justify-content: flex-end;
    }

    .modal-type {
        padding: 8px 10px;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        background: #f9fafb;
        text-transform: uppercase;
        font-size: 12px;
        letter-spacing: 0.04em;
    }

    .field-grid {
        display: grid;
        gap: 6px;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    }

    .field-option {
        display: flex;
        gap: 8px;
        align-items: center;
        font-size: 13px;
    }

    .checkbox {
        display: flex;
        gap: 8px;
        align-items: center;
    }

    .hint {
        color: #6b7280;
        font-size: 12px;
    }

    .input-error {
        border-color: #dc2626;
        background: #fef2f2;
    }

    .error-text {
        color: #dc2626;
        font-size: 12px;
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
