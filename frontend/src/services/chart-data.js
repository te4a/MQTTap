import {
  aggregateSeries,
  alignTimeSeries,
  buildFormulaEvaluator,
  normalizeNumericValue,
  palette
} from '../chart-utils.js'

export async function fetchChartSeries(api, item, isAggEnabled, valueFromRow, maxPoints = 5000) {
  const type = item.type || 'single'
  let labels = []
  let datasets = []
  let error = ''
  const limit = Number.isFinite(maxPoints) ? Math.max(1, maxPoints) : 5000

  if (type === 'single') {
    const params = {
      topic: item.topic,
      fields: item.field,
      from_ts: item.fromTs || undefined,
      to_ts: item.toTs || undefined
    }
    if (isAggEnabled(item.agg)) {
      params.agg = item.agg
      const count = Math.max(1, Number(item.intervalCount) || 1)
      params.interval = count > 1 ? `${count} ${item.interval}` : item.interval
    } else {
      params.order = 'desc'
      params.limit = maxPoints
    }
    const data = await api.history(params)
    const rows = data.rows || []
    labels = isAggEnabled(item.agg)
      ? rows.map(r => r.bucket)
      : rows.map(r => r.ts).reverse()
    const values = isAggEnabled(item.agg)
      ? rows.map(r => normalizeNumericValue(item.isJson ? r[item.field] : r.value))
      : rows.map(r => normalizeNumericValue(valueFromRow(r, item.field, item.isJson))).reverse()
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
    const yAxisMode = item.yAxisMode === 'shared' ? 'shared' : 'multi'
    const fieldsList = item.channels.map(ch => ch.field)
    const params = {
      topic: item.topic,
      fields: fieldsList.join(','),
      from_ts: item.fromTs || undefined,
      to_ts: item.toTs || undefined
    }
    if (isAggEnabled(item.agg)) {
      params.agg = item.agg
      const count = Math.max(1, Number(item.intervalCount) || 1)
      params.interval = count > 1 ? `${count} ${item.interval}` : item.interval
    } else {
      params.order = 'desc'
      params.limit = maxPoints
    }
    const data = await api.history(params)
    const rows = data.rows || []
    labels = isAggEnabled(item.agg)
      ? rows.map(r => r.bucket)
      : rows.map(r => r.ts).reverse()
    datasets = item.channels.map((channel, index) => ({
      label: channel.label || channel.field,
      data: isAggEnabled(item.agg)
        ? rows.map(r => normalizeNumericValue(r[channel.field]))
        : rows.map(r => normalizeNumericValue(valueFromRow(r, channel.field, true))).reverse(),
      borderColor: palette[index % palette.length],
      backgroundColor: 'rgba(17,24,39,0.1)',
      tension: 0.2,
      pointRadius: item.showPoints ? 3 : 0,
      pointHoverRadius: item.showPoints ? 4 : 4,
      pointHitRadius: item.showPoints ? 3 : 10,
      yAxisID: yAxisMode === 'shared'
        ? 'y'
        : (channel.axis || (index === 0 ? 'y' : `y${index}`))
    }))
  } else if (type === 'formula') {
    if (!item.formula || !item.fields || !item.fields.length) {
      throw new Error('errors.formulaConfigEmpty')
    }
    const params = {
      topic: item.topic,
      fields: item.fields.join(','),
      from_ts: item.fromTs || undefined,
      to_ts: item.toTs || undefined,
      order: 'desc',
      limit: maxPoints
    }
    const data = await api.history(params)
    const rows = data.rows || []
    const evaluator = buildFormulaEvaluator(item.fields, item.formula)
    const rawLabels = rows.map(r => r.ts).reverse()
    const rawValues = []
    const rawFilteredLabels = []
    rows.slice().reverse().forEach((row, index) => {
      const values = item.fields.map(name => row[name])
      if (values.some(value => value === null || value === undefined)) return
      const numericValues = values.map(normalizeNumericValue)
      if (numericValues.some(value => !Number.isFinite(value))) return
      let result
      try {
        result = evaluator(...numericValues)
      } catch (err) {
        error = 'errors.formulaEvaluation'
        return
      }
      if (!Number.isFinite(result)) {
        error = 'errors.divisionByZero'
        return
      }
      rawValues.push(result)
      rawFilteredLabels.push(rawLabels[index])
    })
    if (isAggEnabled(item.agg)) {
      const aggregated = aggregateSeries(
        rawFilteredLabels,
        rawValues,
        item.interval,
        item.agg,
        item.intervalCount || 1
      )
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

  const trimmed = trimSeries(labels, datasets, limit)
  const alignInterval = isAggEnabled(item.agg) ? item.interval : null
  const aligned = alignTimeSeries(
    trimmed.labels,
    trimmed.datasets,
    alignInterval,
    item.alignTime,
    limit,
    item.intervalCount || 1
  )
  return {
    labels: aligned.labels,
    datasets: aligned.datasets,
    error,
    truncated: trimmed.truncated || aligned.truncated
  }
}

function trimSeries(labels, datasets, limit) {
  if (!limit || labels.length <= limit) {
    return {labels, datasets, truncated: false}
  }
  const start = labels.length - limit
  const trimmedLabels = labels.slice(start)
  const trimmedDatasets = datasets.map(dataset => ({
    ...dataset,
    data: dataset.data.slice(start)
  }))
  return {labels: trimmedLabels, datasets: trimmedDatasets, truncated: true}
}
