const SCREENS = ['home', 'feeds', 'library', 'settings'];

export function navigate(hash) { location.hash = hash; }

export function currentRoute() {
  return (location.hash || '#/home').replace(/^#\/?/, '') || 'home';
}

export function initRouter(onShow) {
  const handle = () => {
    const route = currentRoute();
    const name = route.split('/')[0];
    const target = SCREENS.includes(name) ? name : 'home';
    SCREENS.forEach(s => {
      const el = document.getElementById('screen-' + s);
      if (el) el.classList.toggle('hidden', s !== target);
    });
    document.querySelectorAll('[data-nav]').forEach(b =>
      b.classList.toggle('nav-active', b.dataset.nav === target));
    onShow(target, route);
  };
  window.addEventListener('hashchange', handle);
  handle();
}
