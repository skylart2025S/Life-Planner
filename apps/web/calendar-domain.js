(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.CalendarDomain = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const KEY = 'life-planner.calendar.v1';
  const KINDS = Object.freeze(['workout', 'study', 'meal', 'clothing', 'personal']);
  function fail(message) { throw new Error(message); }
  function exact(value, keys) {
    if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).sort().join('|') !== keys.slice().sort().join('|')) fail('Invalid calendar record fields.');
  }
  function id(value) {
    if (typeof value !== 'string' || !/^[a-zA-Z0-9-]{1,64}$/.test(value)) fail('Invalid event ID.');
  }
  function instant(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value)) fail('Use a valid UTC event time.');
    const date = new Date(value);
    if (!Number.isFinite(date.getTime()) || date.toISOString() !== value || date.getUTCFullYear() < 2000 || date.getUTCFullYear() > 2100) fail('Event times must be valid dates between 2000 and 2100.');
    return date.getTime();
  }
  function validateEvent(event) {
    exact(event, ['id', 'title', 'kind', 'start', 'end', 'fixed']);
    id(event.id);
    if (typeof event.title !== 'string' || !event.title.trim() || event.title !== event.title.trim() || event.title.length > 200 || /[\u0000-\u001f\u007f]/.test(event.title)) fail('Event title must contain 1–200 characters without control characters.');
    if (!KINDS.includes(event.kind) || typeof event.fixed !== 'boolean') fail('Choose a valid event kind and fixed setting.');
    if (instant(event.end) <= instant(event.start)) fail('The end time must be after the start time.');
    return event;
  }
  function empty() { return { version: 1, revision: 0, events: [] }; }
  function validate(state) {
    exact(state, ['version', 'revision', 'events']);
    if (state.version !== 1 || !Number.isSafeInteger(state.revision) || state.revision < 0) fail('Unsupported calendar version or revision.');
    if (!Array.isArray(state.events) || state.events.length > 500) fail('The device calendar limit is 500 events.');
    state.events.forEach(validateEvent);
    if (new Set(state.events.map(event => event.id)).size !== state.events.length) fail('Duplicate event IDs.');
    const ordered = state.events.slice().sort((a, b) => a.start.localeCompare(b.start));
    for (let i = 1; i < ordered.length; i++) {
      if (ordered[i].start < ordered[i - 1].end) fail(`“${ordered[i].title}” overlaps “${ordered[i - 1].title}”. Choose another time.`);
    }
    return state;
  }
  function copyEvent(e) { return { id: e.id, title: e.title, kind: e.kind, start: e.start, end: e.end, fixed: e.fixed }; }
  function copyState(s) { return { version: s.version, revision: s.revision, events: s.events.map(copyEvent) }; }
  function freeze(value) {
    if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
    return value;
  }
  function propose(state, operation) {
    validate(state);
    if (state.revision === Number.MAX_SAFE_INTEGER) fail('Calendar revision limit reached.');
    if (!operation || !['create', 'update', 'delete'].includes(operation.type)) fail('Choose a supported calendar action.');
    exact(operation, operation.type === 'delete' ? ['type', 'id'] : ['type', 'event']);
    if (operation.type === 'delete') id(operation.id); else validateEvent(operation.event);
    const eventId = operation.type === 'delete' ? operation.id : operation.event.id;
    const old = state.events.find(event => event.id === eventId);
    if (operation.type === 'create' && old) fail('An event with this ID already exists.');
    if (operation.type !== 'create' && !old) fail('This event no longer exists. Reload your calendar.');
    if (old && old.fixed && (operation.type === 'delete' || old.start !== operation.event.start || old.end !== operation.event.end)) fail('This event is fixed. Unlock it first before moving or deleting it.');
    const before = copyState(state), after = copyState(state);
    const index = after.events.findIndex(event => event.id === eventId);
    if (operation.type === 'create') after.events.push(copyEvent(operation.event));
    else if (operation.type === 'delete') after.events.splice(index, 1);
    else after.events[index] = copyEvent(operation.event);
    after.revision++;
    validate(after);
    const copiedOperation = operation.type === 'delete' ? { type: 'delete', id: eventId } : { type: operation.type, event: copyEvent(operation.event) };
    return freeze({ baseRevision: state.revision, before, after, operation: copiedOperation });
  }
  function apply(state, proposal) {
    validate(state);
    exact(proposal, ['baseRevision', 'before', 'after', 'operation']);
    validate(proposal.before); validate(proposal.after);
    if (proposal.baseRevision !== state.revision || JSON.stringify(copyState(proposal.before)) !== JSON.stringify(copyState(state))) fail('Your calendar changed since this preview. Create a new preview.');
    // Recompute every operation so a modified or externally supplied preview
    // cannot bypass conflict, fixed-event or revision rules.
    const verified = propose(state, proposal.operation);
    if (JSON.stringify(copyState(verified.after)) !== JSON.stringify(copyState(proposal.after))) fail('This preview has changed. Create a new preview.');
    return copyState(verified.after);
  }
  function createStore(storage) {
    function raw() {
      try { return storage.getItem(KEY); } catch (_) { fail('Device storage is unavailable. Enable storage to save your calendar.'); }
    }
    function load() {
      const token = raw();
      try {
        if (token !== null && token.length > 500000) fail('Saved data is too large.');
        return { state: token === null ? empty() : validate(JSON.parse(token)), token };
      } catch (_) {
        const error = new Error('Saved calendar data is unreadable or unsupported. It has not been changed.');
        error.token = token; throw error;
      }
    }
    function check(token) { if (raw() !== token) fail('Your calendar changed in another tab. Reload saved plans before making changes.'); }
    // Browser callers must hold the same origin Web Lock while saving/clearing.
    // Comparing the raw token prevents a stale tab from overwriting newer data.
    function save(state, token) {
      const current = load(); check(token); validate(state);
      if (current.state.revision === Number.MAX_SAFE_INTEGER || state.revision !== current.state.revision + 1) fail('Your calendar revision changed. Create a new preview.');
      const serialized = JSON.stringify(copyState(state));
      if (serialized.length > 500000) fail('This calendar is too large to save on this device. Your saved calendar was not changed.');
      try { storage.setItem(KEY, serialized); }
      catch (_) { fail('Could not save on this device. Storage may be full or disabled. Your saved calendar was not changed.'); }
      return load();
    }
    function clear(token) {
      check(token);
      try { storage.removeItem(KEY); } catch (_) { fail('Could not clear device storage. Your calendar was not changed.'); }
      return load();
    }
    return { load, save, clear };
  }
  function localTimeZone() { return Intl.DateTimeFormat().resolvedOptions().timeZone || 'Device local time'; }
  function isoToLocal(value) {
    instant(value);
    const d = new Date(value), pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }
  function localToISO(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) fail('Enter a complete local date and time.');
    const [year, month, day, hour, minute] = value.split(/[-T:]/).map(Number);
    if (year < 2000 || year > 2100 || month < 1 || month > 12 || day < 1 || day > 31 || hour > 23 || minute > 59) fail('Choose a valid date and time between 2000 and 2100.');
    const local = new Date(year, month - 1, day, hour, minute);
    const matches = d => d.getFullYear() === year && d.getMonth() === month - 1 && d.getDate() === day && d.getHours() === hour && d.getMinutes() === minute;
    if (!matches(local)) fail('This local time does not exist or the date is invalid. Choose another time.');
    // Check nearby offsets rather than assuming that every DST change is one
    // hour. This also catches half-hour folds such as Australia/Lord_Howe.
    const offsets = new Set();
    for (let h = -48; h <= 48; h++) offsets.add(new Date(local.getTime() + h * 3600000).getTimezoneOffset());
    const wall = Date.UTC(year, month - 1, day, hour, minute);
    const candidates = [...offsets].map(offset => new Date(wall + offset * 60000)).filter(matches);
    if (candidates.length !== 1) fail('This local time occurs twice because the clocks change. Choose an unambiguous time.');
    const result = candidates[0].toISOString(); instant(result); return result;
  }
  return { KEY, KINDS, empty, validate, propose, apply, createStore, localToISO, isoToLocal, localTimeZone };
});
