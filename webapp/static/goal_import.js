(() => {
  'use strict';
  const form = document.querySelector('#goal-import');
  if (!form) return;
  const folder = document.querySelector('#goal-folder');
  const files = document.querySelector('#goal-files');
  const status = document.querySelector('#goal-import-status');
  folder.addEventListener('change', () => { files.value = ''; });
  files.addEventListener('change', () => { folder.value = ''; });
  let busy = false;
  async function json(response) {
    const data = await response.json().catch(() => ({}));
    if (!response.ok || response.redirected) throw new Error(data.error || 'Übertragung nicht möglich. Anmeldung, Dateigrösse und Verbindung prüfen.');
    return data;
  }
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (busy) return;
    const all = [...folder.files, ...files.files];
    const selected = all.filter(file => /\.(docx|docm|pdf)$/i.test(file.name) && !file.name.startsWith('~$'));
    if (!selected.length) { status.textContent = 'Bitte einen Ordner oder Word-/PDF-Ausblicke auswählen.'; return; }
    if (selected.some(file => file.size > 20 * 1024 * 1024) || selected.length > 5000 || selected.reduce((sum, file) => sum + file.size, 0) > 1024 ** 3) {
      status.textContent = 'Auswahl zu gross: maximal 20 MB je Datei, 5000 Dateien und 1 GB pro Auswahl. Bitte in kleinere Ordner aufteilen.'; return;
    }
    busy = true;
    const button = form.querySelector('button');
    button.disabled = true;
    folder.disabled = files.disabled = true;
    let batch;
    try {
      const body = new FormData();
      body.append('goal_year', form.elements.goal_year.value);
      batch = await json(await fetch(form.dataset.batchUrl, {method: 'POST', body, credentials: 'same-origin'}));
      for (let index = 0; index < selected.length; index++) {
        status.textContent = `Datei ${index + 1} von ${selected.length} wird übertragen: ${selected[index].name}. ${all.length - selected.length} andere Dateien übersprungen.`;
        const upload = new FormData();
        upload.append('file', selected[index], selected[index].name);
        await json(await fetch(batch.upload_url, {method: 'POST', body: upload, credentials: 'same-origin'}));
      }
      status.textContent = 'Auswahl wird analysiert. Die Vorschau wird geöffnet; bitte warten …';
      window.location.assign(batch.preview_url);
    } catch (error) {
      status.textContent = `${error.message} Es wurden noch keine Ziele in die Datenbank übernommen. `;
      if (batch) {
        const link = document.createElement('a');
        link.href = batch.preview_url;
        link.textContent = 'Bereits übertragene Dateien prüfen';
        status.append(link);
      }
    } finally {
      busy = false;
      button.disabled = folder.disabled = files.disabled = false;
    }
  });
})();
