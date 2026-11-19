(() => {
  document.querySelectorAll('[data-probation-event]').forEach(form => {
    const { event_type: type, required_scope: scope, disposition, outlook_due_date: outlookDue } = form.elements;
    const reviewOnly = scope.querySelector('option[value="review_only"]');
    const originalLabel = reviewOnly.dataset.standardLabel || reviewOnly.textContent;
    const submit = form.querySelector('[data-probation-submit]');
    const update = () => {
      const probation = type.value === 'probation_review';
      for (const option of scope.options) {
        option.hidden = probation && option !== reviewOnly;
        option.disabled = option.hidden;
      }
      reviewOnly.textContent = probation ? 'Nur Rückblick Probezeit' : originalLabel;
      if (probation) scope.value = reviewOnly.value;
      if (disposition) {
        const replace = disposition.querySelector('option[value="replace"]');
        replace.hidden = probation;
        replace.disabled = probation;
        if (probation) disposition.value = 'keep';
      }
      outlookDue.disabled = probation;
      if (submit) submit.textContent = probation ? 'Rückblick Probezeit erfassen und Vorlage öffnen' : 'Dialogereignis anlegen';
      form.querySelector('[data-probation-note]').hidden = !probation;
    };
    type.addEventListener('change', update);
    update();
  });
})();
