(() => {
  'use strict';

  document.querySelectorAll('table').forEach((table, tableIndex) => {
    if (table.hasAttribute('data-server-paginated')) return;
    const body = table.tBodies[0];
    if (!body) return;
    const rows = Array.from(body.rows);
    if (rows.length <= 50) return;

    const wrap = table.closest('.table-wrap');
    if (!wrap) return;
    const controls = document.createElement('div');
    controls.className = 'table-controls';
    const searchId = `table-search-${tableIndex}`;
    controls.innerHTML = `
      <label for="${searchId}">Tabelle durchsuchen</label>
      <input id="${searchId}" type="search" placeholder="Suchbegriff">
      <label>Zeilen pro Seite
        <select><option value="25">25</option><option value="50" selected>50</option><option value="100">100</option></select>
      </label>
      <span class="table-controls__status" aria-live="polite"></span>
      <button class="button button--small" type="button" data-page="previous">Zurück</button>
      <button class="button button--small" type="button" data-page="next">Weiter</button>`;
    wrap.before(controls);

    const search = controls.querySelector('input');
    const pageSize = controls.querySelector('select');
    const status = controls.querySelector('.table-controls__status');
    const previous = controls.querySelector('[data-page="previous"]');
    const next = controls.querySelector('[data-page="next"]');
    let page = 1;
    const stateKey = `md-table:${location.pathname}${location.search}:${tableIndex}`;
    try {
      const saved = JSON.parse(sessionStorage.getItem(stateKey) || 'null');
      if (saved) {
        search.value = saved.query || '';
        if ([25, 50, 100].includes(Number(saved.size))) pageSize.value = String(saved.size);
        page = Math.max(1, Number(saved.page) || 1);
      }
    } catch (_) { /* Storage can be disabled. */ }

    const render = () => {
      const needle = search.value.trim().toLocaleLowerCase('de-CH');
      const filtered = rows.filter((row) => row.textContent.toLocaleLowerCase('de-CH').includes(needle));
      const size = Number(pageSize.value);
      const pages = Math.max(1, Math.ceil(filtered.length / size));
      page = Math.min(page, pages);
      const visible = new Set(filtered.slice((page - 1) * size, page * size));
      rows.forEach((row) => { row.hidden = !visible.has(row); });
      status.textContent = `${filtered.length} Einträge · Seite ${page} von ${pages}`;
      previous.disabled = page === 1;
      next.disabled = page === pages;
      try { sessionStorage.setItem(stateKey, JSON.stringify({query: search.value, size, page})); }
      catch (_) { /* Keep controls usable without storage. */ }
    };

    search.addEventListener('input', () => { page = 1; render(); });
    pageSize.addEventListener('change', () => { page = 1; render(); });
    previous.addEventListener('click', () => { page -= 1; render(); });
    next.addEventListener('click', () => { page += 1; render(); });
    render();
  });
})();
