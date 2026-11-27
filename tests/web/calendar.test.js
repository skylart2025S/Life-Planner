'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const path = require('node:path');
const D = require('../../apps/web/calendar-domain.js');
const event = (id = 'gym', changes = {}) => ({ id, title: 'Gym', kind: 'workout', start: '2026-11-25T10:00:00.000Z', end: '2026-11-25T11:00:00.000Z', fixed: false, ...changes });
function create(state = D.empty(), e = event()) { return D.apply(state, D.propose(state, { type: 'create', event: e })); }
function memory() {
  const values = new Map();
  return { getItem: k => values.get(k) ?? null, setItem: (k, v) => values.set(k, v), removeItem: k => values.delete(k) };
}
function inZone(zone, source) {
  execFileSync(process.execPath, ['-e', `const assert=require('node:assert/strict'); const D=require(${JSON.stringify(path.resolve(__dirname, '../../apps/web/calendar-domain.js'))}); ${source}`], { env: { ...process.env, TZ: zone }, stdio: 'pipe' });
}
test('preview is deeply immutable, isolated from caller data, and has no effect until apply', () => {
  const state = D.empty(), e = event();
  const proposal = D.propose(state, { type: 'create', event: e });
  assert.deepEqual(state, D.empty());
  assert.equal(proposal.baseRevision, 0);
  assert.deepEqual(proposal.before, state);
  assert.equal(proposal.after.revision, 1);
  assert.equal(proposal.after.events.length, 1);
  e.title = 'Unrelated edit';
  assert.equal(proposal.after.events[0].title, 'Gym');
  assert.throws(() => { proposal.after.events[0].title = 'Modified'; }, TypeError);
  const saved = D.apply(state, proposal);
  assert.equal(saved.events[0].title, 'Gym');
  assert.equal(saved.revision, 1);
  assert.deepEqual(state, D.empty());
});
test('create, update, and delete preserve unrelated events and advance revisions once', () => {
  let state = create();
  state = create(state, event('study', { title: 'Study', kind: 'study', start: '2026-11-25T11:00:00.000Z', end: '2026-11-25T12:00:00.000Z' }));
  const old = JSON.stringify(state);
  const next = D.apply(state, D.propose(state, { type: 'update', event: event('gym', { title: 'Morning gym', start: '2026-11-26T10:00:00.000Z', end: '2026-11-26T11:00:00.000Z' }) }));
  assert.equal(JSON.stringify(state), old);
  assert.deepEqual(next.events[1], state.events[1]);
  assert.equal(next.revision, 3);
  const removed = D.apply(next, D.propose(next, { type: 'delete', id: 'gym' }));
  assert.deepEqual(removed.events, [state.events[1]]);
  assert.equal(removed.revision, 4);
});
test('rejects all overlap forms but permits adjacent blocks and other days', () => {
  const state = create();
  for (const [start, end] of [['09:30', '10:30'], ['10:30', '11:30'], ['10:10', '10:50'], ['09:00', '12:00'], ['10:00', '11:00']]) {
    assert.throws(() => D.propose(state, { type: 'create', event: event('other', { start: `2026-11-25T${start}:00.000Z`, end: `2026-11-25T${end}:00.000Z` }) }), /overlaps/);
  }
  assert.equal(create(state, event('before', { start: '2026-11-25T09:00:00.000Z', end: '2026-11-25T10:00:00.000Z' })).events.length, 2);
  assert.equal(create(state, event('after', { start: '2026-11-25T11:00:00.000Z', end: '2026-11-25T12:00:00.000Z' })).events.length, 2);
  assert.equal(create(state, event('later', { start: '2026-11-26T10:00:00.000Z', end: '2026-11-26T11:00:00.000Z' })).events.length, 2);
});
test('fixed events require a separate unlock before moving or deleting', () => {
  const fixed = event('gym', { fixed: true }), state = create(D.empty(), fixed);
  assert.throws(() => D.propose(state, { type: 'delete', id: 'gym' }), /fixed/);
  for (const fixedValue of [true, false]) assert.throws(() => D.propose(state, { type: 'update', event: { ...fixed, fixed: fixedValue, end: '2026-11-25T12:00:00.000Z' } }), /fixed/);
  const renamed = D.apply(state, D.propose(state, { type: 'update', event: { ...fixed, title: 'Appointment' } }));
  assert.equal(renamed.events[0].fixed, true);
  const unlocked = D.apply(state, D.propose(state, { type: 'update', event: { ...fixed, fixed: false } }));
  assert.equal(D.apply(unlocked, D.propose(unlocked, { type: 'delete', id: 'gym' })).events.length, 0);
});
test('stale, repeated, modified and forged proposals cannot apply', () => {
  const state = create(), proposal = D.propose(state, { type: 'delete', id: 'gym' });
  const applied = D.apply(state, proposal);
  assert.throws(() => D.apply(applied, proposal), /changed/);
  assert.throws(() => D.apply({ ...state, events: [event('gym', { title: 'Different same revision' })] }, proposal), /changed/);
  const modified = JSON.parse(JSON.stringify(proposal)); modified.after.events.push(event('surprise'));
  assert.throws(() => D.apply(state, modified), /preview has changed/);
  const forged = JSON.parse(JSON.stringify(proposal)); forged.before.events[0].fixed = true;
  const fixedState = { ...state, events: [event('gym', { fixed: true })] };
  assert.throws(() => D.apply(fixedState, forged), /fixed/);
});
test('requires existing IDs for changes and rejects duplicate IDs or unknown operations', () => {
  const state = create();
  assert.throws(() => D.propose(state, { type: 'create', event: event() }), /already exists/);
  assert.throws(() => D.propose(state, { type: 'update', event: event('missing') }), /no longer exists/);
  assert.throws(() => D.propose(state, { type: 'delete', id: 'missing' }), /no longer exists/);
  for (const operation of [null, {}, { type: 'reset' }, { type: 'delete', id: '../bad' }, { type: 'delete', id: 'gym', bypass: true }]) assert.throws(() => D.propose(state, operation));
});
test('strictly validates dates, event fields, state shapes and bounded revisions', () => {
  for (const changes of [{ title: '' }, { title: ' x ' }, { title: '\u0000' }, { title: 'x'.repeat(201) }, { id: 'a/b' }, { kind: 'unknown' }, { fixed: 'false' }, { extra: true }, { start: '2026-11-25T10:00:00Z' }, { start: '2026-02-30T10:00:00.000Z' }, { start: '1999-11-25T10:00:00.000Z' }, { end: '2101-01-01T00:00:00.000Z' }, { end: event().start }, { end: '2026-11-25T09:00:00.000Z' }]) assert.throws(() => create(D.empty(), event('gym', changes)));
  for (const state of [null, [], {}, { ...D.empty(), version: 2 }, { ...D.empty(), revision: -1 }, { ...D.empty(), revision: 1.5 }, { ...D.empty(), revision: Number.MAX_SAFE_INTEGER + 1 }, { ...D.empty(), surprise: true }, { ...D.empty(), events: [event(), event()] }]) assert.throws(() => D.validate(state));
  assert.throws(() => D.propose({ ...D.empty(), revision: Number.MAX_SAFE_INTEGER }, { type: 'create', event: event() }), /limit/);
});
test('enforces the 500 event limit without mutating the saved calendar', () => {
  const events = Array.from({ length: 500 }, (_, i) => event(`event-${i}`, { start: new Date(Date.UTC(2026, 0, 1, i)).toISOString(), end: new Date(Date.UTC(2026, 0, 1, i + 1)).toISOString() }));
  const state = { ...D.empty(), events };
  assert.equal(D.validate(state).events.length, 500);
  assert.throws(() => create(state), /500/);
  assert.equal(state.events.length, 500);
});
test('saved events survive reload; stale tokens and wrong revisions cannot overwrite changes', () => {
  const storage = memory(), a = D.createStore(storage), b = D.createStore(storage);
  assert.deepEqual(a.load(), { state: D.empty(), token: null });
  const first = a.load(), saved = a.save(create(), first.token);
  assert.deepEqual(b.load(), saved);
  assert.throws(() => b.save(create(), first.token), /another tab/);
  assert.throws(() => b.clear(first.token), /another tab/);
  assert.throws(() => b.save(saved.state, saved.token), /revision changed/);
  const next = D.apply(saved.state, D.propose(saved.state, { type: 'delete', id: 'gym' }));
  assert.equal(b.save(next, saved.token).state.revision, 2);
  assert.throws(() => a.save(next, saved.token), /another tab/);
});
test('corrupt, oversized and unsupported storage is preserved until explicit clear of only its key', () => {
  const storage = memory(), store = D.createStore(storage);
  storage.setItem('wardrobe', 'keep');
  for (const raw of ['bad json', '{"version":2}', 'x'.repeat(500001), JSON.stringify({ ...D.empty(), events: [event(), event()] })]) {
    storage.setItem(D.KEY, raw);
    let token;
    assert.throws(() => { try { store.load(); } catch (error) { token = error.token; throw error; } }, /unreadable/);
    assert.throws(() => store.save(create(), raw), /unreadable/);
    assert.equal(storage.getItem(D.KEY), raw);
    assert.deepEqual(store.clear(token).state, D.empty());
    assert.equal(storage.getItem('wardrobe'), 'keep');
  }
});
test('storage failures report errors and preserve already saved data', () => {
  assert.throws(() => D.createStore({ getItem() { throw Error('disabled'); } }).load(), /unavailable/);
  const storage = memory(), store = D.createStore(storage), saved = store.save(create(), null);
  storage.setItem = () => { throw Error('quota'); };
  const next = D.apply(saved.state, D.propose(saved.state, { type: 'delete', id: 'gym' }));
  assert.throws(() => store.save(next, saved.token), /Could not save/);
  assert.equal(storage.getItem(D.KEY), saved.token);
  storage.removeItem = () => { throw Error('disabled'); };
  assert.throws(() => store.clear(saved.token), /Could not clear/);
});
test('oversized serialized state is rejected before it can overwrite readable saved data', () => {
  const storage = memory(), store = D.createStore(storage), saved = store.save(create(), null);
  const events = Array.from({ length: 500 }, (_, i) => event(`event-${i}`, {
    title: '\ud800'.repeat(200),
    start: new Date(Date.UTC(2026, 0, 1, i)).toISOString(),
    end: new Date(Date.UTC(2026, 0, 1, i + 1)).toISOString()
  }));
  const next = { ...saved.state, revision: saved.state.revision + 1, events };
  assert.equal(D.validate(next), next);
  assert.ok(JSON.stringify(next).length > 500000);
  assert.throws(() => store.save(next, saved.token), /too large to save/);
  assert.equal(storage.getItem(D.KEY), saved.token);
  assert.deepEqual(store.load(), saved);
});
test('New York local conversion rejects DST gaps/folds and impossible dates', () => {
  inZone('America/New_York', `
    assert.equal(D.localTimeZone(), 'America/New_York');
    assert.equal(D.localToISO('2026-11-25T10:30'), '2026-11-25T15:30:00.000Z');
    assert.equal(D.isoToLocal('2026-11-25T15:30:00.000Z'), '2026-11-25T10:30');
    assert.throws(() => D.localToISO('2026-03-08T02:30'), /does not exist/);
    assert.throws(() => D.localToISO('2026-11-01T01:30'), /occurs twice/);
    assert.equal(D.localToISO('2026-11-01T02:30'), '2026-11-01T07:30:00.000Z');
    for (const value of ['2026-02-30T10:00', '2026-13-01T10:00', '2026-11-25T24:00', '2026-11-25T10:60', '2026-1-1T10:00', '1999-12-31T23:00', '2026-11-25']) assert.throws(() => D.localToISO(value));
  `);
});
test('local conversion also rejects half-hour DST folds and supports ordinary UTC leap days', () => {
  inZone('Australia/Lord_Howe', `assert.throws(() => D.localToISO('2026-04-05T01:45'), /occurs twice/); assert.throws(() => D.localToISO('2026-10-04T02:15'), /does not exist/);`);
  inZone('UTC', `assert.equal(D.localToISO('2028-02-29T12:45'), '2028-02-29T12:45:00.000Z'); assert.throws(() => D.localToISO('2027-02-29T12:45'), /invalid/);`);
});
