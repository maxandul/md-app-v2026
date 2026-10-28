(() => {
  'use strict';
  const editor = document.querySelector('[data-goal-editor]');
  let dirty = false;
  if (editor) {
    editor.addEventListener('input', () => { dirty = true; });
    editor.addEventListener('change', () => { dirty = true; });
    editor.addEventListener('submit', () => { dirty = false; });
    window.addEventListener('beforeunload', event => {
      if (dirty) { event.preventDefault(); event.returnValue = ''; }
    });
  }
  document.addEventListener('click', event => {
    const add = event.target.closest('[data-add-goal]');
    const remove = event.target.closest('[data-remove-goal]');
    if (add) {
      const kind = add.dataset.addGoal;
      document.querySelector(`[data-goal-list="${kind}"]`).append(document.getElementById(`${kind}-template`).content.cloneNode(true));
      dirty = true;
    }
    if (remove) { remove.closest('fieldset').remove(); dirty = true; }
  });
  document.querySelectorAll('[data-lookup]').forEach(input => {
    let timer, serial = 0;
    input.addEventListener('input', () => {
      clearTimeout(timer);
      const requestId = ++serial;
      timer = setTimeout(async () => {
        const select = document.getElementById(input.dataset.target);
        try {
          const url = new URL(input.dataset.url, location.origin);
          url.searchParams.set('kind', input.dataset.lookup);
          url.searchParams.set('q', input.value);
          const response = await fetch(url);
          if (!response.ok) throw new Error();
          const data = await response.json();
          if (requestId !== serial) return;
          const previous = select.selectedOptions[0];
          const retained = previous && previous.value ? previous.cloneNode(true) : null;
          select.replaceChildren(new Option('Bitte auswählen (max. 25 Treffer)', ''));
          if (retained) { select.append(retained); retained.selected = true; }
          data.results.forEach(row => {
            if (!retained || String(row.id) !== retained.value) select.append(new Option(row.label, row.id));
          });
          input.setCustomValidity('');
        } catch (_) {
          input.setCustomValidity('Suche fehlgeschlagen. Bitte erneut versuchen.');
          input.reportValidity();
        }
      }, 250);
    });
  });
})();
