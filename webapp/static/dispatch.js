(() => {
  'use strict';

  document.querySelectorAll('form[data-refresh-after-download]').forEach((form) => {
    form.addEventListener('submit', () => {
      // Download-Antworten ersetzen die Seite nicht. Nach dem serverseitigen
      // Erzeugen wird deshalb die Statusansicht erneut eingelesen.
      window.setTimeout(() => window.location.reload(), 1200);
    });
  });

  document.querySelectorAll('button[data-confirm-direct-send]').forEach((button) => {
    button.addEventListener('click', (event) => {
      const form = button.form;
      const selected = form ? form.querySelectorAll('input[name="package_event_id"]:checked').length : 0;
      if (!window.confirm(`${selected} ausgewählte E-Mail(s) jetzt direkt S/MIME-verschlüsselt versenden?`)) {
        event.preventDefault();
      }
    });
  });
})();
