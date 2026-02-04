<script>
  export let loggedIn = false
  export let isAdmin = false
  export let navigate

  const links = [
    { href: '/', label: 'История' },
    { href: '/chart', label: 'Графики' },
    { href: '/settings', label: 'Настройки', adminOnly: true },
    { href: '/users', label: 'Пользователи', adminOnly: true }
  ]

  function go(path, event) {
    event.preventDefault()
    if (navigate) navigate(path)
  }
</script>

<aside class="sidebar">
  <div class="brand">MQTTap</div>
  <nav>
    {#each links as link}
      {#if !link.adminOnly || isAdmin}
        <a class:disabled={!loggedIn} href={link.href} on:click={(e) => go(link.href, e)}>{link.label}</a>
      {/if}
    {/each}
  </nav>
  <div class="hint">
    {#if loggedIn}
      Вы вошли в систему
    {:else}
      Войдите для доступа
    {/if}
  </div>
</aside>

<style>
  .sidebar {
    background: #111827;
    color: #f9fafb;
    padding: 24px;
  }

  .brand {
    font-weight: 700;
    font-size: 20px;
    margin-bottom: 32px;
    letter-spacing: 0.5px;
  }

  nav {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  a {
    color: #f9fafb;
    text-decoration: none;
    padding: 10px 12px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.05);
  }

  a:hover {
    background: rgba(255, 255, 255, 0.15);
  }

  a.disabled {
    opacity: 0.5;
    pointer-events: none;
  }

  .hint {
    margin-top: 24px;
    font-size: 12px;
    color: #9ca3af;
  }
</style>