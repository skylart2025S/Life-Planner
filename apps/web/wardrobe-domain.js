(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.Wardrobe = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const KEY = 'life-planner.wardrobe.v1';
  const CATEGORIES = ['top', 'bottom', 'one-piece', 'shoes', 'layer'];
  const OCCASIONS = ['casual', 'work', 'workout', 'any'];
  const SLOTS = { top: 'top', bottom: 'bottom', onePiece: 'one-piece', shoes: 'shoes', layer: 'layer' };
  function fail(message) { throw new Error(message); }
  function object(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }
  function exact(value, keys) {
    if (!object(value) || Object.keys(value).sort().join('|') !== keys.slice().sort().join('|')) fail('Invalid record fields.');
  }
  function text(value, max, label) {
    if (typeof value !== 'string' || !value.trim() || value !== value.trim() || value.length > max || /[\u0000-\u001f\u007f]/.test(value)) fail(`${label} must contain 1–${max} characters, without control characters.`);
    return value;
  }
  function id(value) { if (typeof value !== 'string' || !/^[a-zA-Z0-9-]{1,64}$/.test(value)) fail('Invalid record ID.'); }
  function validateGarment(g) {
    exact(g, ['id', 'name', 'category', 'color', 'occasion', 'available']);
    id(g.id); text(g.name, 80, 'Item name'); text(g.color, 40, 'Color');
    if (!CATEGORIES.includes(g.category) || !OCCASIONS.includes(g.occasion) || typeof g.available !== 'boolean') fail('Choose a valid category, occasion and availability.');
    return g;
  }
  function validateOutfit(outfit, garments) {
    exact(outfit, ['id', 'name', 'items']); id(outfit.id); text(outfit.name, 80, 'Outfit name');
    if (!object(outfit.items) || Object.keys(outfit.items).some(key => !Object.hasOwn(SLOTS, key))) fail('Invalid outfit selections.');
    const s = outfit.items;
    if (s.onePiece ? (s.top || s.bottom) : (!s.top || !s.bottom)) fail('Choose a top and bottom, or one piece.');
    if (!s.shoes) fail('Choose shoes to complete this outfit.');
    for (const [slot, garmentId] of Object.entries(s)) {
      id(garmentId);
      const garment = garments.find(g => g.id === garmentId);
      if (!garment || !garment.available || garment.category !== SLOTS[slot]) fail('An outfit item is missing, unavailable or in the wrong category. Review your selections.');
    }
    return outfit;
  }
  function empty() { return { version: 1, revision: 0, garments: [], outfits: [] }; }
  function validate(state) {
    exact(state, ['version', 'revision', 'garments', 'outfits']);
    if (state.version !== 1 || !Number.isSafeInteger(state.revision) || state.revision < 0) fail('Unsupported wardrobe version or revision.');
    if (!Array.isArray(state.garments) || state.garments.length > 200 || !Array.isArray(state.outfits) || state.outfits.length > 100) fail('The wardrobe limit is 200 items and 100 outfits.');
    for (const g of state.garments) validateGarment(g);
    for (const outfit of state.outfits) validateOutfit(outfit, state.garments);
    if (new Set(state.garments.map(g => g.id)).size !== state.garments.length || new Set(state.outfits.map(o => o.id)).size !== state.outfits.length) fail('Duplicate record IDs.');
    return state;
  }
  function updateGarment(state, garment) {
    validate(state); validateGarment(garment);
    const garments = state.garments.filter(g => g.id !== garment.id).concat(garment);
    const outfits = state.outfits.filter(outfit => {
      try { validateOutfit(outfit, garments); return true; } catch (_) { return false; }
    });
    return validate({ ...state, garments, outfits });
  }
  function deleteGarment(state, garmentId) {
    validate(state);
    return validate({ ...state, garments: state.garments.filter(g => g.id !== garmentId), outfits: state.outfits.filter(o => !Object.values(o.items).includes(garmentId)) });
  }
  function saveOutfit(state, outfit) {
    validate(state); validateOutfit(outfit, state.garments);
    return validate({ ...state, outfits: state.outfits.filter(o => o.id !== outfit.id).concat(outfit) });
  }
  function createStore(storage) {
    function raw() {
      try { return storage.getItem(KEY); } catch (_) { fail('Device storage is unavailable. Enable storage to save your wardrobe.'); }
    }
    function read() {
      const token = raw();
      try {
        if (token !== null && token.length > 300000) fail('Saved data is too large.');
        return { token, state: token === null ? empty() : validate(JSON.parse(token)) };
      } catch (_) {
        const error = new Error('Saved wardrobe data is unreadable or unsupported. It has not been changed. Clear this wardrobe only if you no longer need its saved items.');
        error.token = token; throw error;
      }
    }
    function check(token) { if (raw() !== token) fail('Your wardrobe changed in another tab. Reload saved items before making changes.'); }
    // Call write/clear inside the same origin Web Lock in browser code. The token
    // check detects stale forms; Web Locks serialize overlapping tab writes.
    function write(token, next) {
      const current = read(); check(token);
      if (current.state.revision === Number.MAX_SAFE_INTEGER) fail('Wardrobe revision limit reached.');
      const saved = validate({ ...next, revision: current.state.revision + 1 });
      try { storage.setItem(KEY, JSON.stringify(saved)); } catch (_) { fail('Could not save on this device. Storage may be full or disabled. Your saved wardrobe was not changed.'); }
      return read();
    }
    function clear(token) {
      check(token);
      try { storage.removeItem(KEY); } catch (_) { fail('Could not clear device storage. Your wardrobe was not changed.'); }
      return read();
    }
    return { read, write, clear };
  }
  return { KEY, CATEGORIES, OCCASIONS, SLOTS, empty, validate, validateGarment, validateOutfit, updateGarment, deleteGarment, saveOutfit, createStore };
});
