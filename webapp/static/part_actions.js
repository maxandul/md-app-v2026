/* Informative only: selection persistence and action validation stay server-side. */
(() => {
  const total = document.querySelector('[data-selection-total]');
  const choices = [...document.querySelectorAll('input[name="part"]')];
  const initial = new Set(choices.filter(c => c.checked).map(c => c.value));
  if (total) {
    const saved = Number(total.dataset.savedCount);
    const update = () => {
      const checked = choices.filter(c => c.checked);
      const changed = checked.length !== initial.size || checked.some(c => !initial.has(c.value));
      const count = saved - initial.size + checked.length;
      total.textContent = `${count} Gesprächsteile ausgewählt${changed ? ' · Änderungen dieser Seite noch nicht gespeichert' : ' · gespeichert'}`;
    };
    choices.forEach(choice => choice.addEventListener('change', update));
    update();
  }
  const action = document.querySelector('[data-part-action]');
  if (action) {
    const update = () => document.querySelectorAll('[data-deadline-field]').forEach(field => {
      field.hidden = action.value !== 'deadline';
    });
    action.addEventListener('change', update);
    update();
  }
})();
