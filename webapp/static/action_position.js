/* Keep the working position after a POST returning to the same screen. */
(() => {
  const key = 'md-action-position';
  document.addEventListener('submit', event => {
    const form = event.target;
    if (form.method.toLowerCase() !== 'post') return;
    try {
      sessionStorage.setItem(key, JSON.stringify({path: location.pathname, at: Date.now(), y: scrollY,
        details: [...document.querySelectorAll('details')].map((el, index) => el.open ? index : -1).filter(index => index >= 0)}));
    } catch (_) { /* Browser storage may be disabled. */ }
  }, true);
  try {
    const saved = JSON.parse(sessionStorage.getItem(key) || 'null');
    sessionStorage.removeItem(key);
    if (!saved || saved.path !== location.pathname || Date.now() - saved.at > 120000) return;
    const details = document.querySelectorAll('details');
    saved.details.forEach(index => { if (details[index]) details[index].open = true; });
    requestAnimationFrame(() => {
      if (location.hash) document.getElementById(decodeURIComponent(location.hash.slice(1)))?.scrollIntoView();
      else scrollTo(0, saved.y);
      const messages = document.querySelector('.messages');
      if (messages && saved.y > 300) {
        messages.classList.add('messages--action-result');
        const button = document.createElement('button');
        button.type = 'button'; button.className = 'button button--small'; button.textContent = 'Meldung schliessen';
        button.addEventListener('click', () => messages.remove()); messages.append(button);
      }
    });
  } catch (_) { /* Leave normal navigation intact. */ }
})();
