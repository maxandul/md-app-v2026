/* A local table of contents for screens with several chapters. */
(() => {
  const main = document.getElementById('main-content');
  if (!main) return;
  const headings = [...main.querySelectorAll('h2')].filter(heading =>
    !heading.closest('details, [hidden], [data-preview-result]'));
  if (headings.length < 2 || main.scrollHeight < window.innerHeight * 1.3) return;

  const layout = main.parentElement;
  const panel = document.createElement('details');
  panel.className = 'page-chapters';
  const summary = document.createElement('summary');
  summary.textContent = 'Auf dieser Seite';
  panel.append(summary);
  const nav = document.createElement('nav');
  nav.setAttribute('aria-label', 'Kapitel dieser Seite');
  const list = document.createElement('ol');
  const links = headings.map((heading, index) => {
    if (!heading.id) {
      const stem = 'kapitel-' + heading.textContent.trim().toLocaleLowerCase('de-CH')
        .replace(/[^a-z0-9äöü]+/g, '-').replace(/^-|-$/g, '');
      let id = stem;
      let suffix = 2;
      while (document.getElementById(id)) id = `${stem}-${suffix++}`;
      heading.id = id;
    }
    heading.classList.add('chapter-target');
    const li = document.createElement('li');
    const link = document.createElement('a');
    link.href = '#' + encodeURIComponent(heading.id);
    link.textContent = heading.dataset.chapterLabel || heading.textContent.trim();
    const count = heading.closest('.section-heading')?.querySelector('.section-count');
    if (count) link.textContent += ' · ' + count.textContent.trim();
    link.addEventListener('click', event => {
      event.preventDefault();
      if (!wide.matches) panel.open = false;
      history.replaceState(null, '', link.getAttribute('href'));
      heading.setAttribute('tabindex', '-1');
      heading.focus({preventScroll: true});
      heading.scrollIntoView({block: 'start'});
      activate(index);
    });
    li.append(link); list.append(li);
    return link;
  });
  nav.append(list); panel.append(nav);
  layout.prepend(panel);
  layout.classList.add('page-layout--chapters');
  const wide = matchMedia('(min-width: 1200px)');
  const adapt = () => { panel.open = wide.matches; };
  adapt(); wide.addEventListener('change', adapt);
  // Keep the desktop navigation expanded; the summary is a mobile control.
  summary.addEventListener('click', event => { if (wide.matches) event.preventDefault(); });
  function activate(index) {
    links.forEach((link, i) => {
      if (i === index) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  }
  let scheduled = false;
  function update() {
    scheduled = false;
    let active = 0;
    headings.forEach((heading, index) => {
      if (heading.getBoundingClientRect().top <= 120) active = index;
    });
    activate(active);
  }
  window.addEventListener('scroll', () => {
    if (!scheduled) { scheduled = true; requestAnimationFrame(update); }
  }, {passive: true});
  window.addEventListener('resize', update);
  update();
  // Generated anchors must also work when a chapter URL is opened directly.
  if (location.hash) {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch (_) { return; }
    const target = headings.find(heading => heading.id === id);
    if (target) requestAnimationFrame(() => target.scrollIntoView({block: 'start'}));
  }
})();
