<script>
  import { onMount } from 'svelte'
  import { api } from '../lib.js'

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
      message = 'Сохранено'
    } catch (err) {
      error = err.message
    }
  }

  onMount(load)
</script>

<section class="card">
  <h2>Настройки (admin)</h2>
  <div class="grid">
    <label>MQTT host</label>
    <input bind:value={form.mqtt_host} />

    <label>MQTT port</label>
    <input bind:value={form.mqtt_port} />

    <label>MQTT topics</label>
    <input bind:value={form.mqtt_topics} />

    <label>MQTT username</label>
    <input bind:value={form.mqtt_username} />

    <label>MQTT password</label>
    <input type="password" bind:value={form.mqtt_password} />

    <label>Float precision</label>
    <input bind:value={form.float_precision} />

    <label>Default aggregation</label>
    <select bind:value={form.default_agg}>
      <option value="avg">avg</option>
      <option value="min">min</option>
      <option value="max">max</option>
    </select>

    <label>Default interval</label>
    <select bind:value={form.default_interval}>
      <option value="second">second</option>
      <option value="minute">minute</option>
      <option value="hour">hour</option>
      <option value="day">day</option>
    </select>
  </div>

  <button on:click={save}>Сохранить</button>

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
