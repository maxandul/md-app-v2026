const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const code = fs.readFileSync(path.join(__dirname, '../webapp/static/goal_import.js'), 'utf8');

function setup(selected, fetch) {
  const button = {disabled: false};
  const form = {dataset: {batchUrl: '/batches'}, elements: {goal_year: {value: '2026'}},
    querySelector: () => button, addEventListener(_type, callback) {this.submit = callback;}};
  const folder = {files: selected, addEventListener() {}};
  const files = {files: [], addEventListener() {}};
  const status = {textContent: '', links: [], append(link) {this.links.push(link);}};
  const nodes = {'#goal-import': form, '#goal-folder': folder, '#goal-files': files, '#goal-import-status': status};
  const navigation = [];
  class FormData {
    constructor() {this.fields = [];}
    append(...args) {this.fields.push(args);}
  }
  vm.runInNewContext(code, {document: {querySelector: selector => nodes[selector], createElement: () => ({})},
    fetch, FormData, window: {location: {assign: url => navigation.push(url)}}});
  return {status, button, folder, navigation, submit: () => form.submit({preventDefault() {}})};
}
const response = data => ({ok: true, redirected: false, json: async () => data});

test('folder uploads supported files individually and skips temporary/unrelated files', async () => {
  const calls = [];
  const files = ['old.docx', 'new.PDF', '~$temp.docx', 'notes.txt'].map(name => ({name, size: 1024}));
  const app = setup(files, async (url, options) => {
    calls.push({url, fields: options.body.fields});
    return response(url === '/batches' ? {upload_url: '/files', preview_url: '/preview'} : {file_id: 'a'});
  });
  await app.submit();
  assert.equal(calls.length, 3);
  assert.equal(calls[0].fields[0][1], '2026');
  assert.equal(calls[1].fields[0][2], 'old.docx');
  assert.equal(calls[2].fields[0][2], 'new.PDF');
  assert.deepEqual(app.navigation, ['/preview']);
  assert.equal(app.button.disabled, false);
});

test('partial upload failure offers existing preview without claiming import', async () => {
  let count = 0;
  const app = setup([{name: 'a.docx', size: 1}, {name: 'b.pdf', size: 1}], async () => {
    count++;
    if (count === 1) return response({upload_url: '/files', preview_url: '/preview'});
    if (count === 2) return response({file_id: 'a'});
    return {ok: false, json: async () => ({error: 'Verbindung unterbrochen'})};
  });
  await app.submit();
  assert.equal(app.navigation.length, 0);
  assert.match(app.status.textContent, /noch keine Ziele/);
  assert.equal(app.status.links[0].href, '/preview');
  assert.equal(app.button.disabled, false);
});

test('oversize folder item is rejected before sending', async () => {
  const app = setup([{name: 'huge.pdf', size: 21 * 1024 * 1024}], () => {throw Error('Unexpected upload');});
  await app.submit();
  assert.match(app.status.textContent, /20 MB/);
});
