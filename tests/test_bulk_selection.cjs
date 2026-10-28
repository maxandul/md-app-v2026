const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const code = fs.readFileSync(require('node:path').join(__dirname, '../webapp/static/bulk_selection.js'), 'utf8');

function setup({page = false, count = 120} = {}) {
  const handlers = {};
  const buttons = [];
  const rows = Array.from({length: count}, (_, n) => ({hidden: n >= 25}));
  let bar;
  const inputs = rows.map(row => ({name: 'selected', checked: false, disabled: false, row,
    hasAttribute(name) {return name === 'data-bulk-skip' && !!this.skip;},
    closest() {return row;}, dispatchEvent() {handlers.change();}}));
  const acknowledgement = {name: 'checked', checked: false};
  const scope = {dataset: {bulkSelection: 'selected'}, tagName: 'TABLE',
    querySelectorAll: () => [...inputs, acknowledgement], hasAttribute: () => page,
    closest: () => ({before: value => {bar = value;}}),
    addEventListener: (event, handler) => {handlers[event] = handler;}};
  const document = {querySelectorAll: () => [scope], createElement(tag) {
    const element = {setAttribute() {}, append(...children) {this.children = children;},
      addEventListener(event, callback) {this[event] = callback;}};
    if (tag === 'button') buttons.push(element);
    return element;
  }};
  vm.runInNewContext(code, {document, Event: class {}});
  return {inputs, rows, acknowledgement, all: buttons[0], none: buttons[1], status: bar.children[2], handlers};
}

test('all selects every matching page; disabled items and confirmations stay untouched', () => {
  const app = setup();
  app.inputs[3].disabled = true;
  app.inputs[4].skip = true;
  app.all.click();
  assert.equal(app.inputs.filter(input => input.checked).length, 118);
  assert.equal(app.inputs[119].checked, true);
  assert.equal(app.inputs[3].checked, false);
  assert.equal(app.inputs[4].checked, false);
  assert.equal(app.acknowledgement.checked, false);
  assert.equal(app.status.textContent, '118 ausgewählt insgesamt');
  app.none.click();
  assert.equal(app.inputs.some(input => input.checked), false);
});

test('a filter selects all matching rows including later pages; clear also removes hidden selections', () => {
  const app = setup();
  app.inputs[0].checked = true;
  app.handlers['md-table-filter']({detail: {rows: app.rows.slice(60)}});
  assert.equal(app.all.textContent, 'Alle 60 Treffer auswählen');
  app.all.click();
  assert.equal(app.inputs.filter(input => input.checked).length, 61);
  assert.equal(app.inputs[59].checked, false);
  app.none.click();
  assert.equal(app.inputs.filter(input => input.checked).length, 0);
});

test('manual changes update counts and page-only controls identify their scope', () => {
  const app = setup({page: true, count: 25});
  app.inputs[0].checked = true;
  app.handlers.change();
  assert.equal(app.status.textContent, '1 ausgewählt auf dieser Seite');
  assert.equal(app.all.textContent, 'Alle 25 auf dieser Seite auswählen');
  assert.equal(app.none.textContent, 'Seite abwählen');
  app.all.click();
  assert.equal(app.all.disabled, true);
  app.none.click();
  assert.equal(app.none.disabled, true);
});
