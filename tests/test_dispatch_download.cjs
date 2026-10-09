// Run with: node --test tests/test_dispatch_download.cjs
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const code = fs.readFileSync(require('node:path').join(__dirname, '../webapp/static/dispatch.js'), 'utf8');

function setup(fetch) {
  const nodes = [];
  const button = {disabled: false};
  const form = {
    action: '/word-package',
    after(node) { this.status = node; },
    addEventListener(_type, fn) { this.submit = fn; },
    querySelectorAll() { return [button]; },
    setAttribute(name, value) { this[name] = value; },
    removeAttribute(name) { delete this[name]; },
  };
  const document = {
    querySelectorAll(selector) { return selector.startsWith('form[') ? [form] : []; },
    createElement(tag) {
      const node = {tag, children: [], setAttribute() {}, append(child) { this.children.push(child); }, click() { this.clicked = true; }};
      nodes.push(node); return node;
    },
    createTextNode(text) { return {textContent: text}; },
  };
  vm.runInNewContext(code, {
    document, fetch, FormData: class {append() {}},
    window: {location: {href: '/manager'}},
    URL: {createObjectURL: () => 'blob:test', revokeObjectURL() {}},
    DOMParser: class {parseFromString(text) {return {querySelectorAll: () => [{textContent: text}]};}},
    setTimeout() {throw Error('Downloads must not race a reload timer');},
  });
  return {form, button, nodes, submit: () => form.submit({preventDefault() {}})};
}

test('waits for full download and offers retry without regenerating', async () => {
  let resolveBlob;
  const body = new Promise(resolve => {resolveBlob = resolve;});
  let requests = 0;
  const env = setup(async () => {
    requests++;
    return {ok: true, headers: {get: () => 'attachment; filename="MD_Word.zip"'}, blob: () => body};
  });
  const pending = env.submit();
  await Promise.resolve();
  assert.equal(env.button.disabled, true);
  assert.match(env.form.status.textContent, /Bitte warten/);
  assert.equal(env.nodes.filter(node => node.clicked).length, 0);
  await env.submit();
  assert.equal(requests, 1);
  resolveBlob({}); await pending;
  assert.equal(env.button.disabled, false);
  const link = env.nodes.find(node => node.download);
  assert.equal(link.download, 'MD_Word.zip');
  assert.equal(link.clicked, true);
  link.click(); assert.equal(requests, 1);
  assert.match(env.form.status.textContent, /Datei erzeugt/);
});

test('redirected validation error is visible instead of downloaded as ZIP', async () => {
  const env = setup(async () => ({ok: true, headers: {get: () => ''}, text: async () => 'Die Word-Vorlage fehlt.'}));
  await env.submit();
  assert.equal(env.form.status.textContent, 'Die Word-Vorlage fehlt.');
  assert.equal(env.form.status.className, 'message message--error');
  assert.equal(env.button.disabled, false);
  assert.equal(env.nodes.filter(node => node.clicked).length, 0);
});
