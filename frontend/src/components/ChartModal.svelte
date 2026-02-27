<script>
  import { lang, t } from '../i18n.js'

  export let open = false
  export let modalType = 'single'
  export let topics = []
  export let modalTopic = ''
  export let modalFields = []
  export let modalField = ''
  export let modalSelectedFields = []
  export let modalYAxisMode = 'multi'
  export let modalFormula = ''
  export let modalAgg = 'avg'
  export let modalInterval = 'minute'
  export let modalIntervalCount = 1
  export let modalFromTs = ''
  export let modalToTs = ''
  export let modalShowPoints = false
  export let modalAlignTime = false
  export let modalError = ''
  export let modalFormulaError = ''
  export let isAggEnabled = () => false
  export let onClose = () => {}
  export let onSubmit = () => {}
  export let onTopicChange = () => {}
  export let onToggleField = () => {}
  export let onValidateFormula = () => {}
  export let title = ''
  export let submitLabel = ''

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

{#if open}
  <div class="modal-backdrop" on:click={onClose}>
    <div class="modal" on:click|stopPropagation>
      <div class="modal-header">
        <h3>{title}</h3>
        <button class="ghost" on:click={onClose}>×</button>
      </div>
      <div class="modal-grid">
        <div>
          <label>{t('common.type', $lang)}</label>
          <div class="modal-type">
            {#if modalType === 'single'}
              {t('charts.addSingle', $lang)}
            {:else if modalType === 'multi'}
              {t('charts.addMulti', $lang)}
            {:else}
              {t('charts.addFormula', $lang)}
            {/if}
          </div>
        </div>
        <div>
          <label>{t('charts.topic', $lang)}</label>
          <select bind:value={modalTopic} on:change={onTopicChange}>
            {#each topics as t}
              <option value={t.topic}>{t.topic}</option>
            {/each}
          </select>
        </div>
        {#if modalType === 'single'}
          <div>
            <label>{t('charts.field', $lang)}</label>
            <select bind:value={modalField}>
              {#each modalFields as field}
                <option value={field}>{field}</option>
              {/each}
            </select>
          </div>
        {/if}
        {#if modalType === 'multi'}
          <div class="modal-span">
            <label>{t('charts.fieldsUpTo', $lang)}</label>
            <div class="field-grid">
              {#each modalFields as field}
                <label class="field-option">
                  <input
                    type="checkbox"
                    checked={modalSelectedFields.includes(field)}
                    on:change={() => onToggleField(field)}
                  />
                  {field}
                </label>
              {/each}
            </div>
          </div>
          <div>
            <label>{t('charts.yAxisMode', $lang)}</label>
            <select bind:value={modalYAxisMode}>
              <option value="multi">{t('charts.yAxisModeMulti', $lang)}</option>
              <option value="shared">{t('charts.yAxisModeShared', $lang)}</option>
            </select>
          </div>
        {/if}
        {#if modalType === 'formula'}
          <div class="modal-span">
            <label>{t('charts.formula', $lang)}</label>
            <input
              type="text"
              bind:value={modalFormula}
              class:input-error={!!modalFormulaError}
              on:input={onValidateFormula}
            />
          </div>
          <div class="modal-span hint">
            {t('charts.formulaHint', $lang)}: {modalFields.join(', ')}
          </div>
          {#if modalFormulaError}
            <div class="modal-span error-text">{modalFormulaError}</div>
          {/if}
        {/if}
        <div>
          <label>{t('common.aggregation', $lang)}</label>
          <select bind:value={modalAgg}>
            <option value="off">{t('agg.off', $lang)}</option>
            <option value="avg">{t('agg.avg', $lang)}</option>
            <option value="min">{t('agg.min', $lang)}</option>
            <option value="max">{t('agg.max', $lang)}</option>
          </select>
        </div>
        {#if isAggEnabled(modalAgg)}
          <div>
            <label>{t('common.interval', $lang)}</label>
            <div class="interval-row">
              <span class="interval-label">{t('common.intervalEvery', $lang)}</span>
              <input type="number" min="1" step="1" bind:value={modalIntervalCount} />
              <div class="select-short">
                <span class="select-short-label">{shortInterval(modalInterval, $lang)}</span>
                <select bind:value={modalInterval}>
                  <option value="second">{t('interval.second', $lang)}</option>
                  <option value="minute">{t('interval.minute', $lang)}</option>
                  <option value="hour">{t('interval.hour', $lang)}</option>
                  <option value="day">{t('interval.day', $lang)}</option>
                </select>
              </div>
            </div>
          </div>
        {/if}
        <div>
          <label>{t('common.from', $lang)}</label>
          <input type="datetime-local" bind:value={modalFromTs}/>
        </div>
        <div>
          <label>{t('common.to', $lang)}</label>
          <input type="datetime-local" bind:value={modalToTs}/>
        </div>
        <div class="modal-span modal-checkbox">
          <label class="checkbox checkbox-right">
            <span>{t('common.showPoints', $lang)}</span>
            <input type="checkbox" bind:checked={modalShowPoints} />
          </label>
        </div>
        <div class="modal-span modal-checkbox">
          <label class="checkbox checkbox-right">
            <span>{t('common.alignTime', $lang)}</span>
            <input type="checkbox" bind:checked={modalAlignTime} />
          </label>
        </div>
      </div>
      {#if modalError}
        <div class="error">{modalError}</div>
      {/if}
      <div class="modal-actions">
        <button on:click={onSubmit}>{submitLabel}</button>
        <button class="ghost" on:click={onClose}>{t('common.cancel', $lang)}</button>
      </div>
    </div>
  </div>
{/if}

<style>
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

  .checkbox input {
    margin: 0;
  }

  .checkbox-right {
    display: inline-flex;
    justify-content: flex-start;
    width: auto;
    white-space: nowrap;
  }

  .modal-checkbox {
    justify-self: start;
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

  .error {
    color: #b91c1c;
  }
</style>
