(() => {
  document.querySelectorAll('[data-probation-event]').forEach(form => {
    const { event_type: type, required_scope: scope, disposition, outlook_due_date: outlookDue } = form.elements;
    const { employment_id: employment, period_start: periodStart, period_end: periodEnd } = form.elements;
    const isProbation = () => type.value === 'probation_review';
    let otherPeriod = ['', ''];

    const fillProbationPeriod = () => {
      const dates = employment ? employment.selectedOptions[0]?.dataset : form.dataset;
      periodStart.value = dates?.entryDate || '';
      periodEnd.value = dates?.probationEnd || '';
    };

    const reviewOnly = scope.querySelector('option[value="review_only"]');
    const originalLabel = reviewOnly.dataset.standardLabel || reviewOnly.textContent;
    const submit = form.querySelector('[data-probation-submit]');
    const update = () => {
      const probation = isProbation();
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
    let wasProbation = isProbation();
    type.addEventListener('change', () => {
      const probation = isProbation();
      if (!wasProbation && probation) {
        otherPeriod = [periodStart.value, periodEnd.value];
        fillProbationPeriod();
      } else if (wasProbation && !probation) {
        [periodStart.value, periodEnd.value] = otherPeriod;
      }
      wasProbation = probation;
      update();
    });
    if (employment) {
      employment.addEventListener('change', () => {
        if (isProbation()) fillProbationPeriod();
      });
      if (wasProbation && !periodStart.value && !periodEnd.value) fillProbationPeriod();
    }
    update();
  });
})();
