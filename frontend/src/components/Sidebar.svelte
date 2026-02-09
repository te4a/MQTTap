<script>
  import { lang, t } from '../i18n.js'

  export let loggedIn = false
  export let isAdmin = false
  export let navigate

  const links = [
    { href: '/', key: 'nav.history' },
    { href: '/chart', key: 'nav.charts' },
    { href: '/profile', key: 'nav.profile' },
    { href: '/invites', key: 'nav.invites', adminOnly: true },
    { href: '/settings', key: 'nav.settings', adminOnly: true },
    { href: '/users', key: 'nav.users', adminOnly: true }
  ]

  function go(path, event) {
    event.preventDefault()
    if (navigate) navigate(path)
  }
</script>

<aside class="sidebar">
  <div class="brand">
    <img class="brand-icon" src="/app-icon.png" alt="MQTTap" />
    MQTTap
  </div>
  <nav>
    {#each links as link}
      {#if !link.adminOnly || isAdmin}
        <a class:disabled={!loggedIn} href={link.href} on:click={(e) => go(link.href, e)}>{t(link.key, $lang)}</a>
      {/if}
    {/each}
  </nav>
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
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .brand-icon {
    width: 44px;
    height: 44px;
    object-fit: contain;
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

</style>
