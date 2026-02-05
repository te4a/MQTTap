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

export function aggregateSeries(labels, values, interval, aggMode) {
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

export function buildFormulaEvaluator(fields, formula) {
  const tokens = formula.match(/[A-Za-z_][A-Za-z0-9_]*/g) || []
  for (const token of tokens) {
    if (!fields.includes(token)) {
      throw new Error(`Unknown field in formula: ${token}`)
    }
  }
  return new Function(...fields, `return ${formula}`)
}
