'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const D = require('../../apps/web/wardrobe-domain.js');
const garment = (id, category = 'top', extra = {}) => ({ id, category, name: `My ${id}`, color: 'Cream', occasion: 'any', available: true, ...extra });
function ready() { return { ...D.empty(), garments: [garment('shirt'), garment('trousers', 'bottom'), garment('dress', 'one-piece'), garment('shoes', 'shoes'), garment('jacket', 'layer')] }; }
const outfit = (items = { top: 'shirt', bottom: 'trousers', shoes: 'shoes' }) => ({ id: 'outfit', name: 'A day out', items });
function memory() {
  const values = new Map();
  return { getItem: k => values.get(k) ?? null, setItem: (k, v) => values.set(k, v), removeItem: k => values.delete(k) };
}
test('starts empty and persists validated state across store instances', () => {
  const storage = memory(), a = D.createStore(storage);
  assert.deepEqual(a.read().state, D.empty());
  const saved = a.write(null, ready());
  assert.equal(saved.state.revision, 1);
  assert.deepEqual(D.createStore(storage).read(), saved);
});
test('outfit requires complete separates or one piece plus shoes', () => {
  assert.equal(D.saveOutfit(ready(), outfit()).outfits.length, 1);
  assert.equal(D.saveOutfit(ready(), outfit({ onePiece: 'dress', shoes: 'shoes', layer: 'jacket' })).outfits.length, 1);
  for (const items of [{ top: 'shirt', shoes: 'shoes' }, { onePiece: 'dress' }, { onePiece: 'dress', top: 'shirt', shoes: 'shoes' }, { top: 'shirt', bottom: 'shirt', shoes: 'shoes' }, { shoes: 'shoes' }]) assert.throws(() => D.saveOutfit(ready(), outfit(items)));
});
test('never saves an outfit referencing missing or unavailable clothes', () => {
  const state = ready(); state.garments[0].available = false;
  assert.throws(() => D.saveOutfit(state, outfit()), /unavailable/);
  assert.throws(() => D.saveOutfit(ready(), outfit({ top: 'missing', bottom: 'trousers', shoes: 'shoes' })), /missing/);
});
test('deletion and unavailable/category edits remove affected outfits; renames resolve current data', () => {
  const state = D.saveOutfit(ready(), outfit());
  assert.equal(D.deleteGarment(state, 'shirt').outfits.length, 0);
  assert.equal(D.updateGarment(state, garment('shirt', 'top', { available: false })).outfits.length, 0);
  assert.equal(D.updateGarment(state, garment('shirt', 'layer')).outfits.length, 0);
  const renamed = D.updateGarment(state, garment('shirt', 'top', { name: 'New name' }));
  assert.equal(renamed.outfits.length, 1);
  assert.equal(renamed.garments.find(g => g.id === renamed.outfits[0].items.top).name, 'New name');
  assert.equal(state.garments[0].name, 'My shirt');
});
test('rejects invalid input and stored structures', () => {
  for (const changes of [{ name: '' }, { name: 'x'.repeat(81) }, { name: ' embedded ' }, { color: '\u0000red' }, { category: 'hat' }, { occasion: 'party' }, { available: 'true' }, { id: '../bad' }]) assert.throws(() => D.updateGarment(ready(), garment('shirt', 'top', changes)));
  for (const state of [null, [], {}, { ...ready(), version: 2 }, { ...ready(), revision: -1 }, { ...ready(), revision: 1.5 }, { ...ready(), other: 'data' }, { ...ready(), garments: [garment('a'), garment('a')] }, { ...ready(), outfits: [outfit(), outfit()] }]) assert.throws(() => D.validate(state));
  assert.throws(() => D.saveOutfit(ready(), { ...outfit(), items: { ...outfit().items, unknown: 'shirt' } }));
  assert.throws(() => D.saveOutfit(ready(), { ...outfit(), name: '' }));
});
test('enforces garment and outfit count limits', () => {
  const garments = Array.from({ length: 200 }, (_, i) => garment(`item-${i}`));
  const state = { ...D.empty(), garments };
  assert.equal(D.validate(state).garments.length, 200);
  assert.throws(() => D.updateGarment(state, garment('another')), /limit/);
  const outfits = Array.from({ length: 100 }, (_, i) => ({ ...outfit(), id: `outfit-${i}` }));
  assert.equal(D.validate({ ...ready(), outfits }).outfits.length, 100);
  assert.throws(() => D.saveOutfit({ ...ready(), outfits }, outfit()), /limit/);
});
test('corrupt or unsupported saved data is preserved, never replaced by a write', () => {
  const storage = memory(), store = D.createStore(storage);
  for (const raw of ['invalid json', '{"version":2}', JSON.stringify({ ...ready(), outfits: [outfit({ top: 'missing', bottom: 'trousers', shoes: 'shoes' })] }), 'x'.repeat(300001)]) {
    storage.setItem(D.KEY, raw);
    assert.throws(() => store.read(), /unreadable/);
    assert.throws(() => store.write(raw, ready()), /unreadable/);
    assert.equal(storage.getItem(D.KEY), raw);
  }
});
test('stale tabs cannot overwrite or clear newer saved changes', () => {
  const storage = memory(), a = D.createStore(storage), b = D.createStore(storage);
  const first = a.read(), second = b.read();
  const saved = a.write(first.token, ready());
  assert.throws(() => b.write(second.token, D.empty()), /another tab/);
  assert.throws(() => b.clear(second.token), /another tab/);
  assert.deepEqual(a.read(), saved);
  const later = b.write(saved.token, D.updateGarment(saved.state, garment('coat', 'layer')));
  assert.throws(() => a.write(saved.token, saved.state), /another tab/);
  assert.equal(later.state.revision, 2);
});
test('clear removes only the wardrobe key, including explicit recovery from corruption', () => {
  const storage = memory(), store = D.createStore(storage);
  storage.setItem('other-data', 'keep'); storage.setItem(D.KEY, 'bad');
  let token; try { store.read(); } catch (error) { token = error.token; }
  assert.deepEqual(store.clear(token).state, D.empty());
  assert.equal(storage.getItem('other-data'), 'keep');
});
test('storage failures are visible and do not produce successful saves', () => {
  assert.throws(() => D.createStore({ getItem() { throw Error('disabled'); } }).read(), /unavailable/);
  const storage = memory(); storage.setItem(D.KEY, JSON.stringify(ready()));
  const before = storage.getItem(D.KEY), store = D.createStore(storage);
  storage.setItem = () => { throw Error('quota'); };
  assert.throws(() => store.write(before, ready()), /Could not save/);
  assert.equal(storage.getItem(D.KEY), before);
  storage.removeItem = () => { throw Error('disabled'); };
  assert.throws(() => store.clear(before), /Could not clear/);
});
