(() => {
  'use strict';

  document.querySelectorAll('[data-mail-preview]').forEach(button => {
    const form = button.form;
    const status = form.querySelector('[data-preview-status]');
    const result = form.querySelector('[data-preview-result]');
    const preview = async () => {
      button.disabled = true;
      result.replaceChildren();
      status.textContent = 'Vorschau wird geladen …';
      try {
        const response = await fetch(button.dataset.mailPreview, {method: 'POST', body: new FormData(form), credentials: 'same-origin'});
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Vorschau konnte nicht geladen werden.');
        const subject = document.createElement('h3');
        subject.textContent = data.subject;
        const body = document.createElement('div');
        body.innerHTML = data.body_html;
        result.append(subject, body);
        status.textContent = 'Vorschau des aktuellen Texts. Es wurde kein Outlook-Entwurf erstellt.';
      } catch (error) {
        status.textContent = error.message;
      } finally { button.disabled = false; }
    };
    button.addEventListener('click', preview);
    form.addEventListener('input', event => {
      if (['subject_template', 'body_template', 'preview_manager_pn'].includes(event.target.name)) {
        result.replaceChildren();
        status.textContent = 'Text oder Führungskraft geändert. Bitte die Vorschau aktualisieren.';
      }
    });
    preview();
  });

  document.querySelectorAll('form[data-refresh-after-download]').forEach((form) => {
    let busy = false;
    let downloadUrl = '';
    const status = document.createElement('div');
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    form.after(status);

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (busy) return;
      busy = true;
      const body = new FormData(form);
      if (event.submitter && event.submitter.name) {
        body.append(event.submitter.name, event.submitter.value);
      }
      const buttons = [...form.querySelectorAll('button[type="submit"],button:not([type]),input[type="submit"]')];
      const disabled = buttons.map(button => button.disabled);
      buttons.forEach(button => { button.disabled = true; });
      form.setAttribute('aria-busy', 'true');
      status.className = 'message message--info';
      status.textContent = 'Datei wird erzeugt. Bitte warten und diese Seite geöffnet lassen …';
      if (downloadUrl) { URL.revokeObjectURL(downloadUrl); downloadUrl = ''; }
      try {
        const response = await fetch(form.action, { method: 'POST', body, credentials: 'same-origin' });
        const disposition = response.headers.get('Content-Disposition') || '';
        if (!response.ok || !/^attachment\b/i.test(disposition)) {
          const html = await response.text();
          const page = new DOMParser().parseFromString(html, 'text/html');
          const messages = [...page.querySelectorAll('.message--error')].map(node => node.textContent.trim());
          throw new Error(messages.join(' ') || 'Keine Datei erhalten. Bitte die Seite aktualisieren und gegebenenfalls erneut anmelden. Bei einem Serverfehler steht die Fehlermeldung im Terminal.');
        }
        const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i);
        const plain = disposition.match(/filename="([^"]+)"|filename=([^;]+)/i);
        let filename = plain ? (plain[1] || plain[2]).trim() : 'MD_Download.zip';
        if (encoded) {
          try { filename = decodeURIComponent(encoded[1]); } catch (_) { /* Use plain filename. */ }
        }
        downloadUrl = URL.createObjectURL(await response.blob());
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = filename;
        link.textContent = filename + ' erneut herunterladen';
        status.className = 'message message--success';
        status.textContent = 'Datei erzeugt; Download wird gestartet. Du findest sie normalerweise im Download-Ordner (Strg+J im Browser). ';
        status.append(link);
        link.click();
        status.append(document.createTextNode(' '));
        const refresh = document.createElement('a');
        refresh.href = window.location.href;
        refresh.textContent = 'Statusansicht aktualisieren';
        status.append(refresh);
      } catch (error) {
        status.className = 'message message--error';
        status.textContent = error instanceof TypeError
          ? 'Die Verbindung wurde unterbrochen. Die Erzeugung kann bereits erfolgt sein. Bitte zuerst die Statusansicht prüfen.'
          : error.message;
      } finally {
        busy = false;
        buttons.forEach((button, index) => { button.disabled = disabled[index]; });
        form.removeAttribute('aria-busy');
      }
    });
  });

  document.querySelectorAll('button[data-confirm-direct-send]').forEach((button) => {
    button.addEventListener('click', (event) => {
      const form = button.form;
      const selected = form ? form.querySelectorAll('input[name="package_event_id"]:checked,input[name="word_package_id"]:checked').length : 0;
      if (!window.confirm(`${selected} ausgewählte E-Mail(s) jetzt direkt S/MIME-verschlüsselt versenden?`)) {
        event.preventDefault();
      }
    });
  });

  document.querySelectorAll('button[data-confirm-recreate]').forEach((button) => {
    button.addEventListener('click', (event) => {
      if (!window.confirm('Eine neue vollständige START-Datei erzeugen? Frühere Arbeitsmappen und Update-Dateien werden dadurch abgelöst.')) {
        event.preventDefault();
      }
    });
  });
})();
