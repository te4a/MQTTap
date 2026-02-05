<script>
  export let item
  export let dragId = null
  export let isAggEnabled = () => false
  export let onDragStart = () => {}
  export let onDragOver = () => {}
  export let onDrop = () => {}
  export let onDragEnd = () => {}
  export let onToggleMenu = () => {}
  export let onTogglePoints = () => {}
  export let onEdit = () => {}
  export let onExport = () => {}
  export let onRemove = () => {}
  export let onResizeStart = () => {}
  export let onUpdateConfig = () => {}
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
            <button class="ghost" on:click={() => onEdit(item)}>Редактировать</button>
            <button class="ghost" on:click={() => onExport(item)}>Export JSON</button>
            <label class="toggle-row toggle-row-right">
              <span>Показывать точки</span>
              <input type="checkbox" checked={item.showPoints}
                     on:change={(e) => onTogglePoints(item, e)}/>
            </label>
            <div class="menu-section">
              <label>Агрегация</label>
              <select bind:value={item.agg} on:change={() => onUpdateConfig(item)}>
                <option value="off">off</option>
                <option value="avg">avg</option>
                <option value="min">min</option>
                <option value="max">max</option>
              </select>
            </div>
            {#if isAggEnabled(item.agg)}
              <div class="menu-section">
                <label>Интервал</label>
                <select bind:value={item.interval} on:change={() => onUpdateConfig(item)}>
                  <option value="second">second</option>
                  <option value="minute">minute</option>
                  <option value="hour">hour</option>
                  <option value="day">day</option>
                </select>
              </div>
            {/if}
            <div class="menu-section">
              <label>С</label>
              <input type="datetime-local" bind:value={item.fromTs} on:change={() => onUpdateConfig(item)} />
            </div>
            <div class="menu-section">
              <label>По</label>
              <input type="datetime-local" bind:value={item.toTs} on:change={() => onUpdateConfig(item)} />
            </div>
          </div>
        {/if}
      </div>
      <button class="ghost" on:click={() => onRemove(item.id)}>Удалить</button>
    </div>
  </div>
  <div class="chart-area" style={`height: ${item.height}px`}>
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
  }

  .chart-area canvas {
    width: 100% !important;
    height: 100% !important;
    display: block;
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

</style>
