(() => {
  'use strict';

  document.querySelectorAll('form[data-refresh-after-download]').forEach((form) => {
    form.addEventListener('submit', () => {
      // Download-Antworten ersetzen die Seite nicht. Nach dem serverseitigen
      // Erzeugen wird deshalb die Statusansicht erneut eingelesen.
      window.setTimeout(() => window.location.reload(), 1200);
    });
  });
})();
