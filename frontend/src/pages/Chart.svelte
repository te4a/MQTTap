<script>
    import {onMount, onDestroy, tick} from 'svelte'
    import {get} from 'svelte/store'
    import Chart from 'chart.js/auto'
    import {api} from '../lib.js'
    import ChartModal from '../components/ChartModal.svelte'
    import ChartCard from '../components/ChartCard.svelte'
    import {
        buildFormulaEvaluator,
        buildScales,
        formatNumber,
        makeLabelFormatter
    } from '../chart-utils.js'
    import {fetchChartSeries} from '../services/chart-data.js'
    import {lang, t} from '../i18n.js'

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
    let importInput
    let windowResizeHandler = null

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
        windowResizeHandler = () => {
            charts.forEach((item) => {
                if (item.chart) item.chart.resize()
            })
        }
        window.addEventListener('resize', windowResizeHandler)
    })

    onDestroy(() => {
        if (refreshTimer) clearInterval(refreshTimer)
        if (windowResizeHandler) {
            window.removeEventListener('resize', windowResizeHandler)
        }
    })

    function isAggEnabled(value) {
        return value && value !== 'off'
    }

    function tr(key) {
        return t(key, get(lang))
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
                        ? `${cfg.topic} (${tr('charts.multiLabel')})`
                        : type === 'formula'
                            ? (cfg.formula || tr('charts.formulaLabel'))
                            : (isAggEnabled(normalizedAgg) ? `${cfg.field} (${normalizedAgg})` : `${cfg.field} (${tr('charts.raw')})`)
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

    function triggerImport() {
        if (importInput) importInput.click()
    }

    async function handleImport(event) {
        error = ''
        const file = event.target.files?.[0]
        if (!file) return
        try {
            const text = await file.text()
            const raw = JSON.parse(text)
            const config = raw?.config || raw
            if (!config || !config.topic) {
                throw new Error(tr('errors.invalidChartJson'))
            }
            const topic = getTopicByName(config.topic)
            if (!topic) {
                throw new Error(tr('errors.unknownTopic'))
            }
            const type = config.type || 'single'
            const normalized = {
                type,
                topic: config.topic,
                agg: config.agg || 'avg',
                interval: config.interval || 'minute',
                fromTs: config.fromTs || '',
                toTs: config.toTs || '',
                showPoints: config.showPoints !== false,
                label: config.label || (type === 'single' ? `${config.field || tr('charts.field')} (${config.agg || 'avg'})` : (type === 'multi' ? `${config.topic} (${tr('charts.multiLabel')})` : (config.formula || tr('charts.formulaLabel')))),
                order: charts.length,
                height: Number.isFinite(config.height) ? config.height : 240
            }
            if (type === 'single') {
                if (!config.field) throw new Error(tr('errors.fieldRequired'))
                normalized.field = config.field
            } else if (type === 'multi') {
                const channels = normalizeChannels(config.channels || (config.fields || []))
                if (!channels.length) throw new Error(tr('errors.channelsRequired'))
                normalized.channels = channels.slice(0, 5)
            } else if (type === 'formula') {
                if (!config.formula || !Array.isArray(config.fields) || !config.fields.length) {
                    throw new Error(tr('errors.formulaRequired'))
                }
                normalized.formula = config.formula
                normalized.fields = config.fields
            }
            await createChartItem(normalized, topic)
        } catch (err) {
            error = err.message
        } finally {
            event.target.value = ''
        }
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

    function exportChart(item) {
        const config = buildConfig(item)
        const payload = {name: item.label, config}
        const blob = new Blob([JSON.stringify(payload, null, 2)], {type: 'application/json'})
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        const safeName = (item.label || 'chart').replace(/[^a-z0-9_-]+/gi, '_')
        link.href = url
        link.download = `${safeName}.json`
        document.body.appendChild(link)
        link.click()
        link.remove()
        URL.revokeObjectURL(url)
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
            modalFormulaError = tr('errors.formulaFieldsRequired')
            return
        }
        const invalidFields = fieldsList.filter(field => !modalFields.includes(field))
        if (invalidFields.length) {
            modalFormulaError = `${tr('errors.unknownFields')}: ${invalidFields.join(', ')}`
            return
        }
        const formula = modalFormula.trim()
        if (!formula) {
            modalFormulaError = tr('errors.formulaRequired')
            return
        }
        if (!/^[0-9A-Za-z_+\-*/().\s]+$/.test(formula)) {
            modalFormulaError = tr('errors.invalidFormulaChars')
            return
        }
        try {
            buildFormulaEvaluator(fieldsList, formula)
        } catch (err) {
            modalFormulaError = tr('errors.invalidFormula')
        }
    }

    function valueFromRow(row, field, isJson) {
        if (isJson) return row[field]
        return row.value_float ?? row.value_int ?? row.value_bool ?? row.value_text ?? row.value_json
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

    function formatValue(value) {
        return formatNumber(value, floatPrecision)
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
            const {labels, datasets, error: seriesError} = await fetchChartSeries(
                api,
                item,
                isAggEnabled,
                valueFromRow
            )
            if (seriesError) {
                error = seriesError.startsWith('errors.') ? tr(seriesError) : seriesError
            }

            if (!datasets.length) {
                throw new Error(tr('errors.noData'))
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
            const scales = buildScales(axisIds, tickCallback, axisColors, formatValue)

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
                            label: (ctx) => formatValue(ctx.parsed.y)
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
                                    label: (ctx) => formatValue(ctx.parsed.y)
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
            modalError = tr('errors.required')
            return
        }
        const topic = getTopicByName(modalTopic)
        if ((modalType === 'multi' || modalType === 'formula') && (!topic || !topic.is_json)) {
            modalError = tr('errors.onlyJsonTopics')
            return
        }
        if (modalType === 'single') {
            if (!modalField) {
                modalError = tr('errors.fieldRequired')
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
                label: isAggEnabled(modalAgg) ? `${modalField} (${modalAgg})` : `${modalField} (${tr('charts.raw')})`,
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
                modalError = tr('errors.selectUpToFields')
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
                label: `${modalTopic} (${tr('charts.multiLabel')})`,
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
                modalError = tr('errors.formulaFieldsRequired')
                return
            }
            const invalidFields = fieldsList.filter(field => !modalFields.includes(field))
            if (invalidFields.length) {
                modalError = `${tr('errors.unknownFields')}: ${invalidFields.join(', ')}`
                return
            }
            if (!modalFormula.trim()) {
                modalError = tr('errors.formulaRequired')
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
    <h2>{t('charts.title', $lang)}</h2>
    <div class="filters">
        <div class="actions">
            <div class="add-menu">
                <button on:click={toggleAddMenu}>{t('charts.add', $lang)}</button>
                {#if addMenuOpen}
                    <div class="add-menu-panel">
                        <button class="ghost" on:click={() => openAddModal('single')}>{t('charts.addSingle', $lang)}</button>
                        <button class="ghost" on:click={() => openAddModal('multi')}>{t('charts.addMulti', $lang)}</button>
                        <button class="ghost" on:click={() => openAddModal('formula')}>{t('charts.addFormula', $lang)}</button>
                        <button class="ghost" on:click={triggerImport}>{t('common.importJson', $lang)}</button>
                    </div>
                {/if}
            </div>
            <button class="ghost" on:click={clearCharts}>{t('common.clear', $lang)}</button>
        </div>
    </div>

    <input
        class="file-input"
        type="file"
        accept="application/json"
        bind:this={importInput}
        on:change={handleImport}
    />

    {#if error}
        <div class="error">{error}</div>
    {/if}

    <ChartModal
        open={modalOpen}
        modalType={modalType}
        {topics}
        modalFields={modalFields}
        modalSelectedFields={modalSelectedFields}
        modalError={modalError}
        modalFormulaError={modalFormulaError}
        title={modalEditingId ? t('charts.modalTitleEdit', $lang) : t('charts.modalTitleAdd', $lang)}
        submitLabel={modalEditingId ? t('charts.modalSubmitEdit', $lang) : t('charts.modalSubmitAdd', $lang)}
        bind:modalTopic
        bind:modalField
        bind:modalFormulaFields
        bind:modalFormula
        bind:modalAgg
        bind:modalInterval
        bind:modalFromTs
        bind:modalToTs
        bind:modalShowPoints
        {isAggEnabled}
        onClose={closeModal}
        onSubmit={addChartFromModal}
        onTopicChange={updateModalFields}
        onToggleField={toggleModalField}
        onValidateFormula={validateFormulaInput}
    />
</section>

<div class="grid">
    {#each charts as item (item.id)}
        <ChartCard
            {item}
            {dragId}
            {isAggEnabled}
            onDragStart={onDragStart}
            onDragOver={onDragOver}
            onDrop={onDrop}
            onDragEnd={onDragEnd}
            onToggleMenu={toggleMenu}
            onTogglePoints={togglePoints}
            onEdit={openEditModal}
            onExport={exportChart}
            onRemove={removeChart}
            onResizeStart={startResize}
            onUpdateConfig={updateChartConfig}
        />
    {/each}
</div>

<style>
    .filters {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
        align-items: end;
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
        margin-bottom: 8px;
    }

    .grid {
        margin-top: 16px;
        display: grid;
        grid-template-columns: 1fr;
        gap: 16px;
        min-width: 0;
    }

    .file-input {
        display: none;
    }

</style>
