import {aggregateSeries, alignTimeSeries, buildFormulaEvaluator, palette} from '../chart-utils.js'

export async function fetchChartSeries(api, item, isAggEnabled, valueFromRow) {
  const type = item.type || 'single'
  let labels = []
  let datasets = []
  let error = ''

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
    rows.slice().reverse().forEach((row, index) => {
      const values = item.fields.map(name => row[name])
      if (values.some(value => value === null || value === undefined)) return
      const numericValues = values.map(Number)
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

  const alignInterval = isAggEnabled(item.agg) ? item.interval : null
  const aligned = alignTimeSeries(labels, datasets, alignInterval, item.alignTime)
  return {labels: aligned.labels, datasets: aligned.datasets, error, truncated: aligned.truncated}
}
