const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const code = fs.readFileSync(require('node:path').join(__dirname, '../webapp/static/action_position.js'), 'utf8');
function run(path, hash = '', blocked = false) {
  const result = {details: [{open: false}]};
  let saved = JSON.stringify({path: '/dialoge', at: Date.now(), y: 740, details: [0]});
  vm.runInNewContext(code, {
    location: {pathname: path, hash}, scrollY: 740,
    scrollTo: (_, y) => {result.y = y;}, requestAnimationFrame: fn => fn(),
    sessionStorage: {getItem() {if (blocked) throw Error('blocked'); return saved;}, removeItem() {saved = null;}, setItem(_, value) {saved = value;}},
    document: {addEventListener(_, fn) {result.submit = fn;}, querySelectorAll: () => result.details,
      querySelector: () => null, getElementById: () => ({scrollIntoView() {result.anchor = true;}})}
  });
  return result;
}
test('same-screen POST restores position and expanded details', () => {
  const result = run('/dialoge'); assert.equal(result.y, 740); assert.equal(result.details[0].open, true);
});
test('explicit result anchor has priority', () => {
  const result = run('/dialoge', '#result'); assert.equal(result.anchor, true); assert.equal(result.y, undefined);
});
test('different screen and disabled storage preserve normal navigation', () => {
  assert.equal(run('/versand').y, undefined); assert.equal(run('/dialoge', '', true).y, undefined);
});
