(() => {
  document.querySelectorAll('[data-filter-select]').forEach(input => {
    const select = document.getElementById(input.dataset.filterSelect);
    const options = [...select.options];
    input.addEventListener('input', () => {
      const needle = input.value.trim().toLocaleLowerCase('de-CH');
      const selected = select.value;
      select.replaceChildren(...options.filter(option => !option.value || option.value === selected || option.textContent.toLocaleLowerCase('de-CH').includes(needle)));
      select.value = selected;
    });
    if (input.value) input.dispatchEvent(new Event('input'));
  });
  const employee = document.getElementById('manual-employee');
  const manager = document.getElementById('manual-manager');
  const source = document.getElementById('form-org-source');
  const preview = document.getElementById('form-org-preview');
  if (!employee || !manager || !source || !preview) return;
  const update = () => {
    const selected = (source.value === 'manager' ? manager : employee).selectedOptions[0];
    preview.textContent = selected?.value ? 'OE im Formular: ' + (selected.dataset.org || 'Keine OE in den Stammdaten hinterlegt') : 'Bitte zuerst die betreffende Person auswählen.';
  };
  [employee, manager, source].forEach(select => select.addEventListener('change', update));
  update();
})();
