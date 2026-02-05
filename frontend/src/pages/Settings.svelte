<script>
  import { onMount } from 'svelte'
  import { api } from '../lib.js'
  import { lang, t } from '../i18n.js'

  let form = {
    mqtt_host: '',
    mqtt_port: '',
    mqtt_topics: '',
    mqtt_username: '',
    mqtt_password: '',
    float_precision: '',
    default_agg: 'avg',
    default_interval: 'minute'
  }
  let message = ''
  let error = ''

  async function load() {
    try {
      const data = await api.getSettings()
      form = { ...form, ...data }
    } catch (err) {
      error = err.message
    }
  }

  async function save() {
    error = ''
    message = ''
    try {
      await api.updateSettings(form)
      message = t('messages.saved', $lang)
    } catch (err) {
      error = err.message
    }
  }

  onMount(load)
</script>

<section class="card">
  <h2>{t('settings.title', $lang)}</h2>
  <div class="grid">
    <label>{t('settings.mqttHost', $lang)}</label>
    <input bind:value={form.mqtt_host} />

    <label>{t('settings.mqttPort', $lang)}</label>
    <input bind:value={form.mqtt_port} />

    <label>{t('settings.mqttTopics', $lang)}</label>
    <input bind:value={form.mqtt_topics} />

    <label>{t('settings.mqttUsername', $lang)}</label>
    <input bind:value={form.mqtt_username} />

    <label>{t('settings.mqttPassword', $lang)}</label>
    <input type="password" bind:value={form.mqtt_password} />

    <label>{t('settings.floatPrecision', $lang)}</label>
    <input bind:value={form.float_precision} />

    <label>{t('settings.defaultAgg', $lang)}</label>
    <select bind:value={form.default_agg}>
      <option value="avg">{t('agg.avg', $lang)}</option>
      <option value="min">{t('agg.min', $lang)}</option>
      <option value="max">{t('agg.max', $lang)}</option>
    </select>

    <label>{t('settings.defaultInterval', $lang)}</label>
    <select bind:value={form.default_interval}>
      <option value="second">{t('interval.second', $lang)}</option>
      <option value="minute">{t('interval.minute', $lang)}</option>
      <option value="hour">{t('interval.hour', $lang)}</option>
      <option value="day">{t('interval.day', $lang)}</option>
    </select>
  </div>

  <button on:click={save}>{t('common.save', $lang)}</button>

  {#if message}
    <div class="ok">{message}</div>
  {/if}
  {#if error}
    <div class="error">{error}</div>
  {/if}
</section>

<style>
  .grid {
    display: grid;
    grid-template-columns: 160px 1fr;
    gap: 12px;
    margin-bottom: 16px;
  }

  .ok {
    margin-top: 10px;
  }

  .error {
    margin-top: 10px;
  }

  @media (max-width: 700px) {
    .grid {
      grid-template-columns: 1fr;
    }
  }
</style>
