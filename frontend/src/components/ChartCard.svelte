<script>
  import { lang, t } from '../i18n.js'

  export let item
  export let dragId = null
  export let isAggEnabled = () => false
  export let onDragStart = () => {}
  export let onDragOver = () => {}
  export let onDrop = () => {}
  export let onDragEnd = () => {}
  export let onToggleMenu = () => {}
  export let onTogglePoints = () => {}
  export let onToggleAlign = () => {}
  export let onToggleYAxisMode = () => {}
  export let onEdit = () => {}
  export let onExport = () => {}
  export let onRemove = () => {}
  export let onResizeStart = () => {}
  export let onUpdateConfig = () => {}

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
</script>

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
        <button class="ghost" on:click={() => onToggleMenu(item)}>...</button>
        {#if item.menuOpen}
          <div class="menu-panel">
            <button class="ghost" on:click={() => onEdit(item)}>{t('charts.edit', $lang)}</button>
            <button class="ghost" on:click={() => onExport(item)}>{t('charts.export', $lang)}</button>
            <label class="toggle-row toggle-row-right">
              <span>{t('common.showPoints', $lang)}</span>
              <input type="checkbox" checked={item.showPoints}
                     on:change={(e) => onTogglePoints(item, e)}/>
            </label>
            <label class="toggle-row toggle-row-right">
              <span>{t('common.alignTime', $lang)}</span>
              <input type="checkbox" checked={item.alignTime}
                     on:change={(e) => onToggleAlign(item, e)}/>
            </label>
            {#if item.type === 'multi'}
              <div class="menu-section">
                <label>{t('charts.yAxisMode', $lang)}</label>
                <select
                  value={item.yAxisMode || 'multi'}
                  on:change={(e) => onToggleYAxisMode(item, e)}
                >
                  <option value="multi">{t('charts.yAxisModeMulti', $lang)}</option>
                  <option value="shared">{t('charts.yAxisModeShared', $lang)}</option>
                </select>
              </div>
            {/if}
            <div class="menu-section">
              <label>{t('common.aggregation', $lang)}</label>
              <select bind:value={item.agg} on:change={() => onUpdateConfig(item)}>
                <option value="off">{t('agg.off', $lang)}</option>
                <option value="avg">{t('agg.avg', $lang)}</option>
                <option value="min">{t('agg.min', $lang)}</option>
                <option value="max">{t('agg.max', $lang)}</option>
              </select>
            </div>
            {#if isAggEnabled(item.agg)}
              <div class="menu-section">
                <label>{t('common.interval', $lang)}</label>
                <div class="interval-row">
                  <span class="interval-label">{t('common.intervalEvery', $lang)}</span>
                  <input
                    type="number"
                    min="1"
                    step="1"
                    bind:value={item.intervalCount}
                    on:change={() => onUpdateConfig(item)}
                  />
                  <div class="select-short">
                    <span class="select-short-label">{shortInterval(item.interval, $lang)}</span>
                    <select bind:value={item.interval} on:change={() => onUpdateConfig(item)}>
                      <option value="second">{t('interval.second', $lang)}</option>
                      <option value="minute">{t('interval.minute', $lang)}</option>
                      <option value="hour">{t('interval.hour', $lang)}</option>
                      <option value="day">{t('interval.day', $lang)}</option>
                    </select>
                  </div>
                </div>
              </div>
            {/if}
            <div class="menu-section">
              <label>{t('common.from', $lang)}</label>
              <input type="datetime-local" bind:value={item.fromTs} on:change={() => onUpdateConfig(item)} />
            </div>
            <div class="menu-section">
              <label>{t('common.to', $lang)}</label>
              <input type="datetime-local" bind:value={item.toTs} on:change={() => onUpdateConfig(item)} />
            </div>
          </div>
        {/if}
      </div>
      <button class="ghost" on:click={() => onRemove(item.id)}>{t('charts.delete', $lang)}</button>
    </div>
  </div>
  <div class="chart-area" style={`height: ${item.height}px`}>
    {#if item.limitNotice}
      <div class="limit-badge">{item.limitNotice}</div>
    {/if}
    <canvas bind:this={item.canvas}></canvas>
  </div>
  <div class="resize-grip" on:mousedown={(e) => onResizeStart(item, e)}></div>
</section>

<style>
  .chart-card {
    background: #ffffff;
    padding: 16px;
    border-radius: 12px;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.06);
    display: flex;
    flex-direction: column;
    gap: 12px;
    position: relative;
    min-width: 0;
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
    width: 100%;
    min-width: 0;
    position: relative;
  }

  .chart-area canvas {
    width: 100% !important;
    height: 100% !important;
    display: block;
  }

  .limit-badge {
    position: absolute;
    top: 8px;
    right: 8px;
    background: rgba(17, 24, 39, 0.85);
    color: #f9fafb;
    padding: 4px 8px;
    border-radius: 999px;
    font-size: 11px;
    letter-spacing: 0.02em;
    z-index: 2;
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

  .toggle-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
  }

  .toggle-row-right {
    justify-content: flex-start;
    width: auto;
    white-space: nowrap;
  }

  .toggle-row input {
    margin: 0;
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
</style>
