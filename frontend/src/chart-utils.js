export const palette = ['#111827', '#2563eb', '#16a34a', '#f97316', '#dc2626']

export function makeLabelFormatter(labels) {
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

    const rendered = parts
      .filter(p => !p.same)
      .map((p, i) => (i === 0 ? p.value : p.sep + p.value))
      .join('')
    const prefix = allSameHour && !allSameMinute ? ':' : ''
    const suffix = allSameMinute && !allSameSecond ? ':' : ''
    return `${prefix}${rendered}${suffix}`
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

export function formatNumber(value, precision) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'number' && Number.isFinite(value)) {
    const digits = Number.isFinite(precision) ? Math.max(0, precision) : 5
    const factor = Math.pow(10, digits)
    const rounded = Math.round(value * factor) / factor
    return String(rounded)
  }
  return String(value)
}

export function normalizeNumericValue(value) {
  if (value === null || value === undefined) return null
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null
  }
  if (typeof value === 'boolean') {
    return value ? 1 : 0
  }
  if (typeof value === 'string') {
    const normalized = value.trim().replace(',', '.')
    if (!normalized) return null
    const direct = Number(normalized)
    if (Number.isFinite(direct)) return direct
    const match = normalized.match(/[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?/)
    if (!match) return null
    const parsed = Number(match[0])
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

export function buildScales(axisIds, tickCallback, axisColors = {}, formatNumberFn = (v) => v) {
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
        callback: formatNumberFn,
        color: axisColors[id] || '#111827'
      }
    }
  })
  return scales
}

function bucketDate(value, interval, intervalCount = 1) {
  if (!interval) return null
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return null
  if (intervalCount > 1) {
    const stepMs = (INTERVAL_MS[interval] || 0) * intervalCount
    if (!stepMs) return null
    const bucket = Math.floor(d.getTime() / stepMs) * stepMs
    return new Date(bucket)
  }
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

export function aggregateSeries(labels, values, interval, aggMode, intervalCount = 1) {
  const buckets = new Map()
  labels.forEach((label, index) => {
    const value = values[index]
    if (value === null || value === undefined || !Number.isFinite(value)) return
    const bucket = bucketDate(label, interval, intervalCount)
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

export function buildFormulaEvaluator(fields, formula) {
  const tokens = formula.match(/[A-Za-z_][A-Za-z0-9_]*/g) || []
  for (const token of tokens) {
    if (!fields.includes(token)) {
      throw new Error(`Unknown field in formula: ${token}`)
    }
  }
  return new Function(...fields, `return ${formula}`)
}

const INTERVAL_MS = {
  second: 1000,
  minute: 60000,
  hour: 3600000,
  day: 86400000
}

function median(values) {
  if (!values.length) return null
  const sorted = values.slice().sort((a, b) => a - b)
  return sorted[Math.floor(sorted.length / 2)]
}

export function alignTimeSeries(labels, datasets, interval, enabled, maxPoints = 5000, intervalCount = 1) {
  if (!enabled || labels.length < 2) return {labels, datasets, truncated: false}
  const times = labels.map((value) => {
    const d = new Date(value)
    return Number.isNaN(d.getTime()) ? null : d.getTime()
  })
  if (times.some(value => value === null)) return {labels, datasets, truncated: false}
  const baseStep = interval ? INTERVAL_MS[interval] : null
  let stepMs = baseStep ? baseStep * Math.max(1, intervalCount) : null
  if (!stepMs) {
    const deltas = []
    for (let i = 1; i < times.length; i += 1) {
      const delta = times[i] - times[i - 1]
      if (delta > 0) deltas.push(delta)
    }
    stepMs = median(deltas)
  }
  if (!stepMs || stepMs <= 0) return {labels, datasets, truncated: false}
  const start = times[0]
  const end = times[times.length - 1]
  let total = Math.floor((end - start) / stepMs) + 1
  const limit = Number.isFinite(maxPoints) ? Math.max(1, maxPoints) : 5000
  const truncated = total > limit
  if (truncated) total = limit
  const indexByTime = new Map()
  times.forEach((value, index) => indexByTime.set(value, index))
  const fullLabels = []
  const newDatasets = datasets.map((dataset) => ({
    ...dataset,
    data: []
  }))
  for (let i = 0; i < total; i += 1) {
    const current = start + (i * stepMs)
    fullLabels.push(new Date(current).toISOString())
    const sourceIndex = indexByTime.get(current)
    newDatasets.forEach((dataset, datasetIndex) => {
      if (sourceIndex === undefined) {
        dataset.data.push(null)
      } else {
        dataset.data.push(datasets[datasetIndex].data[sourceIndex])
      }
    })
  }
  return {labels: fullLabels, datasets: newDatasets, truncated}
}
