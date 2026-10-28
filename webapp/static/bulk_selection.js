(() => {
  'use strict';

  document.querySelectorAll('[data-bulk-selection]').forEach(scope => {
    const name = scope.dataset.bulkSelection;
    const choices = () => [...scope.querySelectorAll('input[type="checkbox"]')]
      .filter(input => input.name === name && !input.disabled);
    if (!choices().length) return;
    let matchingRows = null;
    let changingSelection = false;
    const pageOnly = scope.hasAttribute('data-bulk-page');
    const targets = () => choices().filter(input => !input.hasAttribute('data-bulk-skip')
      && (!matchingRows || matchingRows.has(input.closest('tr'))));
    const bar = document.createElement('div');
    bar.className = 'selection-controls';
    bar.setAttribute('role', 'group');
    bar.setAttribute('aria-label', 'Einträge gemeinsam auswählen');
    const all = document.createElement('button');
    const none = document.createElement('button');
    const status = document.createElement('span');
    all.type = none.type = 'button';
    all.className = none.className = 'button button--small';
    none.textContent = pageOnly ? 'Seite abwählen' : 'Alles abwählen';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    bar.append(all, none, status);
    if (scope.tagName === 'TABLE') (scope.closest('.table-wrap') || scope).before(bar);
    else scope.prepend(bar);

    const update = () => {
      const available = targets();
      const count = choices().filter(input => input.checked).length;
      all.textContent = pageOnly ? `Alle ${available.length} auf dieser Seite auswählen`
        : `Alle ${available.length} Treffer auswählen`;
      all.disabled = !available.length || available.every(input => input.checked);
      none.disabled = count === 0;
      status.textContent = `${count} ausgewählt${pageOnly ? ' auf dieser Seite' : ' insgesamt'}`;
    };
    const set = (inputs, checked) => {
      changingSelection = true;
      inputs.forEach(input => {
        if (input.checked !== checked) {
          input.checked = checked;
          input.dispatchEvent(new Event('change', {bubbles: true}));
        }
      });
      changingSelection = false;
      update();
    };
    all.addEventListener('click', () => set(targets(), true));
    none.addEventListener('click', () => set(choices(), false));
    scope.addEventListener('change', () => { if (!changingSelection) update(); });
    scope.addEventListener('md-table-filter', event => {
      matchingRows = new Set(event.detail.rows);
      update();
    });
    update();
  });
})();
