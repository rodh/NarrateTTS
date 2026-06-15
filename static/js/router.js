const NAV_SCREENS = ['home', 'feeds', 'library', 'settings'];
const ALL_SCREENS = [...NAV_SCREENS, 'feed-detail'];

export function navigate(hash) { location.hash = hash; }
export function currentRoute() { return (location.hash || '#/home').replace(/^#\/?/, '') || 'home'; }

export function initRouter(onShow) {
  const handle = () => {
    const route = currentRoute();
    const name = route.split('/')[0];
    const target = NAV_SCREENS.includes(name) ? name : (name === 'feed' ? 'feed-detail' : 'home');
    ALL_SCREENS.forEach(s => {
      const el = document.getElementById('screen-' + s);
      if (el) el.classList.toggle('hidden', s !== target);
    });
    const navTarget = name === 'feed' ? 'feeds' : target;
    document.querySelectorAll('[data-nav]').forEach(b =>
      b.classList.toggle('nav-active', b.dataset.nav === navTarget));
    onShow(name, route);
  };
  window.addEventListener('hashchange', handle);
  handle();
}
